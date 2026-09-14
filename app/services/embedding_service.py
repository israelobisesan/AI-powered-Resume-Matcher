import hashlib
import json
import numpy as np


def compute_content_hash(text):
    """Compute SHA-256 hash of document content for change detection."""
    if not text:
        return None
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def document_needs_analysis(document, content_hash):
    """Check if a document needs (re)analysis based on content hash and analysis status.

    Returns True if analysis should be triggered.
    """
    from config import Config

    # Never analyzed
    if document.analysis_status != 'completed':
        return True

    # No content hash stored (e.g. uploaded before semantic system)
    if not document.content_hash:
        return True

    # Content changed
    if document.content_hash != content_hash:
        return True

    # Analysis version outdated
    if (document.analysis_version or 0) < Config.CURRENT_ANALYSIS_VERSION:
        return True

    # No semantic analysis stored
    if not document.semantic_analysis:
        return True

    return False


def serialize_embedding(embedding):
    """Serialize a numpy embedding vector to JSON string for storage."""
    if embedding is None:
        return None
    if isinstance(embedding, np.ndarray):
        return json.dumps(embedding.tolist())
    if isinstance(embedding, list):
        return json.dumps(embedding)
    return None


def deserialize_embedding(embedding_json):
    """Deserialize a JSON string back to a numpy embedding vector."""
    if not embedding_json:
        return None
    try:
        data = json.loads(embedding_json)
        return np.array(data, dtype=np.float32)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


# Fixed vocabulary of tech/domain topics for consistent embedding dimensions.
# Every document gets a vector of exactly this length.
TOPIC_VOCABULARY = [
    # Programming languages
    'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'rust', 'ruby', 'php',
    'swift', 'kotlin', 'scala', 'r', 'matlab', 'sql', 'html', 'css', 'sass',
    # Frameworks
    'django', 'flask', 'fastapi', 'react', 'vue', 'angular', 'next.js', 'node.js',
    'express', 'spring', 'rails', 'laravel', 'ASP.NET',
    # Databases
    'postgresql', 'mysql', 'mongodb', 'redis', 'sqlite', 'elasticsearch', 'oracle', 'cassandra',
    # Cloud & DevOps
    'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'jenkins', 'ci/cd', 'terraform', 'ansible',
    'linux', 'nginx', 'apache',
    # Data & ML
    'machine learning', 'deep learning', 'data science', 'data analysis', 'data engineering',
    'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'spark', 'hadoop',
    'power bi', 'tableau', 'data visualization', 'statistical analysis', 'nlp',
    # Frontend
    'responsive design', 'ui/ux', 'tailwind css', 'bootstrap', 'sass', 'webpack',
    'frontend development', 'component architecture', 'cross-browser',
    # Backend
    'api design', 'rest api', 'graphql', 'microservices', 'authentication', 'authorization',
    'backend development', 'server-side', 'caching', 'message queues',
    # DevOps & Tools
    'git', 'github', 'gitlab', 'jira', 'confluence', 'agile', 'scrum',
    'testing', 'unit testing', 'integration testing', 'ci/cd pipelines',
    # Domains
    'web development', 'mobile development', 'desktop development', 'embedded systems',
    'fintech', 'healthcare', 'e-commerce', 'saas', 'blockchain', 'cybersecurity',
    'iot', 'cloud computing', 'game development',
    # Soft skills
    'leadership', 'team management', 'communication', 'problem solving', 'mentoring',
    'project management', 'cross-functional collaboration', 'stakeholder management',
    # Education levels
    'phd', 'masters', 'bachelors', 'diploma', 'certification',
    # Experience levels
    'entry level', 'mid level', 'senior', 'lead', 'principal', 'executive',
    # Capabilities
    'system design', 'architecture', 'code review', 'debugging', 'optimization',
    'scalability', 'security', 'documentation', 'technical writing',
    'database design', 'data modeling', 'etl', 'data pipelines',
    'team leadership', 'strategic planning', 'risk management',
    # Industries
    'finance', 'banking', 'insurance', 'retail', 'manufacturing',
    'telecommunications', 'education', 'logistics', 'energy',
]

# Pre-computed index map for O(1) lookup
_TOPIC_INDEX = {topic: i for i, topic in enumerate(TOPIC_VOCABULARY)}
EMBEDDING_DIM = len(TOPIC_VOCABULARY)


def generate_embedding_from_analysis(semantic_analysis):
    """Generate a fixed-dimension semantic embedding from structured analysis.

    All embeddings have the same length (len(TOPIC_VOCABULARY)) so they can
    be compared via cosine similarity.

    Each topic dimension gets a weight based on how strongly the document
    relates to that topic, derived from the structured analysis fields.
    """
    if not semantic_analysis:
        return None

    embedding = np.zeros(EMBEDDING_DIM, dtype=np.float32)

    # Map analysis fields to topic weights
    field_weights = {
        'primary_roles': 5.0,
        'related_roles': 3.0,
        'domains': 4.0,
        'direct_skills': 5.0,
        'critical_skills': 5.0,
        'important_skills': 4.0,
        'preferred_skills': 3.0,
        'related_skills': 3.0,
        'inferred_capabilities': 3.0,
        'key_responsibilities': 2.0,
        'key_strengths': 2.0,
    }

    for field, weight in field_weights.items():
        items = semantic_analysis.get(field, [])
        if isinstance(items, str):
            items = [items]
        for item in items:
            if not item:
                continue
            term = str(item).strip().lower()
            # Direct match
            if term in _TOPIC_INDEX:
                embedding[_TOPIC_INDEX[term]] += weight
            else:
                # Partial match: check if any vocabulary topic is a substring
                for topic, idx in _TOPIC_INDEX.items():
                    if topic in term or term in topic:
                        embedding[idx] += weight * 0.7

    # Handle experience/education level fields
    level_terms = {
        'experience_level': {
            'entry': 'entry level', 'mid': 'mid level', 'senior': 'senior',
            'lead': 'lead', 'executive': 'executive'
        },
        'education_level': {
            'phd': 'phd', 'doctorate': 'phd', 'masters': 'masters',
            'bachelors': 'bachelors', 'diploma': 'diploma', 'high_school': 'diploma'
        },
        'education_requirement': {
            'phd': 'phd', 'doctorate': 'phd', 'masters': 'masters',
            'bachelors': 'bachelors', 'diploma': 'diploma'
        },
    }

    for field, mapping in level_terms.items():
        value = semantic_analysis.get(field, '')
        if value and value.lower() in mapping:
            topic = mapping[value.lower()]
            if topic in _TOPIC_INDEX:
                embedding[_TOPIC_INDEX[topic]] += 3.0

    # L2 normalize
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding


def cosine_similarity_vec(a, b):
    """Compute cosine similarity between two numpy vectors."""
    if a is None or b is None:
        return 0.0
    if len(a) != len(b):
        return 0.0
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
