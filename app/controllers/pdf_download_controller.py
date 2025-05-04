import asyncio
import json
import re
import unicodedata
from pathlib import Path
from typing import Optional

import aiofiles
import httpx
import tenacity

from app.models import ReportItem, ReportList
from app.utils.structlogger import logger


def _sanitize_filename(details: str) -> str:
    """Creates a safe filename from report details."""
    # Normalize unicode characters
    details = unicodedata.normalize("NFKD", details).encode("ascii", "ignore").decode("ascii")
    # Lowercase, replace spaces/punctuation with underscores
    details = details.lower()
    details = re.sub(r"[\s\W]+", "_", details)
    # Remove leading/trailing underscores and consecutive underscores
    details = re.sub(r"^_+|_+$", "", details)
    details = re.sub(r"_+", "_", details)
    # Limit length (optional, but good practice)
    max_len = 100
    if len(details) > max_len:
        details = details[:max_len].rsplit("_", 1)[0]  # Try to cut at last underscore
        details = details or "report"  # Handle case where cut removes everything
    # Ensure filename is not empty
    details = details or "unknown_report"
    return f"{details}.pdf"


@tenacity.retry(
    reraise=True,
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=2, min=2, max=10),
    before_sleep=tenacity.before_sleep_log(logger, log_level="WARNING"),
)
async def _download_and_save_pdf(client: httpx.AsyncClient, item: ReportItem, output_dir: Path) -> Optional[Path]:
    """Downloads a single PDF and saves it asynchronously."""
    filename = _sanitize_filename(item.details)
    output_path = output_dir / filename
    url_str = str(item.download_url)  # Convert HttpUrl back to string for httpx

    logger.info(f"Attempting download: '{item.details}' from {url_str}")
    try:
        async with client.stream("GET", url_str, timeout=60.0, follow_redirects=True) as response:
            response.raise_for_status()  # Raise exception for 4xx/5xx errors

            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" not in content_type:
                logger.warning(f"Expected PDF, but got content-type '{content_type}' for {url_str}. Skipping.")
                return None

            async with aiofiles.open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    await f.write(chunk)
            logger.info(f"Successfully downloaded and saved: {output_path}")
            return output_path
    except httpx.RequestError as e:
        logger.error(f"HTTP Request error for {url_str}: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Status error {e.response.status_code} for {url_str}: {e}")
    except Exception:
        logger.exception(f"Unexpected error downloading {url_str}")
    return None


async def download_pdfs_for_company(company_name: str) -> None:
    """
    Reads urls_{company_name}.json, downloads all PDFs concurrently,
    and saves them to a company-specific folder.
    """
    input_json_path = Path(f"urls_{company_name}.json")
    output_dir = Path(company_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting PDF download process for '{company_name}'")
    logger.info(f"Reading URLs from: {input_json_path.resolve()}")
    logger.info(f"Saving PDFs to: {output_dir.resolve()}")

    if not input_json_path.is_file():
        logger.error(f"Input file not found: {input_json_path}")
        return

    try:
        async with aiofiles.open(input_json_path, encoding="utf-8") as f:
            content = await f.read()
        data = json.loads(content)
        report_data = ReportList(**data)  # Validate structure
        reports_to_download = report_data.results
        logger.info(f"Found {len(reports_to_download)} reports to download.")
    except json.JSONDecodeError:
        logger.exception(f"Failed to parse JSON from {input_json_path}")
        return
    except Exception:  # Catch Pydantic validation errors etc.
        logger.exception(f"Error processing JSON data from {input_json_path}")
        return

    if not reports_to_download:
        logger.info("No reports found in the JSON file to download.")
        return

    tasks = []
    # Use a single client for connection pooling
    async with httpx.AsyncClient() as client:
        for item in reports_to_download:
            tasks.append(_download_and_save_pdf(client, item, output_dir))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log summary
    success_count = sum(1 for r in results if isinstance(r, Path))
    failure_count = len(results) - success_count
    logger.info(f"Download process finished for '{company_name}'.")
    logger.info(f"Successful downloads: {success_count}")
    logger.info(f"Failed downloads: {failure_count}")

    if failure_count > 0:
        logger.warning("Some downloads failed. Check logs above for details.")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"  - Failed item '{reports_to_download[i].details}': {result}")
