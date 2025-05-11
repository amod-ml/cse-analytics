from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ReportItem(BaseModel):
    details: str
    download_url: HttpUrl


class ReportList(BaseModel):
    results: list[ReportItem]


class FinancialDataOutput(BaseModel):
    company_name: Optional[str] = None
    period_end_date: Optional[str] = None
    currency: Optional[str] = None
    unit: Optional[str] = None
    revenue: Optional[float] = None
    cost_of_sales: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_expenses: Optional[float] = None
    profit_before_tax: Optional[float] = None
    net_income_parent: Optional[float] = None


class DataExtractionRequest(BaseModel):
    company_name: str = Field(..., description="Name of the company. All PDFs in the 'directory_path' must belong to this company.")
    directory_path: Path = Field(..., description="Path to a directory containing PDF financial reports for the specified company.")

    @model_validator(mode="after")
    def validate_directory_path(self) -> "DataExtractionRequest":
        if not self.directory_path.exists():
            raise ValueError(f"Directory not found: {self.directory_path}")
        if not self.directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.directory_path}")
        # Optional: Check if directory is empty or contains non-PDFs, though current logic filters for PDFs.
        return self


class MergeQuarterliesResponse(BaseModel):
    """Response returned after successfully merging the quarterly JSON files."""

    rows: int = Field(..., description="Number of rows written to the master table")
    csv_path: str = Field(..., description="Absolute path of the generated CSV file")
    parquet_path: str = Field(..., description="Absolute path of the generated Parquet file")
    preview: list[dict[str, Any]] = Field(..., description="The first five rows (for a quick sanity check)")
