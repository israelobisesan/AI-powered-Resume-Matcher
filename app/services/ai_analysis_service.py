import json
import logging
from config import Config
from app.services.gemini_service import get_gemini_client

logger = logging.getLogger(__name__)


RESUME_ANALYSIS_PROMPT = """You are an expert HR analyst. Analyze the following resume and extract a structured semantic understanding.

RESUME TEXT:
{resume_text}

Provide your analysis as a JSON object with exactly these fields:

- "primary_roles": array of job titles this person is best suited for (e.g., ["Python Developer", "Backend Engineer"])
- "related_roles": array of related roles they could also fill (e.g., ["Full Stack Developer", "DevOps Engineer"])
- "domains": array of industry/domain knowledge areas (e.g., ["web development", "data engineering", "fintech"])
- "direct_skills": array of specific technical skills explicitly mentioned (e.g., ["Python", "Flask", "PostgreSQL"])
- "related_skills": array of skills that are closely related to what they've shown (e.g., if they know Django, add "Python web frameworks")
- "inferred_capabilities": array of capabilities you can infer from their experience (e.g., ["API design", "database optimization", "team leadership"])
- "key_responsibilities": array of main responsibility types they've handled (e.g., ["backend development", "database management", "code review"])
- "experience_level": one of "entry", "mid", "senior", "lead", "executive"
- "years_of_experience": estimated total years of professional experience (number)
- "education_level": highest education level ("high_school", "diploma", "bachelors", "masters", "phd")
- "education_field": field of study (e.g., "Computer Science")
- "key_strengths": array of 2-4 strongest aspects of this candidate
- "potential_gaps": array of areas where this candidate might have gaps

IMPORTANT RULES:
- Use semantic understanding: "Django Developer" implies Python expertise, "React" implies JavaScript
- Infer capabilities from responsibilities, not just keywords
- Be specific and practical
- Return ONLY the JSON object, no other text"""


JOB_ANALYSIS_PROMPT = """You are an expert HR analyst. Analyze the following job description and extract a structured semantic understanding.

JOB TITLE: {title}
JOB DESCRIPTION:
{description}

REQUIRED SKILLS: {required_skills}
PREFERRED SKILLS: {preferred_skills}
MINIMUM EXPERIENCE: {min_experience} years
EDUCATION REQUIREMENT: {education_requirement}

Provide your analysis as a JSON object with exactly these fields:

- "primary_role": the main role title for this position (e.g., "Python Backend Developer")
- "related_roles": array of related roles that could also fill this position (e.g., ["Full Stack Developer", "Software Engineer"])
- "domains": array of industry/domain areas (e.g., ["web development", "SaaS", "fintech"])
- "critical_skills": array of skills that are absolutely required (must have)
- "important_skills": array of skills that are strongly preferred (should have)
- "preferred_skills": array of nice-to-have skills
- "inferred_capabilities": array of capabilities the ideal candidate should have (e.g., ["system design", "code review", "mentoring"])
- "key_responsibilities": array of main responsibility types for this role
- "experience_level": required experience level ("entry", "mid", "senior", "lead")
- "min_years_experience": minimum years required (number)
- "education_requirement": normalized education requirement ("none", "high_school", "diploma", "bachelors", "masters", "phd")
- "education_field": preferred field of study

IMPORTANT RULES:
- Classify skills as critical vs important vs preferred based on context
- Critical = mentioned in requirements as mandatory
- Important = mentioned as required but not dealbreaker
- Preferred = mentioned as nice-to-have
- Infer capabilities from responsibilities and requirements
- Return ONLY the JSON object, no other text"""


