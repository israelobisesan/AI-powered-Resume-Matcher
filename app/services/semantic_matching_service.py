import json
from config import Config
from app.services.embedding_service import (
    deserialize_embedding, cosine_similarity_vec, serialize_embedding
)


SKILL_RELATIONSHIPS = {
    # Framework -> Language
    'django': ['python', 'python web frameworks', 'web development'],
    'flask': ['python', 'python web frameworks', 'web development'],
    'fastapi': ['python', 'python web frameworks', 'web development'],
    'express': ['javascript', 'node.js', 'web development'],
    'react': ['javascript', 'frontend development', 'react.js'],
    'react.js': ['javascript', 'frontend development', 'react'],
    'vue': ['javascript', 'frontend development', 'vue.js'],
    'vue.js': ['javascript', 'frontend development', 'vue'],
    'angular': ['javascript', 'frontend development', 'typescript'],
    'next.js': ['react', 'javascript', 'node.js', 'frontend development'],
    'node.js': ['javascript', 'backend development', 'server-side programming'],
    'nodejs': ['javascript', 'backend development', 'server-side programming'],

    # Database -> Data
    'postgresql': ['sql', 'databases', 'relational databases'],
    'postgres': ['sql', 'databases', 'relational databases'],
    'mysql': ['sql', 'databases', 'relational databases'],
    'mongodb': ['databases', 'nosql', 'document databases'],
    'redis': ['databases', 'caching', 'in-memory databases'],
    'sqlite': ['sql', 'databases', 'relational databases'],

    # DevOps -> Infrastructure
    'docker': ['containerization', 'devops', 'deployment'],
    'kubernetes': ['containerization', 'devops', 'orchestration'],
    'aws': ['cloud computing', 'cloud platforms', 'infrastructure'],
    'gcp': ['cloud computing', 'cloud platforms', 'infrastructure'],
    'azure': ['cloud computing', 'cloud platforms', 'infrastructure'],
    'ci/cd': ['devops', 'deployment', 'automation'],

    # Languages -> Domains
    'python': ['programming', 'backend development', 'data science', 'scripting'],
    'javascript': ['programming', 'web development', 'frontend development', 'backend development'],
    'java': ['programming', 'enterprise development', 'backend development'],
    'typescript': ['programming', 'web development', 'frontend development'],
    'sql': ['databases', 'data querying', 'data analysis'],

    # Data -> Roles
    'machine learning': ['data science', 'artificial intelligence', 'predictive modeling'],
    'data analysis': ['data science', 'business intelligence', 'analytics'],
    'power bi': ['data visualization', 'business intelligence', 'data analysis'],
    'tableau': ['data visualization', 'business intelligence', 'data analysis'],
    'pandas': ['data analysis', 'python', 'data manipulation'],
    'numpy': ['data science', 'python', 'numerical computing'],

    # Frontend
    'html': ['web development', 'frontend development'],
    'css': ['web development', 'frontend development', 'styling'],
    'tailwind css': ['web development', 'frontend development', 'css', 'styling'],
    'bootstrap': ['web development', 'frontend development', 'css', 'styling'],

    # Management
    'leadership': ['team management', 'soft skills', 'management'],
    'communication': ['soft skills', 'interpersonal skills'],
    'project management': ['management', 'planning', 'leadership'],
    'agile': ['project management', 'software development methodologies'],
    'scrum': ['project management', 'agile', 'software development methodologies'],
}


def compute_skill_matches(candidate_skills, job_analysis):
    """Compute direct, related, and missing skill matches.

    Returns:
        dict with 'direct', 'related', 'missing' lists
    """
    candidate_set = {s.lower().strip() for s in candidate_skills if s}
    candidate_expanded = set(candidate_set)

    # Expand candidate skills with related terms
    for skill in candidate_set:
        related = SKILL_RELATIONSHIPS.get(skill, [])
        candidate_expanded.update(r.lower() for r in related)

    # Combine critical + important skills from job analysis as "required"
    critical = [s.lower().strip() for s in job_analysis.get('critical_skills', []) if s]
    important = [s.lower().strip() for s in job_analysis.get('important_skills', []) if s]
    preferred = [s.lower().strip() for s in job_analysis.get('preferred_skills', []) if s]
    all_required = critical + important

    direct_matches = []
    related_matches = []
    missing = []

    for skill in all_required:
        if skill in candidate_set:
            direct_matches.append(skill)
        elif skill in candidate_expanded:
            related_matches.append(skill)
        else:
            missing.append(skill)

    # Also check preferred skills
    for skill in preferred:
        if skill in candidate_set:
            direct_matches.append(skill)
        elif skill in candidate_expanded:
            related_matches.append(skill)
        # Preferred skills missing are not critical

    return {
        'direct': direct_matches,
        'related': related_matches,
        'missing': missing,
        'total_required': len(all_required),
    }


def compute_skill_score(skill_matches):
    """Compute skill score (0-100) from skill match results.

    Scoring:
    - Direct match: 100% credit
    - Related match: 60% credit
    - Missing: 0% credit
    """
    total = skill_matches['total_required']
    if total == 0:
        return 100.0

    direct_count = len(skill_matches['direct'])
    related_count = len(skill_matches['related'])

    score = ((direct_count * 1.0 + related_count * 0.6) / total) * 100
    return round(min(100.0, score), 1)


