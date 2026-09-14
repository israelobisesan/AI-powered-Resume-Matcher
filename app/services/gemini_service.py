import json
import time
from google import genai
from config import Config


def get_gemini_client():
    """Initialize and return a Gemini client."""
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        return None
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception:
        return None


def match_resume_to_job(resume_text, job_description, required_skills=None, preferred_skills=None):
    """Use Gemini to comprehensively match a resume to a job description.

    Returns a dict with all match data:
    - final_score (0-100)
    - skill_score (0-100)
    - experience_score (0-100)
    - education_score (0-100)
    - matched_skills (list)
    - missing_skills (list)
    - explanation (string)
    - strengths (string)
    - weaknesses (string)

    Raises an exception if Gemini is unavailable.
    """
    client = get_gemini_client()
    if not client:
        raise Exception('Gemini API is not configured. Please set GEMINI_API_KEY in your .env file.')

    req_skills_text = ', '.join(required_skills) if required_skills else 'Not specified'
    pref_skills_text = ', '.join(preferred_skills) if preferred_skills else 'Not specified'

    prompt = f"""You are an expert HR analyst and talent matcher. Analyze how well the following resume matches the job description and provide a comprehensive match assessment.

RESUME:
{resume_text[:4000]}

JOB DESCRIPTION:
{job_description[:4000]}

REQUIRED SKILLS (from job posting): {req_skills_text}
PREFERRED SKILLS (from job posting): {pref_skills_text}

Provide your analysis as a JSON object with exactly these fields:
- "final_score": a number from 0 to 100 representing the overall match quality
- "skill_score": a number from 0 to 100 representing how well the candidate's skills match the required skills (consider semantic similarity, e.g., "Python" matches "Python Developer", "JavaScript" matches "JavaScript programming")
- "experience_score": a number from 0 to 100 representing how well the candidate's experience level matches the job requirements
- "education_score": a number from 0 to 100 representing how well the candidate's education matches the job requirements
- "matched_skills": an array of skill strings from the required skills that the candidate HAS (use the exact required skill names)
- "missing_skills": an array of skill strings from the required skills that the candidate LACKS (use the exact required skill names)
- "explanation": a detailed 3-5 sentence explanation of the match quality, referencing specific skills, experience, and education. Be specific and practical.
- "strengths": a brief 1-2 sentence summary of the strongest aspects
- "weaknesses": a brief 1-2 sentence summary of areas for improvement

IMPORTANT RULES:
- For skill matching, use semantic understanding: "Python" matches "Python Developer", "React" matches "React.js", "JS" matches "JavaScript"
- The final_score should be a weighted combination but also consider factors not captured by simple scoring
- Be honest and accurate in your assessment
- Return ONLY the JSON object, no other text or markdown formatting"""

    try:
        interaction = client.interactions.create(
            model=Config.GEMINI_MODEL,
            input=prompt
        )
        response_text = interaction.output_text.strip()

        # Clean up response
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        if response_text.endswith('```'):
            response_text = response_text[:-3].strip()

        result = json.loads(response_text)

        return {
            'final_score': min(100, max(0, int(result.get('final_score', 50)))),
            'skill_score': min(100, max(0, int(result.get('skill_score', 50)))),
            'experience_score': min(100, max(0, int(result.get('experience_score', 50)))),
            'education_score': min(100, max(0, int(result.get('education_score', 50)))),
            'matched_skills': result.get('matched_skills', []),
            'missing_skills': result.get('missing_skills', []),
            'explanation': result.get('explanation', 'Analysis completed.'),
            'strengths': result.get('strengths', ''),
            'weaknesses': result.get('weaknesses', '')
        }
    except json.JSONDecodeError:
        raise Exception('Gemini returned an invalid response. Please try again.')
    except Exception as e:
        raise Exception(f'Gemini API error: {str(e)}')