def analyze_resume(resume_text):
    """Analyze a resume using Gemini to produce structured semantic analysis.

    Returns a dict with structured analysis fields.
    Raises an exception if Gemini is unavailable or returns invalid data.
    """
    client = get_gemini_client()
    if not client:
        raise Exception('Gemini API is not configured. Please set GEMINI_API_KEY in your .env file.')

    prompt = RESUME_ANALYSIS_PROMPT.format(resume_text=resume_text[:6000])

    try:
        interaction = client.interactions.create(
            model=Config.GEMINI_MODEL,
            input=prompt
        )
        response_text = interaction.output_text.strip()

        # Clean markdown code fences
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        if response_text.endswith('```'):
            response_text = response_text[:-3].strip()

        result = json.loads(response_text)

        # Normalize and validate fields
        analysis = {
            'primary_roles': _ensure_list(result.get('primary_roles', [])),
            'related_roles': _ensure_list(result.get('related_roles', [])),
            'domains': _ensure_list(result.get('domains', [])),
            'direct_skills': _ensure_list(result.get('direct_skills', [])),
            'related_skills': _ensure_list(result.get('related_skills', [])),
            'inferred_capabilities': _ensure_list(result.get('inferred_capabilities', [])),
            'key_responsibilities': _ensure_list(result.get('key_responsibilities', [])),
            'experience_level': result.get('experience_level', 'mid'),
            'years_of_experience': _safe_int(result.get('years_of_experience', 3)),
            'education_level': result.get('education_level', 'bachelors'),
            'education_field': result.get('education_field', ''),
            'key_strengths': _ensure_list(result.get('key_strengths', [])),
            'potential_gaps': _ensure_list(result.get('potential_gaps', [])),
        }

        return analysis

    except json.JSONDecodeError:
        raise Exception('Gemini returned an invalid response for resume analysis.')
    except Exception as e:
        raise Exception(f'Gemini API error during resume analysis: {str(e)}')


def analyze_job(title, description, required_skills=None, preferred_skills=None,
                min_experience=0, education_requirement=''):
    """Analyze a job description using Gemini to produce structured semantic analysis.

    Returns a dict with structured analysis fields.
    Raises an exception if Gemini is unavailable or returns invalid data.
    """
    client = get_gemini_client()
    if not client:
        raise Exception('Gemini API is not configured. Please set GEMINI_API_KEY in your .env file.')

    req_skills_text = ', '.join(required_skills) if required_skills else 'Not specified'
    pref_skills_text = ', '.join(preferred_skills) if preferred_skills else 'Not specified'

    prompt = JOB_ANALYSIS_PROMPT.format(
        title=title,
        description=description[:4000],
        required_skills=req_skills_text,
        preferred_skills=pref_skills_text,
        min_experience=min_experience or 0,
        education_requirement=education_requirement or 'Not specified'
    )

    try:
        interaction = client.interactions.create(
            model=Config.GEMINI_MODEL,
            input=prompt
        )
        response_text = interaction.output_text.strip()

        # Clean markdown code fences
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        if response_text.endswith('```'):
            response_text = response_text[:-3].strip()

        result = json.loads(response_text)

        analysis = {
            'primary_role': result.get('primary_role', title),
            'related_roles': _ensure_list(result.get('related_roles', [])),
            'domains': _ensure_list(result.get('domains', [])),
            'critical_skills': _ensure_list(result.get('critical_skills', [])),
            'important_skills': _ensure_list(result.get('important_skills', [])),
            'preferred_skills': _ensure_list(result.get('preferred_skills', [])),
            'inferred_capabilities': _ensure_list(result.get('inferred_capabilities', [])),
            'key_responsibilities': _ensure_list(result.get('key_responsibilities', [])),
            'experience_level': result.get('experience_level', 'mid'),
            'min_years_experience': _safe_int(result.get('min_years_experience', min_experience or 0)),
            'education_requirement': result.get('education_requirement', education_requirement or 'none'),
            'education_field': result.get('education_field', ''),
        }

        return analysis

    except json.JSONDecodeError:
        raise Exception('Gemini returned an invalid response for job analysis.')
    except Exception as e:
        raise Exception(f'Gemini API error during job analysis: {str(e)}')


def _ensure_list(value):
    """Ensure value is a list of strings."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if item]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return []


def _safe_int(value):
    """Safely convert to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