def compute_capability_score(candidate_analysis, job_analysis):
    """Compute capability match score (0-100).

    Compares inferred capabilities from both sides.
    """
    candidate_caps = {c.lower().strip() for c in candidate_analysis.get('inferred_capabilities', []) if c}
    job_caps = {c.lower().strip() for c in job_analysis.get('inferred_capabilities', []) if c}

    if not job_caps:
        return 80.0  # Default if no capabilities required

    # Expand candidate capabilities with related terms
    expanded = set(candidate_caps)
    for cap in candidate_caps:
        related = SKILL_RELATIONSHIPS.get(cap, [])
        expanded.update(r.lower() for r in related)

    matched = len(candidate_caps & job_caps) + len(expanded & job_caps - candidate_caps)
    # Deduplicate: count each job cap only once
    matched_job_caps = set()
    for cap in job_caps:
        if cap in candidate_caps:
            matched_job_caps.add(cap)
        elif cap in expanded:
            matched_job_caps.add(cap)

    score = (len(matched_job_caps) / len(job_caps)) * 100
    return round(min(100.0, score), 1)


def compute_experience_score(candidate_years, candidate_level, job_analysis):
    """Compute experience level match score (0-100).

    Considers both years and level alignment.
    """
    level_map = {'entry': 1, 'mid': 3, 'senior': 5, 'lead': 8, 'executive': 10}
    candidate_num = level_map.get(candidate_level, 3)
    job_num = level_map.get(job_analysis.get('experience_level', 'mid'), 3)
    min_years = job_analysis.get('min_years_experience', 0) or 0

    # Years component
    if min_years > 0:
        if candidate_years >= min_years:
            years_score = 100.0
        else:
            years_score = (candidate_years / min_years) * 100
    else:
        years_score = 100.0

    # Level component
    level_diff = abs(candidate_num - job_num)
    if level_diff == 0:
        level_score = 100.0
    elif level_diff == 1:
        level_score = 80.0
    elif level_diff == 2:
        level_score = 50.0
    else:
        level_score = 20.0

    # Over-qualification penalty (mild)
    if candidate_num > job_num + 2:
        level_score = max(40.0, level_score)

    score = (years_score * 0.6 + level_score * 0.4)
    return round(min(100.0, score), 1)


def compute_education_score(candidate_education_level, job_analysis):
    """Compute education match score (0-100)."""
    level_hierarchy = {
        'none': 0, 'high_school': 1, 'diploma': 2,
        'bachelors': 3, 'masters': 4, 'phd': 5
    }

    candidate_level = level_hierarchy.get(candidate_education_level, 0)
    req_level_str = job_analysis.get('education_requirement', 'none') or 'none'

    # Normalize requirement
    req_lower = req_level_str.lower()
    if 'phd' in req_lower or 'doctorate' in req_lower:
        req_level = 5
    elif 'master' in req_lower or 'mba' in req_lower:
        req_level = 4
    elif 'bachelor' in req_lower or 'b.sc' in req_lower or 'ba ' in req_lower:
        req_level = 3
    elif 'diploma' in req_lower or 'hnd' in req_lower:
        req_level = 2
    elif 'high_school' in req_lower or 'secondary' in req_lower:
        req_level = 1
    else:
        req_level = 0

    if req_level == 0:
        return 90.0  # No specific requirement

    if candidate_level >= req_level:
        return 100.0
    elif candidate_level > 0:
        return round((candidate_level / req_level) * 80, 1)
    else:
        return 20.0


def compute_semantic_score(resume_embedding, job_embedding):
    """Compute semantic similarity score from embeddings."""
    sim = cosine_similarity_vec(resume_embedding, job_embedding)
    return round(max(0.0, sim * 100), 1)


def compute_final_score(semantic_score, skill_score, capability_score,
                        experience_score, education_score):
    """Compute weighted final score using MATCH_WEIGHTS from config."""
    weights = Config.MATCH_WEIGHTS
    final = (
        semantic_score * weights['semantic'] +
        skill_score * weights['skills'] +
        capability_score * weights['capabilities'] +
        experience_score * weights['experience'] +
        education_score * weights['education']
    )
    return round(min(100.0, final), 1)


def generate_deterministic_explanation(semantic_score, skill_score, capability_score,
                                       experience_score, education_score, final_score,
                                       skill_matches, candidate_analysis, job_analysis):
    """Generate a match explanation deterministically from stored analysis.

    No LLM call — pure template-based from the structured data.
    """
    parts = []

    # Overall assessment
    if final_score >= 80:
        parts.append(f"Strong overall match ({final_score}%). This candidate aligns well with the {job_analysis.get('primary_role', 'role')} position.")
    elif final_score >= 60:
        parts.append(f"Good overall match ({final_score}%). The candidate has relevant qualifications for the {job_analysis.get('primary_role', 'role')} position.")
    elif final_score >= 40:
        parts.append(f"Moderate match ({final_score}%). The candidate has some relevant qualifications but there are notable gaps.")
    else:
        parts.append(f"Lower match ({final_score}%). The candidate's background may not align closely with this role's requirements.")

    # Skills
    direct = skill_matches.get('direct', [])
    related = skill_matches.get('related', [])
    missing = skill_matches.get('missing', [])

    if direct:
        parts.append(f"Direct skill matches include {', '.join(direct[:5])}.")
    if related:
        parts.append(f"Related skills: {', '.join(related[:3])} — these transfer from adjacent technologies.")
    if missing:
        parts.append(f"Missing skills: {', '.join(missing[:3])}.")

    # Semantic
    if semantic_score >= 75:
        parts.append("The candidate's profile shows strong semantic alignment with the role requirements.")
    elif semantic_score >= 50:
        parts.append("There is moderate semantic similarity between the candidate's experience and the role.")

    # Capabilities
    if capability_score >= 70:
        parts.append("The candidate demonstrates the key capabilities needed for this position.")

    # Experience
    if experience_score >= 80:
        parts.append("Experience level is well-aligned with the requirements.")
    elif experience_score < 50:
        parts.append("There may be a gap in experience level compared to what's required.")

    # Education
    if education_score >= 90:
        parts.append("Education requirements are met.")

    return ' '.join(parts)
