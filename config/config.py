from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

AI_TOKEN = os.getenv("AI_TOKEN")
AI_MODEL = os.getenv("AI_MODEL")

AI_CLIENT = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=AI_TOKEN
)