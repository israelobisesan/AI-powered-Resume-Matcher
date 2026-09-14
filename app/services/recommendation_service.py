import json
import logging
from datetime import datetime
from app import db
from app.models.resume import Resume
from app.models.job import Job
from app.models.match import Match
from config import Config

logger = logging.getLogger(__name__)


def ensure_resume_analysis(resume):
    """Ensure resume has been analyzed by Gemini and has embeddings.

    Returns the semantic_analysis dict, or raises on failure.
    """
    from app.services.embedding_service import (
        compute_content_hash, document_needs_analysis, serialize_embedding,
        generate_embedding_from_analysis
    )
    from app.services.ai_analysis_service import analyze_resume

    content_hash = compute_content_hash(resume.raw_text)

    if not document_needs_analysis(resume, content_hash):
        return json.loads(resume.semantic_analysis)

    # Need analysis
    resume.analysis_status = 'processing'
    resume.content_hash = content_hash
    db.session.commit()

    try:
        analysis = analyze_resume(resume.raw_text or '')
        embedding = generate_embedding_from_analysis(analysis)

        resume.semantic_analysis = json.dumps(analysis)
        resume.semantic_embedding = serialize_embedding(embedding)
        resume.analysis_status = 'completed'
        resume.analysis_version = Config.CURRENT_ANALYSIS_VERSION
        resume.analysis_model = Config.GEMINI_MODEL
        resume.analyzed_at = datetime.utcnow()
        db.session.commit()

        return analysis

    except Exception as e:
        logger.error(f'Resume analysis failed for resume {resume.id}: {e}')
        resume.analysis_status = 'failed'
        db.session.commit()
        raise


def ensure_job_analysis(job):
    """Ensure job has been analyzed by Gemini and has embeddings.

    Returns the semantic_analysis dict, or raises on failure.
    """
    from app.services.embedding_service import (
        compute_content_hash, document_needs_analysis, serialize_embedding,
        generate_embedding_from_analysis
    )
    from app.services.ai_analysis_service import analyze_job
    from app.services.nlp_service import extract_skills as nlp_extract_skills

    # Build content hash from all job fields
    hash_input = f"{job.title}|{job.description}|{job.required_skills}|{job.preferred_skills}|{job.minimum_experience}|{job.education_requirement}"
    content_hash = compute_content_hash(hash_input)

    if not document_needs_analysis(job, content_hash):
        return json.loads(job.semantic_analysis)

    # Need analysis
    job.analysis_status = 'processing'
    job.content_hash = content_hash
    db.session.commit()

    req_skills = json.loads(job.required_skills) if job.required_skills else []
    pref_skills = json.loads(job.preferred_skills) if job.preferred_skills else []

    try:
        analysis = analyze_job(
            title=job.title,
            description=job.description or '',
            required_skills=req_skills,
            preferred_skills=pref_skills,
            min_experience=job.minimum_experience or 0,
            education_requirement=job.education_requirement or ''
        )
        embedding = generate_embedding_from_analysis(analysis)

        job.semantic_analysis = json.dumps(analysis)
        job.semantic_embedding = serialize_embedding(embedding)
        job.analysis_status = 'completed'
        job.analysis_version = Config.CURRENT_ANALYSIS_VERSION
        job.analysis_model = Config.GEMINI_MODEL
        job.analyzed_at = datetime.utcnow()
        db.session.commit()

        return analysis

    except Exception as e:
        logger.error(f'Job analysis failed for job {job.id}: {e}')
        job.analysis_status = 'failed'
        db.session.commit()
        raise