def match_resume_to_jobs(resume_text, jobs_data):
    """Use Gemini to match ONE resume against MULTIPLE jobs in a single API call.

    Args:
        resume_text: The candidate's resume text
        jobs_data: List of dicts, each with:
            - job_id (int)
            - title (str)
            - description (str)
            - required_skills (list)
            - preferred_skills (list)

    Returns:
        Dict mapping job_id -> match result dict

    Raises an exception if Gemini is unavailable.
    """
    client = get_gemini_client()
    if not client:
        raise Exception('Gemini API is not configured. Please set GEMINI_API_KEY in your .env file.')

    if not jobs_data:
        return {}

    # Build jobs section for the prompt
    jobs_text = ""
    for i, job in enumerate(jobs_data, 1):
        req_skills = ', '.join(job.get('required_skills', [])) or 'Not specified'
        pref_skills = ', '.join(job.get('preferred_skills', [])) or 'Not specified'
        jobs_text += f"""
JOB {i} (ID: {job['job_id']}):
Title: {job['title']}
Description: {job['description'][:1000]}
Required Skills: {req_skills}
Preferred Skills: {pref_skills}
"""

    prompt = f"""You are an expert HR analyst and talent matcher. Analyze how well the following resume matches EACH of the job descriptions below. Return a separate assessment for EACH job.

RESUME:
{resume_text[:4000]}

JOBS TO EVALUATE:
{jobs_text}

For EACH job, provide a JSON object with exactly these fields:
- "job_id": the job ID number
- "final_score": a number from 0 to 100 representing the overall match quality
- "skill_score": a number from 0 to 100 for skill match (use semantic understanding: "Python" matches "Python Developer", "React" matches "React.js")
- "experience_score": a number from 0 to 100 for experience match
- "education_score": a number from 0 to 100 for education match
- "matched_skills": an array of required skills the candidate HAS
- "missing_skills": an array of required skills the candidate LACKS
- "explanation": a 2-3 sentence explanation of the match

Return a JSON array containing one object for each job. Return ONLY the JSON array, no other text.

IMPORTANT:
- Evaluate each job independently
- Use semantic understanding for skill matching
- Be honest and accurate
- The array length must match the number of jobs provided"""

    try:
        interaction = client.interactions.create(
            model=Config.GEMINI_MODEL,
            input=prompt
        )
        response_text = interaction.output_text.strip()

        # Clean up response
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        if response_text.endswith('```'):
            response_text = response_text[:-3].strip()

        results = json.loads(response_text)

        # Convert to dict mapping job_id -> match data
        matches = {}
        if isinstance(results, list):
            for result in results:
                try:
                    job_id = int(result.get('job_id', 0))
                except (ValueError, TypeError):
                    continue
                if job_id > 0:
                    matches[job_id] = {
                        'final_score': min(100, max(0, int(result.get('final_score', 50)))),
                        'skill_score': min(100, max(0, int(result.get('skill_score', 50)))),
                        'experience_score': min(100, max(0, int(result.get('experience_score', 50)))),
                        'education_score': min(100, max(0, int(result.get('education_score', 50)))),
                        'matched_skills': result.get('matched_skills', []),
                        'missing_skills': result.get('missing_skills', []),
                        'explanation': result.get('explanation', 'Analysis completed.')
                    }

        return matches
    except json.JSONDecodeError:
        raise Exception('Gemini returned an invalid response. Please try again.')
    except Exception as e:
        raise Exception(f'Gemini API error: {str(e)}')


def generate_explanation(tfidf_score, skill_score, experience_score, education_score,
                         matched_skills, missing_skills, required_skills,
                         resume_text='', job_description=''):
    """Use Gemini to generate a rich, personalized match explanation.

    Returns a detailed explanation string.
    Raises an exception if Gemini is unavailable.
    """
    client = get_gemini_client()
    if not client:
        raise Exception('Gemini API is not configured. Please set GEMINI_API_KEY in your .env file.')

    prompt = f"""You are an expert career advisor. Based on the following match data, write a detailed, personalized explanation of how well this candidate matches the job.

MATCH SCORES:
- TF-IDF Text Similarity: {tfidf_score}%
- Skill Match: {skill_score}%
- Experience Match: {experience_score}%
- Education Match: {education_score}%

MATCHED SKILLS: {', '.join(matched_skills) if matched_skills else 'None'}
MISSING SKILLS: {', '.join(missing_skills) if missing_skills else 'None'}
REQUIRED SKILLS: {', '.join(required_skills) if required_skills else 'None'}

Write a clear, professional explanation (3-5 sentences) that:
1. Summarizes the overall match quality
2. Highlights the strongest matching areas
3. Notes any gaps or areas for improvement
4. Gives a practical recommendation

Be specific and reference the actual skills and scores. Do not use generic statements."""

    try:
        interaction = client.interactions.create(
            model=Config.GEMINI_MODEL,
            input=prompt
        )
        return interaction.output_text.strip()
    except Exception as e:
        raise Exception(f'Gemini API error: {str(e)}')


def suggest_skills(job_description):
    """Use Gemini to suggest required and preferred skills from a job description.

    Returns a dict with required_skills and preferred_skills lists.
    Raises an exception if Gemini is unavailable.
    """
    client = get_gemini_client()
    if not client:
        raise Exception('Gemini API is not configured. Please set GEMINI_API_KEY in your .env file.')

    prompt = f"""Analyze the following job description and extract the required and preferred skills.

JOB DESCRIPTION:
{job_description[:3000]}

Provide your response as a JSON object with exactly these fields:
- "required_skills": an array of skill strings that are mandatory/required for this role
- "preferred_skills": an array of skill strings that are nice-to-have/preferred

Rules:
- Include specific technical skills (e.g., "Python", "Flask", "SQL")
- Include professional skills where mentioned (e.g., "Communication", "Leadership")
- Keep skills concise (1-3 words each)
- Do not include generic terms like "experience" or "knowledge"
- Return 5-10 required skills and 3-5 preferred skills

Return ONLY the JSON object, no other text."""

    try:
        interaction = client.interactions.create(
            model=Config.GEMINI_MODEL,
            input=prompt
        )
        response_text = interaction.output_text.strip()

        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]

        result = json.loads(response_text)
        return {
            'required_skills': result.get('required_skills', []),
            'preferred_skills': result.get('preferred_skills', [])
        }
    except json.JSONDecodeError:
        return {
            'required_skills': [],
            'preferred_skills': []
        }
    except Exception as e:
        raise Exception(f'Gemini API error: {str(e)}')
