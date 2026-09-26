"""
Two-stage prompt design:
  1. Extract structured requirements from the raw job description.
  2. Compare the resume against those requirements and produce
     a match score, missing keywords, tailored bullets, and a cover letter.

Splitting it into two calls makes each step more reliable than asking
one giant prompt to do everything at once.
"""

EXTRACT_REQUIREMENTS_PROMPT = """You are analyzing a job description to extract structured hiring requirements.

Job Description:
{job_description}

Return ONLY a JSON object (no markdown formatting, no code fences, no preamble) with this exact structure:
{{
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1"],
  "years_experience": "string describing the requirement, e.g. '2-3 years' or 'not specified'",
  "key_tone_keywords": ["keyword1", "keyword2"],
  "role_summary": "one sentence summary of what this role actually does"
}}
"""

ANALYZE_MATCH_PROMPT = """You are an experienced career coach helping a candidate tailor their resume to a specific job posting.

Job Requirements (already extracted from the posting):
{requirements_json}

Candidate's Resume:
{resume_text}

Compare the resume against these requirements honestly. Return ONLY a JSON object (no markdown formatting, no code fences, no preamble) with this exact structure:
{{
  "match_score": 0,
  "missing_keywords": ["keyword1", "keyword2"],
  "tailored_bullets": ["Rewritten resume bullet that better reflects the job's language and priorities", "another bullet"],
  "cover_letter_draft": "A complete, tailored cover letter, 3-4 paragraphs, professional but not generic. It should reference specific requirements from the job description and specific real experience from the resume."
}}

Rules:
- match_score is an integer from 0 to 100. Be honest — do not inflate it.
- tailored_bullets must be based on real content already in the resume. Do not invent experience the candidate doesn't have.
- missing_keywords lists important terms from the job requirements that are absent from the resume.
"""
