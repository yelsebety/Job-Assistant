from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import AnalyzeRequest, AnalyzeResponse, ResumeUploadResponse
from parser import extract_text_from_pdf
from prompts import EXTRACT_REQUIREMENTS_PROMPT, ANALYZE_MATCH_PROMPT
from llm import generate_json

load_dotenv()

app = FastAPI(title="AI Job-Application Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    file_bytes = await file.read()

    try:
        text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return ResumeUploadResponse(extracted_text=text)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest):
    if not payload.resume_text.strip() or not payload.job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Both resume_text and job_description are required.",
        )

    try:
        # Stage 1: extract structured requirements from the job description
        requirements = generate_json(
            EXTRACT_REQUIREMENTS_PROMPT.format(job_description=payload.job_description)
        )

        # Stage 2: compare resume against those requirements
        result = generate_json(
            ANALYZE_MATCH_PROMPT.format(
                requirements_json=requirements,
                resume_text=payload.resume_text,
            )
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        return AnalyzeResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Model output did not match expected schema: {e}",
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
