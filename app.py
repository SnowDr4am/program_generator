from flask import Flask, render_template, jsonify, request, send_file
import asyncio
from generate_ai import ai_generate
import json
from database.db import Database
import io
from docx import Document
from docx.shared import Pt
import logging
import re

app = Flask(__name__)
db = Database()
logging.basicConfig(level=logging.INFO)

def clean_ai_response(response):
    """Очищает ответ ИИ от markdown-обёртки и форматирования"""
    try:
        # Удаляем markdown-обёртку
        clean = re.sub(r"^```json|^```|```$", "", response.strip(), flags=re.MULTILINE).strip()
        # Пробуем распарсить JSON
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка при разборе JSON: {str(e)}")
        logging.error(f"Исходный ответ: {response}")
        raise ValueError("Не удалось разобрать ответ от ИИ")

# --- Вспомогательная функция для безопасного вызова асинхронных функций ---
def safe_ai_generate_sync(prompt, mode, max_retries=3):
    async def inner():
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await ai_generate(prompt, mode)
                if result is not None and result.strip():
                    return result
                print(f"⚠️ Пустой ответ от ИИ (попытка {attempt + 1}/{max_retries}), пробуем снова...")
            except Exception as e:
                last_error = e
                print(f"⚠️ Ошибка при генерации (попытка {attempt + 1}/{max_retries}): {str(e)}")
                if hasattr(e, 'response'):
                    print(f"Ответ API: {e.response.text}")
                    # Проверяем на превышение лимита
                    if 'Rate limit exceeded' in str(e.response.text):
                        raise ValueError("Превышен дневной лимит запросов к ИИ. Пожалуйста, попробуйте завтра или добавьте кредиты в настройках API.")
        if last_error:
            raise ValueError(f"❌ Не удалось получить корректный ответ от ИИ после {max_retries} попыток. Последняя ошибка: {str(last_error)}")
        raise ValueError(f"❌ Не удалось получить корректный ответ от ИИ после {max_retries} попыток.")
    return asyncio.run(inner())

@app.route('/')
def index():
    programs = db.get_all_programs()
    return render_template('index.html', programs=programs)

@app.route('/generate_programs', methods=['POST'])
def generate_programs():
    data = request.get_json()
    course_theme = data.get('course_theme', '')
    keywords = data.get('keywords', [])
    
    if not course_theme or not keywords:
        return jsonify({'error': 'Необходимо указать тему курса и ключевые слова'}), 400
    
    result = [course_theme, keywords]
    try:
        logging.info(f"Генерация программ для темы: {course_theme}, ключевые слова: {keywords}")
        programs = safe_ai_generate_sync(result, "names_programs")
        if not programs:
            raise ValueError("Получен пустой ответ от ИИ")
        programs_dict = clean_ai_response(programs)
        logging.info(f"Сгенерированные программы: {programs_dict}")
        
        # Сохраняем программы в базу данных
        for title, description in programs_dict.items():
            db.save_program(title, description)
        
        return jsonify(programs_dict)
    except Exception as e:
        logging.exception('Ошибка при генерации программ:')
        return jsonify({'error': str(e)}), 500

@app.route('/generate_course_plan/<int:program_id>', methods=['POST'])
def generate_course_plan(program_id):
    program = db.get_program_by_id(program_id)
    if not program:
        logging.error(f'Программа с id={program_id} не найдена')
        return jsonify({'error': 'Программа не найдена'}), 404
    
    try:
        # Передаем и заголовок, и описание программы
        result = [program['title'], program['description']]
        plan = safe_ai_generate_sync(result, "generate_full_program")
        plan_dict = clean_ai_response(plan)
        logging.info(f'План курса для программы {program_id}: {plan_dict}')
        
        # Сортируем темы по их номерам
        sorted_plan = {}
        # Сначала добавляем все темы, кроме литературы
        for key in sorted(plan_dict.keys(), key=lambda x: int(x.split(':')[0].split()[1]) if x.split(':')[0].split()[0] == 'Тема' else float('inf')):
            if key != 'literature':
                sorted_plan[key] = plan_dict[key]
        
        # В конце добавляем литературу, если она есть
        if 'literature' in plan_dict:
            sorted_plan['literature'] = plan_dict['literature']
        
        # Сохраняем план в базу данных
        db.save_course_plan(program_id, sorted_plan)
        return jsonify(sorted_plan)
    except Exception as e:
        logging.exception('Ошибка при генерации плана курса:')
        return jsonify({'error': str(e)}), 500

