"""Safe CSV/XLSX parsing shared by Phase 2 bulk-import endpoints."""
from io import BytesIO

import pandas as pd

from app.core.config import settings


def parse_tabular_upload(file_name: str, content: bytes) -> list[dict]:
    suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    if suffix == "csv":
        frame = pd.read_csv(BytesIO(content))
    elif suffix in {"xlsx", "xls"}:
        frame = pd.read_excel(BytesIO(content))
    else:
        raise ValueError("Only CSV and Excel files are supported")
    if len(frame.index) > settings.MAX_IMPORT_ROWS:
        raise ValueError(f"Import exceeds the {settings.MAX_IMPORT_ROWS}-row limit")
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    rows: list[dict] = []
    for row in frame.to_dict(orient="records"):
        cleaned: dict = {}
        for key, value in row.items():
            if value is None or pd.isna(value):
                continue
            cleaned[str(key)] = value.item() if hasattr(value, "item") else value
        rows.append(cleaned)
    return rows
