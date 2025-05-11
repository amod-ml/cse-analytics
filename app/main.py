from fastapi import FastAPI

from app.routes import download_pdfs, extract_data, merge_financials
from app.utils.structlogger import logger

app = FastAPI(title="CSE Analytics API")

# Include the PDF download router
app.include_router(download_pdfs.router, prefix="/api/v1", tags=["PDF Downloads"])

# Include the data extraction router
app.include_router(extract_data.router, prefix="/api/v1", tags=["Data Extraction"])

# Include the financial-data merge router
app.include_router(merge_financials.router, prefix="/api/v1", tags=["Data Merge"])


@app.get("/")
def read_root() -> dict[str, str]:
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to CSE Analytics API"}