@app.route('/get_course_plan/<int:program_id>')
def get_course_plan(program_id):
    plan = db.get_course_plan(program_id)
    return jsonify(plan) if plan else jsonify({'error': 'План не найден'}), 404

@app.route('/update_course_plan/<int:program_id>', methods=['POST'])
def update_course_plan(program_id):
    data = request.get_json()
    db.update_course_plan(program_id, data)
    return jsonify({'success': True})

@app.route('/generate_lecture/<int:program_id>/<theme>', methods=['POST'])
def generate_lecture(program_id, theme):
    course_plan = db.get_course_plan(program_id)
    if not course_plan:
        logging.error(f'План курса для программы {program_id} не найден')
        return jsonify({'error': 'План курса не найден'}), 404
    
    program = db.get_program_by_id(program_id)
    if not program:
        logging.error(f'Программа с id={program_id} не найдена')
        return jsonify({'error': 'Программа не найдена'}), 404
    
    try:
        # Фильтруем литературу, если она есть
        if theme == 'literature':
            return jsonify({'error': 'Нельзя сгенерировать лекцию по литературе'}), 400
        if theme not in course_plan:
            return jsonify({'error': f'Тема {theme} не найдена в плане курса'}), 404
        
        result = [program['title'], theme, course_plan[theme]]
        lecture = safe_ai_generate_sync(result, "generate_theme_lection")
        lecture_dict = clean_ai_response(lecture)
        
        # Сохраняем лекцию в базу данных
        db.save_lecture(program_id, theme, lecture_dict)
        return jsonify(lecture_dict)
    except Exception as e:
        logging.exception('Ошибка при генерации лекции:')
        return jsonify({'error': str(e)}), 500

@app.route('/get_lecture/<int:program_id>/<theme>')
def get_lecture(program_id, theme):
    lecture = db.get_lecture(program_id, theme)
    return jsonify(lecture) if lecture else jsonify({'error': 'Лекция не найдена'}), 404

@app.route('/export_lecture/<int:program_id>/<theme>')
def export_lecture(program_id, theme):
    lecture = db.get_lecture(program_id, theme)
    if not lecture:
        return jsonify({'error': 'Лекция не найдена'}), 404
    
    # Создаем документ Word
    doc = Document()
    doc.add_heading(theme, 0)
    
    for pair_name, pair_content in lecture[theme].items():
        doc.add_heading(pair_name, level=1)
        
        # Добавляем введение
        doc.add_heading('Введение', level=2)
        doc.add_paragraph(pair_content['introduction'])
        
        # Добавляем разделы
        doc.add_heading('Основные разделы', level=2)
        for section in pair_content['sections']:
            doc.add_paragraph(section['title'], style='Heading 3')
            doc.add_paragraph(section['content'])
        
        # Добавляем заключение
        doc.add_heading('Заключение', level=2)
        doc.add_paragraph(pair_content['conclusion'])
        
        # Добавляем рекомендации
        if pair_content['recommendations']:
            doc.add_heading('Рекомендации', level=2)
            for rec in pair_content['recommendations']:
                doc.add_paragraph(rec, style='List Bullet')
    
    # Сохраняем документ в память
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    
    return send_file(
        doc_io,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=f'{theme}.docx'
    )

@app.route('/api/all_programs')
def api_all_programs():
    programs = db.get_all_programs()
    return jsonify(programs)

if __name__ == '__main__':
    app.run(debug=True) 