# AI Job-Application Assistant

Paste a job description and your resume — get back a match score, the
keywords you're missing, resume bullets rewritten to match the posting's
language, and a tailored cover letter draft.

![Match results screenshot](docs/screenshot.png)
# Website
   🔗 **[Live demo](https://job-assistant-production-3056.up.railway.app/)**

## Why

Tailoring a resume and cover letter to every job posting is the single
highest-leverage thing you can do in a job search, and also the thing
almost nobody has time to actually do well. This automates the tedious
comparison step so you can focus on making sure the content is honest
and accurate.

## How it works

1. Your resume (pasted or uploaded as a PDF) and a job description go in.
2. Stage 1: the model extracts structured requirements from the job
   posting (required skills, preferred skills, experience level, tone).
3. Stage 2: the model compares your resume against those requirements
   and returns a match score, missing keywords, tailored bullet points,
   and a cover letter draft — as structured JSON, not free-form text.

Splitting the analysis into two LLM calls (extract, then compare) gives
more reliable output than asking one prompt to do everything at once.

## Tech stack

- **FastAPI** — backend API
- **Google Gemini API** (`google-genai`) — free-tier LLM, with automatic
  retry and model fallback if a given model is overloaded or retired
- **pdfplumber** — PDF resume text extraction
- **Vanilla HTML/CSS/JS** — custom dark-themed frontend, no build step,
  no framework

## Running locally

```bash
git clone <your-repo-url>
cd job-assistant
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then add your GEMINI_API_KEY
uvicorn main:app --reload
```

Open http://localhost:8000

Get a free Gemini API key at https://aistudio.google.com/apikey

## API

`POST /upload-resume` — multipart PDF upload, returns extracted text

`POST /analyze`
```json
{
  "resume_text": "...",
  "job_description": "..."
}
```
returns
```json
{
  "match_score": 78,
  "missing_keywords": ["Docker", "CI/CD"],
  "tailored_bullets": ["..."],
  "cover_letter_draft": "..."
}
```

## Deployment

A `Procfile` is included for Railway or Render:

1. Push this repo to GitHub
2. Create a new web service on [Railway](https://railway.app) or
   [Render](https://render.com), pointing at the repo
3. Add `GEMINI_API_KEY` as an environment variable in the dashboard
4. Deploy — the platform reads the `Procfile` automatically

Free-tier deploys spin down when idle, so the first request after
inactivity can take 10-30 seconds.

## Notes

- The model is instructed not to fabricate experience — tailored bullets
  are rewrites of real resume content, not invented achievements.
- Google retires Gemini models on a rolling schedule. `llm.py` tries a
  short list of fallback models and retries automatically on overload,
  but if all models in `MODEL_CANDIDATES` eventually get retired, check
  https://ai.google.dev/gemini-api/docs/deprecations and update the list.
- Dependency versions in `requirements.txt` are pinned for reproducibility.

## License

MIT — see [LICENSE](LICENSE).
