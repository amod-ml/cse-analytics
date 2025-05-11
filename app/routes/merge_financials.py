from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.controllers.merge_financials_controller import (
    merge_quarterly_files,
    save_outputs,
)
from app.models import MergeQuarterliesResponse

router = APIRouter()


@router.post(
    "/merge-quarterlies",
    status_code=status.HTTP_201_CREATED,
)
def merge_quarterlies(
    json_dir: Annotated[
        Path,
        Query(..., description="Directory containing the JSON reports"),
    ],
) -> MergeQuarterliesResponse:
    """
    Merge all quarterly JSON files in *json_dir* and persist combined CSV/Parquet.
    """
    if not json_dir.exists() or not json_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{json_dir} is not a valid directory",
        )

    quarterly_df = merge_quarterly_files(json_dir)
    paths = save_outputs(quarterly_df, json_dir)

    return MergeQuarterliesResponse(
        rows=len(quarterly_df),
        csv_path=paths["csv"],
        parquet_path=paths["parquet"],
        preview=quarterly_df.head().to_dict(orient="records"),
    )
