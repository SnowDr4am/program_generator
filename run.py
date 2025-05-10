import asyncio
import json

from generate_ai import ai_generate

async def safe_ai_generate(prompt, mode, max_retries=3):
    for attempt in range(max_retries):
        try:
            raw_response = await ai_generate(prompt, mode)

            if not raw_response:
                print(f"⚠️ Пустой ответ от ИИ (попытка {attempt}/{max_retries})")
                continue

            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json") and cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[7:-3].strip()
            elif cleaned_response.startswith('```') and cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[3:-3].strip()

            response_data = json.loads(cleaned_response)

            print(response_data)
            return response_data
        except Exception as e:
            print(f"⚠️ Неожиданная ошибка (попытка {attempt}/{max_retries}): {type(e).__name__}: {e}")

async def generate_lection(course_theme, theme_lection, plan_lection):
    course_name = next(iter(plan_lection.keys()))
    course_data = plan_lection[course_name]

    lection = {}
    mode = "generate_theme_lection"

    for pair_name, pair_content in course_data.items():
        try:
            data = [course_theme, theme_lection, plan_lection, pair_content]
            lection_part = await safe_ai_generate(data, mode)
            lection[pair_name] = lection_part
        except Exception as e:
            print(f"Ошибка: {e}")
    print(lection)

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

    plan_lection = await safe_ai_generate(result, mode)
    print("Результат генерации плана на конкретную тему")
    # Тестирование промпта 4 - генерация лекции на 1 тему
    theme_lection = input("\nВведите тему для создания лекции -> ")

    await generate_lection(course_theme, theme_lection, plan_lection)

if __name__ == '__main__':
    asyncio.run(main())