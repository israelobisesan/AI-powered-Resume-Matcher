import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def preprocess_text(text):
    """Preprocess text for TF-IDF vectorization."""
    if not text:
        return ''

    import re
    text = text.lower()
    text = re.sub(r'[^\w\s\+\#\.]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'shall', 'can', 'need', 'dare',
        'this', 'that', 'these', 'those', 'i', 'me', 'my', 'we', 'our',
        'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its',
        'they', 'them', 'their', 'what', 'which', 'who', 'whom',
        'not', 'no', 'nor', 'so', 'if', 'then', 'than', 'too', 'very',
        'just', 'about', 'above', 'after', 'again', 'all', 'also', 'am',
        'any', 'as', 'because', 'before', 'below', 'between', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such',
        'into', 'only', 'own', 'same', 'through', 'during', 'out',
        'up', 'down', 'here', 'there', 'when', 'where', 'why', 'how',
        'while', 'until', 'since', 'once', 'year', 'years'
    }

    words = text.split()
    words = [w for w in words if w not in stop_words and len(w) > 1]
    return ' '.join(words)


def calculate_tfidf_similarity(resume_text, job_description):
    """Calculate TF-IDF cosine similarity between resume and job description."""
    if not resume_text or not job_description:
        return 0.0

    processed_resume = preprocess_text(resume_text)
    processed_job = preprocess_text(job_description)

    if not processed_resume or not processed_job:
        return 0.0

    vectorizer = TfidfVectorizer(max_features=5000)
    try:
        tfidf_matrix = vectorizer.fit_transform([processed_resume, processed_job])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return round(float(similarity[0][0]) * 100, 2)
    except Exception:
        return 0.0


def calculate_skill_score(candidate_skills, required_skills):
    """Calculate skill match score (kept for test compatibility).
    In production, Gemini handles skill matching via match_resume_to_job().
    """
    if not required_skills:
        return 100.0, [], []

    if isinstance(required_skills, str):
        try:
            required_skills = json.loads(required_skills)
        except (json.JSONDecodeError, TypeError):
            required_skills = [s.strip() for s in required_skills.split(',') if s.strip()]

    if isinstance(candidate_skills, str):
        try:
            candidate_skills = json.loads(candidate_skills)
        except (json.JSONDecodeError, TypeError):
            candidate_skills = [s.strip() for s in candidate_skills.split(',') if s.strip()]

    candidate_lower = {s.lower().strip() for s in candidate_skills}
    required_lower = {s.lower().strip() for s in required_skills}

    matched = [s for s in required_skills if s.lower().strip() in candidate_lower]
    missing = [s for s in required_skills if s.lower().strip() not in candidate_lower]

    if not required_skills:
        score = 100.0
    else:
        score = round((len(matched) / len(required_skills)) * 100, 2)

    return score, matched, missing


def calculate_experience_score(candidate_years, required_years):
    """Calculate experience match score (kept for test compatibility)."""
    if not required_years or required_years == 0:
        return 100.0

    if candidate_years >= required_years:
        return 100.0

    return round((candidate_years / required_years) * 100, 2)


def calculate_education_score(candidate_education, requirement):
    """Calculate education match score (kept for test compatibility)."""
    if not requirement:
        return 100.0

    if not candidate_education:
        return 20.0

    degree_hierarchy = {
        'phd': 5, 'doctorate': 5, 'doctor': 5,
        'master': 4, 'mba': 4, 'm.sc': 4, 'ma': 4, 'm.sc.': 4, 'm.a.': 4,
        'bachelor': 3, 'b.sc': 3, 'ba': 3, 'b.sc.': 3, 'b.a.': 3, 'b.eng': 3,
        'hnd': 2, 'nd': 1, 'diploma': 1, 'certificate': 1
    }

    req_level = 0
    req_lower = requirement.lower()
    for key, level in degree_hierarchy.items():
        if key in req_lower:
            req_level = level
            break

    if req_level == 0:
        return 80.0

    highest_candidate_level = 0
    for edu in candidate_education:
        degree = edu.get('degree', '').lower() if isinstance(edu, dict) else str(edu).lower()
        for key, level in degree_hierarchy.items():
            if key in degree:
                highest_candidate_level = max(highest_candidate_level, level)
                break

    if highest_candidate_level >= req_level:
        return 100.0
    elif highest_candidate_level > 0:
        return round((highest_candidate_level / req_level) * 80, 2)
    else:
        return 20.0


def calculate_final_score(tfidf_score, skill_score, experience_score, education_score):
    """Calculate weighted final score (kept for test compatibility)."""
    from config import Config
    final = (
        tfidf_score * Config.TFIDF_WEIGHT +
        skill_score * Config.SKILL_WEIGHT +
        experience_score * Config.EXPERIENCE_WEIGHT +
        education_score * Config.EDUCATION_WEIGHT
    )
    return round(final, 2)


def generate_explanation(final_score, skill_score, experience_score, education_score,
                         matched_skills, missing_skills, required_skills,
                         resume_text='', job_description=''):
    """Generate explanation using Gemini AI. Falls back to basic text if Gemini fails."""
    from app.services.gemini_service import generate_explanation as gemini_explanation
    try:
        return gemini_explanation(
            tfidf_score=0,
            skill_score=skill_score,
            experience_score=experience_score,
            education_score=education_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            required_skills=required_skills,
            resume_text=resume_text,
            job_description=job_description
        )
    except Exception as e:
        return f'Explanation unavailable: {str(e)[:200]}'
