import asyncio
import json
import traceback
from datetime import date
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, HTTPException, status

from app.controllers.data_extractor_controller import generate_financial_data
from app.models import DataExtractionRequest
from app.utils.structlogger import logger

router = APIRouter()

OUTPUT_FILES_DIR = Path("output_files")
ERRORS_DIR_NAME = "errors"
OUTPUT_FILES_DIR.mkdir(parents=True, exist_ok=True)

MAX_CONCURRENT_GEMINI_CALLS = 8


def sanitize_company_name(name: str) -> str:
    """Sanitizes a company name for use in directory or file names."""
    return name.lower().replace(" ", "_").replace(".", "").replace(",", "")


async def _save_json_output(output_path: Path, data: dict[str, Any]) -> None:
    """Saves the financial data as a JSON file asynchronously."""
    try:
        async with aiofiles.open(output_path, "w") as f:
            await f.write(json.dumps(data, indent=4))
    except Exception as e:
        logger.error(f"Failed to save JSON output to {output_path}: {e}")
        # Not raising HTTPException here, as this is a helper. Error should be handled by caller.


async def _save_error_file(error_file_path: Path, raw_text: str) -> None:
    """Saves the raw, malformed text to an error file asynchronously."""
    try:
        error_file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(error_file_path, "w") as f:
            await f.write(raw_text)
        logger.info(f"Saved malformed JSON error to: {error_file_path}")
    except Exception as e:
        logger.error(f"Failed to save error file to {error_file_path}: {e}")


def _prepare_output_paths(
    user_provided_company_name: str,
    period_end_date_str: str | None,
    original_pdf_name: str,
) -> tuple[Path, str, Path | None]:
    """
    Prepares output directory and filename using the user-provided company name.
    Returns (json_output_path, json_output_path_str, error_file_path_if_needed).
    """
    sanitized_company_name = sanitize_company_name(user_provided_company_name)
    company_output_dir = OUTPUT_FILES_DIR / f"{sanitized_company_name}_data"
    errors_dir = company_output_dir / ERRORS_DIR_NAME

    original_pdf_stem = Path(original_pdf_name).stem.replace(" ", "_")

    if not period_end_date_str:  # Fallback if date parsing failed or not provided by Gemini
        logger.warning(f"Period end date not available for {original_pdf_name}. Using PDF name for JSON output.")
        json_filename = f"{original_pdf_stem}.json"
        error_filename = f"{original_pdf_stem}_error.txt"
    else:
        try:
            # Assuming period_end_date_str is "YYYY-MM-DD"
            date_obj = date.fromisoformat(period_end_date_str)
            formatted_date = date_obj.strftime("%d_%m_%Y")
            json_filename = f"{formatted_date}.json"
            error_filename = f"{formatted_date}_error.txt"  # Error file also uses date if available
        except ValueError:
            logger.warning(f"Invalid date format '{period_end_date_str}' for {original_pdf_name}. Using PDF name for JSON output.")
            json_filename = f"{original_pdf_stem}.json"
            error_filename = f"{original_pdf_stem}_error.txt"

    json_output_path = company_output_dir / json_filename
    error_file_path = errors_dir / error_filename  # Path for potential error file

    # Ensure directories exist
    company_output_dir.mkdir(parents=True, exist_ok=True)
    # errors_dir will be created by _save_error_file if needed

    return json_output_path, str(json_output_path), error_file_path


