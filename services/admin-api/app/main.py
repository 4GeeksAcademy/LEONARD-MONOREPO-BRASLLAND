from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="LEONARD Admin API", version="0.1.0")


class HealthRead(BaseModel):
    status: str


@app.get("/health", response_model=HealthRead)
def health() -> HealthRead:
    return HealthRead(status="ok")
