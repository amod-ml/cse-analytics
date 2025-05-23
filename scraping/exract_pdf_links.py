from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Configure logging at the module level
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)  # Use a named logger

# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #

HTML_PATH = Path("output/playwright_explore/quarterly_reports_tab_cleaned.html")
OUTPUT_PATH = Path("urls_dpl.json")

SYSTEM_PROMPT = (
    "You are given the raw HTML source of a page that lists quarterly reports. "
    "Identify only the CDN links that point to actual Quarterly Financial Reports only."
    "You must strictly ignore links that point to Interim Financial Statements or any other reports other than Quarterly Financial Reports, "
    "return an object with:\n"
    " • details - the human-readable title of the report if available\n"
    " • download_url - the absolute URL\n\n"
    "Return the collection under the key `results` and conform EXACTLY to the "
    "JSON schema passed in the request."
)

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _load_html() -> str:
    """Read the cleaned HTML file into a single string."""
    return HTML_PATH.read_text(encoding="utf-8")


def _init_client() -> genai.Client:
    """Initialise a Gemini client using the API key from the environment."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY must be set.")
    return genai.Client(api_key=api_key)


def _call_model(client: genai.Client, html: str) -> dict:
    """Send the HTML to Gemini and return the structured JSON response."""
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=html)],
        ),
    ]

    config = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json",
        response_schema=types.Schema(
            type=types.Type.OBJECT,
            required=["results"],
            properties={
                "results": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        required=["details", "download_url"],
                        properties={
                            "details": types.Schema(type=types.Type.STRING),
                            "download_url": types.Schema(type=types.Type.STRING),
                        },
                    ),
                )
            },
        ),
        system_instruction=[types.Part.from_text(text=SYSTEM_PROMPT)],
    )

    stream = client.models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=contents,
        config=config,
    )

    response_text = "".join(chunk.text for chunk in stream)
    logger.debug("Raw model output: %s", response_text)
    return json.loads(response_text)


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #


def main() -> None:
    """Entry point for CLI execution."""
    load_dotenv()

    logger.info("Loading HTML from %s", HTML_PATH)
    html = _load_html()

    logger.info("Calling Gemini to extract quarterly report URLs…")
    client = _init_client()
    data = _call_model(client, html)

    logger.info("Writing %d URLs to %s", len(data.get("results", [])), OUTPUT_PATH)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
