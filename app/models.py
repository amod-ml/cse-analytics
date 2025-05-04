from pydantic import BaseModel, HttpUrl


class ReportItem(BaseModel):
    details: str
    download_url: HttpUrl


class ReportList(BaseModel):
    results: list[ReportItem]
