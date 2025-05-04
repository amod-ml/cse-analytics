from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.controllers.pdf_download_controller import download_pdfs_for_company
from app.utils.structlogger import logger

router = APIRouter()


@router.post("/download-pdfs/{company_name}", status_code=202)
async def trigger_pdf_download(company_name: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    """
    Triggers the asynchronous download of PDF reports for a given company.
    Reads URLs from urls_{company_name}.json and saves PDFs to ./{company_name}/
    """
    logger.info(f"Received request to download PDFs for company: {company_name}")
    if not company_name or not company_name.isalnum():  # Basic validation
        raise HTTPException(status_code=400, detail="Invalid company name format. Use alphanumeric characters only.")

    json_path = Path(f"urls_{company_name}.json")
    if not json_path.is_file():
        raise HTTPException(status_code=404, detail=f"No JSON file found for company '{company_name}' in root directory.")

    # Add the download task to run in the background
    background_tasks.add_task(download_pdfs_for_company, company_name)

    return {"message": f"Accepted request to download PDFs for {company_name}. Process running in background."}
