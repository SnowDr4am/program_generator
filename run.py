import asyncio
import json

from generate_ai import ai_generate


async def safe_ai_generate(prompt, mode, max_retries=3):
    for attempt in range(max_retries):
        result = await ai_generate(prompt, mode)
        if result:
            return result
        print(f"⚠️ Пустой ответ от ИИ (попытка {attempt + 1}/{max_retries}), пробуем снова...")
    raise ValueError("❌ Не удалось получить корректный ответ от ИИ после нескольких попыток.")



async def main():
    # Тестирование промпта 1 - генерация возможных учебных дисциплин
    course_theme = input("Введите основу для курса -> ")
    keyword_input = input("Введите ключевые слова через запятую -> ")
    keywords = [word.strip() for word in keyword_input.split(",")]
    result = [course_theme, keywords]
    mode = "names_programs"

    names_result = await safe_ai_generate(result, mode)
    print("Результат генерации учебных дисциплин")

    # Тестирование промпта 2 - генерация учебного плана
    course_theme = input("\nВыберите тему курса из списка -> ")
    mode = "generate_full_program"

    full_study_plan = await safe_ai_generate(course_theme, mode)
    print("Результат генерации учебного плана")

    # Тестирование промпта 3 - генерация плана на тему
    mode = "generate_theme_plan"
    lection_theme = input("\nВыберите тему из учебного плана -> ")
    result = [course_theme, full_study_plan, lection_theme]

    lection_plan_raw = await safe_ai_generate(result, mode)

    try:
        lection_plan = json.loads(lection_plan_raw)
    except json.JSONDecodeError:
        print("❌ Ошибка: не удалось разобрать JSON из ответа ИИ.")
        print("Содержимое:", lection_plan_raw)
        return

    print("Результат генерации плана на конкретную тему")

    # Тестирование промпта 4 - генерация лекции на 1 тему
    mode = "generate_theme_lection"
    theme_lection = input("\nВведите тему для создания лекции -> ")

    lections = {}

    if not isinstance(lection_plan, dict):
        print("❌ Ошибка: план лекций сгенерирован в неверном формате (ожидался словарь).")
        print(f"Фактически получено: {type(lection_plan).__name__} -> {lection_plan}")
        return

    if theme_lection not in lection_plan:
        print("❌ Ошибка: указанная тема не найдена в плане.")
        print("Доступные темы:")
        for key in lection_plan.keys():
            print(f" - {key}")
        return

    for pair_name, pair_content in lection_plan[theme_lection].items():
        print(f"Генерация лекции для {pair_name}...")

        result = [course_theme, theme_lection, {pair_name: pair_content}]
        lection_content = await safe_ai_generate(result, mode)

        lections[pair_name] = lection_content

    if lections:
        print("Результат генерации лекций")
    else:
        print("Ошибка: не удалось сгенерировать лекции.")

if __name__ == '__main__':
    asyncio.run(main())