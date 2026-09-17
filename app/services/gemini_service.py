import json
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
