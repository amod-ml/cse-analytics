from fastapi import FastAPI

from app.routes import download_pdfs
from app.utils.structlogger import logger

app = FastAPI(title="CSE Analytics API")

# Include the PDF download router
app.include_router(download_pdfs.router, prefix="/api/v1", tags=["PDF Downloads"])


@app.get("/")
def read_root() -> dict[str, str]:
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to CSE Analytics API"}
