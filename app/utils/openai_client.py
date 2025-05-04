import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.utils.structlogger import logger

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def get_openai_client() -> AsyncOpenAI:
    """Get the OpenAI client."""
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not set")
        raise ValueError("OPENAI_API_KEY is not set")
    logger.info("Creating OpenAI client")
    return AsyncOpenAI(api_key=OPENAI_API_KEY)
