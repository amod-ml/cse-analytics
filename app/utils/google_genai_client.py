import os

from dotenv import load_dotenv
from google import genai

from app.utils.structlogger import logger

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


async def get_google_genai_client() -> genai.Client:
    """Get the Google GenAI client."""
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY is not set")
        raise ValueError("GOOGLE_API_KEY is not set")
    logger.info("Creating Google GenAI client")
    return genai.Client(api_key=GOOGLE_API_KEY)