def compute_match(resume, job):
    """Compute a full semantic match between a resume and job.

    Uses the new pipeline:
    1. Ensure both are analyzed (Gemini called only if needed)
    2. Generate embeddings from analysis
    3. Compute all scores locally
    4. Cache in Match model

    Returns a dict with all match data.
    """
    from app.services.embedding_service import deserialize_embedding
    from app.services.semantic_matching_service import (
        compute_skill_matches, compute_skill_score, compute_capability_score,
        compute_experience_score, compute_education_score, compute_semantic_score,
        compute_final_score, generate_deterministic_explanation
    )

    # Ensure both documents are analyzed
    resume_analysis = ensure_resume_analysis(resume)
    job_analysis = ensure_job_analysis(job)

    # Get embeddings
    resume_embedding = deserialize_embedding(resume.semantic_embedding)
    job_embedding = deserialize_embedding(job.semantic_embedding)

    # Get candidate skills from NLP extraction
    candidate_skills = json.loads(resume.skills) if resume.skills else []

    # Compute all scores
    skill_matches = compute_skill_matches(candidate_skills, job_analysis)
    skill_score = compute_skill_score(skill_matches)
    capability_score = compute_capability_score(resume_analysis, job_analysis)
    experience_score = compute_experience_score(
        resume_analysis.get('years_of_experience', 0),
        resume_analysis.get('experience_level', 'mid'),
        job_analysis
    )
    education_score = compute_education_score(
        resume_analysis.get('education_level', 'none'),
        job_analysis
    )
    semantic_score = compute_semantic_score(resume_embedding, job_embedding)
    final_score = compute_final_score(semantic_score, skill_score, capability_score,
                                      experience_score, education_score)

    # Generate deterministic explanation
    explanation = generate_deterministic_explanation(
        semantic_score, skill_score, capability_score, experience_score, education_score,
        final_score, skill_matches, resume_analysis, job_analysis
    )

    # Build match data
    match_data = {
        'semantic_score': semantic_score,
        'skill_score': skill_score,
        'capability_score': capability_score,
        'experience_score': experience_score,
        'education_score': education_score,
        'final_score': final_score,
        'direct_matches': skill_matches['direct'],
        'related_matches': skill_matches['related'],
        'missing_skills': skill_matches['missing'],
        'matched_skills': skill_matches['direct'] + skill_matches['related'],  # backward compat
        'explanation': explanation,
    }

    # Cache to database
    save_match(resume.id, job.id, match_data)

    return match_data


def calculate_match(resume, job):
    """Calculate match between a single resume and job.

    Uses caching — only recomputes if no cached result exists or documents changed.
    This is the main entry point used by routes.
    """
    # Check cache first
    existing = Match.query.filter_by(resume_id=resume.id, job_id=job.id).first()
    if existing:
        # Check if either document has been updated since this match was computed
        resume_changed = (resume.content_hash and
                         resume.analysis_status == 'completed' and
                         existing.analysis_version and
                         int(existing.analysis_version.split('_')[0].replace('r', '')) < Config.CURRENT_ANALYSIS_VERSION) if existing.analysis_version else True
        job_changed = (job.content_hash and
                      job.analysis_status == 'completed' and
                      existing.analysis_version and
                      int(existing.analysis_version.split('_')[1].replace('j', '')) < Config.CURRENT_ANALYSIS_VERSION) if existing.analysis_version else True

        if not resume_changed and not job_changed:
            return _match_to_dict(existing)

    # Compute fresh
    try:
        return compute_match(resume, job)
    except Exception as e:
        logger.error(f'Match computation failed for resume {resume.id}, job {job.id}: {e}')
        return {
            'semantic_score': 0.0, 'skill_score': 0.0, 'capability_score': 0.0,
            'experience_score': 0.0, 'education_score': 0.0, 'final_score': 0.0,
            'matched_skills': [], 'missing_skills': [], 'direct_matches': [],
            'related_matches': [], 'explanation': 'Match computation unavailable.'
        }


def get_job_recommendations(user_id, limit=20):
    """Get job recommendations for a job seeker based on their resume.

    Pipeline: analyze resume once → compute scores locally for each job.
    Only ONE Gemini call per unique resume (if not already analyzed).
    """
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    if not resume:
        return []

    # Ensure resume is analyzed (at most one Gemini call)
    try:
        ensure_resume_analysis(resume)
    except Exception as e:
        logger.error(f'Could not analyze resume {resume.id}: {e}')
        return []

    open_jobs = Job.query.filter_by(status='open').all()
    if not open_jobs:
        return []

    recommendations = []
    for job in open_jobs:
        try:
            match_data = calculate_match(resume, job)
            recommendations.append({
                'job': job,
                'match': match_data
            })
        except Exception as e:
            logger.error(f'Could not compute match for job {job.id}: {e}')
            continue

    recommendations.sort(key=lambda x: x['match']['final_score'], reverse=True)
    return recommendations[:limit]


