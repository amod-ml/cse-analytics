import os

from dotenv import load_dotenv
from mistralai import MistralAI

from app.utils.structlogger import logger

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


async def get_mistral_client() -> MistralAI:
    """Get the Mistral client."""
    if not MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY is not set")
        raise ValueError("MISTRAL_API_KEY is not set")
    logger.info("Creating Mistral client")
    return MistralAI(api_key=MISTRAL_API_KEY)
