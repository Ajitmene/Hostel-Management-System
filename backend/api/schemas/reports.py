from pydantic import BaseModel


class ReportOut(BaseModel):
    title: str
    columns: list[str]
    rows: list[list]
    summary: dict