def get_candidate_rankings(job_id):
    """Get ranked candidates for a specific job posting.

    Pipeline: analyze job once → compute scores locally for each resume.
    Only ONE Gemini call per unique job (if not already analyzed).
    """
    job = Job.query.get(job_id)
    if not job:
        return []

    # Ensure job is analyzed (at most one Gemini call)
    try:
        ensure_job_analysis(job)
    except Exception as e:
        logger.error(f'Could not analyze job {job.id}: {e}')
        return []

    resumes = Resume.query.all()
    if not resumes:
        return []

    rankings = []
    for resume in resumes:
        try:
            match_data = calculate_match(resume, job)
            rankings.append({
                'resume': resume,
                'match': match_data
            })
        except Exception as e:
            logger.error(f'Could not compute match for resume {resume.id}: {e}')
            continue

    rankings.sort(key=lambda x: x['match']['final_score'], reverse=True)
    return rankings


def save_match(resume_id, job_id, match_data):
    """Save or update a match record to the database (cache)."""
    existing = Match.query.filter_by(resume_id=resume_id, job_id=job_id).first()

    version_str = f"r{Config.CURRENT_ANALYSIS_VERSION}_j{Config.CURRENT_ANALYSIS_VERSION}"

    if existing:
        existing.semantic_score = match_data.get('semantic_score', 0.0)
        existing.skill_score = match_data['skill_score']
        existing.capability_score = match_data.get('capability_score', 0.0)
        existing.experience_score = match_data['experience_score']
        existing.education_score = match_data['education_score']
        existing.final_score = match_data['final_score']
        existing.direct_matches = json.dumps(match_data.get('direct_matches', []))
        existing.related_matches = json.dumps(match_data.get('related_matches', []))
        existing.missing_skills = json.dumps(match_data.get('missing_skills', []))
        existing.matched_skills = json.dumps(match_data.get('matched_skills', []))
        existing.explanation = match_data['explanation']
        existing.analysis_version = version_str
        db.session.commit()
        return existing

    match = Match(
        resume_id=resume_id,
        job_id=job_id,
        semantic_score=match_data.get('semantic_score', 0.0),
        skill_score=match_data['skill_score'],
        capability_score=match_data.get('capability_score', 0.0),
        experience_score=match_data['experience_score'],
        education_score=match_data['education_score'],
        final_score=match_data['final_score'],
        direct_matches=json.dumps(match_data.get('direct_matches', [])),
        related_matches=json.dumps(match_data.get('related_matches', [])),
        missing_skills=json.dumps(match_data.get('missing_skills', [])),
        matched_skills=json.dumps(match_data.get('matched_skills', [])),
        explanation=match_data['explanation'],
        analysis_version=version_str,
    )
    db.session.add(match)
    db.session.commit()
    return match


def _match_to_dict(match):
    """Convert a Match model instance to a dict for template use."""
    return {
        'semantic_score': match.semantic_score,
        'skill_score': match.skill_score,
        'capability_score': getattr(match, 'capability_score', 0.0),
        'experience_score': match.experience_score,
        'education_score': match.education_score,
        'final_score': match.final_score,
        'matched_skills': json.loads(match.matched_skills) if match.matched_skills else [],
        'missing_skills': json.loads(match.missing_skills) if match.missing_skills else [],
        'direct_matches': json.loads(match.direct_matches) if match.direct_matches else [],
        'related_matches': json.loads(match.related_matches) if match.related_matches else [],
        'explanation': match.explanation or '',
        'tfidf_score': getattr(match, 'tfidf_score', 0.0),
    }


def _parse_skills(skills_raw):
    """Parse skills from JSON string or comma-separated string."""
    if not skills_raw:
        return []
    try:
        return json.loads(skills_raw)
    except (json.JSONDecodeError, TypeError):
        return [s.strip() for s in skills_raw.split(',') if s.strip()]
