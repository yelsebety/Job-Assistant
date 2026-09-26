from pydantic import BaseModel
from typing import List


class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str


class AnalyzeResponse(BaseModel):
    match_score: int
    missing_keywords: List[str]
    tailored_bullets: List[str]
    cover_letter_draft: str


class ResumeUploadResponse(BaseModel):
    extracted_text: str