async def _process_single_pdf(pdf_path: Path, user_provided_company_name: str, semaphore: asyncio.Semaphore) -> dict[str, Any]:
    """Processes a single PDF: calls Gemini, handles response, saves output/error."""
    async with semaphore:
        logger.info(f"Processing PDF: {pdf_path} for company: {user_provided_company_name}")
        try:
            # Call the controller function that interacts with the Gemini API
            # The controller now doesn't extract company_name, so we rely on user_provided_company_name
            financial_data = await generate_financial_data(pdf_path)

            if not financial_data:
                logger.error(f"No data returned from Gemini for {pdf_path}")
                return {"file": str(pdf_path), "status": "error", "detail": "No data from model"}

            # Check for errors from Gemini (e.g., JSONDecodeError)
            if financial_data.get("error"):
                logger.error(f"Error from Gemini for {pdf_path}: {financial_data.get('detail')}")
                # Prepare paths using user_provided_company_name and a placeholder date or PDF name if date is missing
                # The period_end_date might be missing if the error occurred before Gemini could provide it
                output_json_path, _, error_file_path = _prepare_output_paths(
                    user_provided_company_name=user_provided_company_name,
                    period_end_date_str=financial_data.get("period_end_date"),  # May be None
                    original_pdf_name=pdf_path.name,
                )
                if error_file_path and financial_data.get("raw_text"):
                    await _save_error_file(error_file_path, financial_data["raw_text"])
                return {
                    "file": str(pdf_path),
                    "status": "error",
                    "detail": financial_data.get("detail", "Unknown error from Gemini"),
                    "error_file": str(error_file_path) if error_file_path else None,
                }

            # Prepare output paths using the USER-PROVIDED company name and extracted date
            output_json_path, output_json_str, _ = _prepare_output_paths(
                user_provided_company_name=user_provided_company_name,
                period_end_date_str=financial_data.get("period_end_date"),
                original_pdf_name=pdf_path.name,
            )

            await _save_json_output(output_json_path, financial_data)
            logger.info(f"Successfully processed and saved: {output_json_path}")
            return {"file": str(pdf_path), "status": "success", "output_path": output_json_str, "data_from_gemini": financial_data}  # Optionally return gemini data in response

        except HTTPException as http_exc:  # Catch HTTPExceptions from generate_financial_data
            logger.error(f"HTTPException during processing {pdf_path}: {http_exc.detail}")
            return {"file": str(pdf_path), "status": "error", "detail": http_exc.detail}
        except Exception as e:
            logger.error(f"Unexpected error processing {pdf_path}: {e}", exc_info=True)
            # Save error info if possible
            _, _, error_file_path_on_exc = _prepare_output_paths(
                user_provided_company_name=user_provided_company_name,
                period_end_date_str=None,  # Date might not be available
                original_pdf_name=pdf_path.name,
            )
            if error_file_path_on_exc:
                await _save_error_file(error_file_path_on_exc, f"Unexpected error: {e!s}\nTraceback: {traceback.format_exc()}")

            return {"file": str(pdf_path), "status": "error", "detail": f"Unexpected error: {e!s}", "error_file": str(error_file_path_on_exc) if error_file_path_on_exc else None}


@router.post(
    "/extract-financial-data/",
    status_code=status.HTTP_200_OK,
    summary="Extract Financial Data from PDFs in a Directory",
    description=(
        "Processes all PDF files in a specified directory to extract financial data. "
        "The directory should contain PDF financial reports for a SINGLE company, "
        "and the company's name must be provided in the request."
    ),
)
async def extract_financial_data(request_data: DataExtractionRequest) -> dict[str, Any]:
    """
    Endpoint to extract financial data from all PDF files in a given directory.
    Requires company name and a directory path.
    The directory must contain PDF files for the specified company only.
    """
    if not request_data.directory_path.exists() or not request_data.directory_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid directory_path: {request_data.directory_path}. Ensure it exists and is a directory.",
        )

    pdf_files = list(request_data.directory_path.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in directory: {request_data.directory_path}")
        return {
            "message": "No PDF files found in the specified directory.",
            "company_name": request_data.company_name,
            "directory_path": str(request_data.directory_path),
            "files_processed": 0,
            "results": [],
        }

    logger.info(f"Starting financial data extraction for company: {request_data.company_name} from directory: {request_data.directory_path}. Found {len(pdf_files)} PDF(s).")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_GEMINI_CALLS)
    tasks = [_process_single_pdf(pdf_path, request_data.company_name, semaphore) for pdf_path in pdf_files]
    results = await asyncio.gather(*tasks, return_exceptions=False)  # Let _process_single_pdf handle exceptions internally

    successful_extractions = [res for res in results if res.get("status") == "success"]
    failed_extractions = [res for res in results if res.get("status") == "error"]

    summary_message = f"Processed {len(pdf_files)} PDF(s) for company '{request_data.company_name}'. {len(successful_extractions)} successful, {len(failed_extractions)} failed."
    logger.info(summary_message)

    return {
        "message": summary_message,
        "company_name": request_data.company_name,
        "directory_path": str(request_data.directory_path),
        "total_files_found": len(pdf_files),
        "successful_extractions": len(successful_extractions),
        "failed_extractions": len(failed_extractions),
        "detailed_results": results,
    }
