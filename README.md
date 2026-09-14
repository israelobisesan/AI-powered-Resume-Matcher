# DESIGN AND IMPLEMENTATION OF AN AI-BASED RESUME SCREENING AND JOB MATCHING SYSTEM

## Project Description

An AI-powered web application that uses Natural Language Processing (NLP), machine learning, and Google Gemini AI to automatically screen resumes and match candidates with job descriptions. The system uses TF-IDF vectorization, cosine similarity, skill-based matching, and Gemini AI-generated explanations to provide explainable match scores and rankings for both job seekers and recruiters.

---

## Features

### Job Seeker Features
- Account registration and authentication
- Resume upload (PDF/DOCX) with automatic text extraction
- NLP-based extraction of skills, education, and work experience
- Editable resume profile (correct extracted information)
- Browse open jobs with match percentages
- Detailed match breakdown (TF-IDF, skills, experience, education)
- Matched and missing skills visualization
- Explainable match results

### Recruiter Features
- Account registration and authentication
- Create, edit, close, and delete job postings
- View ranked candidates for each job posting
- Candidate search and filtering by match score
- Detailed candidate profiles with match explanations
- Dashboard with job statistics
- AI-powered skill suggestion when creating jobs (Gemini)

### AI/NLP Pipeline
- PDF text extraction using pypdf
- DOCX text extraction using python-docx
- Named Entity Recognition for personal information
- Dictionary-based skills extraction
- Education and work experience parsing
- TF-IDF vectorization and cosine similarity
- Weighted multi-factor scoring (skills, experience, education)
- Human-readable match explanations

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | SQLite with SQLAlchemy ORM |
| Authentication | Flask-Login, Werkzeug |
| Frontend | HTML5, Tailwind CSS, Vanilla JavaScript |
| NLP/AI | scikit-learn (TF-IDF, Cosine Similarity), Google Gemini AI (explanations, skill suggestions) |
| PDF Extraction | pypdf |
| DOCX Extraction | python-docx |

---

## System Architecture

```
User uploads resume
        |
        v
PDF/DOCX text extraction
        |
        v
Text preprocessing
        |
        v
NLP information extraction
        |
        v
Structured candidate profile
        |
        v
TF-IDF vectorization
        |
        v
Cosine similarity calculation
        |
        v
Skill matching
        |
        v
Experience matching
        |
        v
Education matching
        |
        v
Weighted final score
        |
        v
Ranked results with explanations
```

---

## Database Design

### Users Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(100) | Full name |
| email | String(120) | Unique email |
| password_hash | String(256) | Hashed password |
| role | String(20) | job_seeker or recruiter |
| created_at | DateTime | Registration date |

### Resumes Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to Users |
| filename | String(255) | Stored filename |
| file_type | String(10) | pdf or docx |
| raw_text | Text | Extracted text |
| candidate_name | String(200) | Extracted name |
| email | String(120) | Extracted email |
| phone | String(50) | Extracted phone |
| skills | Text | JSON array of skills |
| education | Text | JSON array of education |
| work_experience | Text | JSON array of experience |

### Jobs Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| recruiter_id | Integer | Foreign key to Users |
| title | String(200) | Job title |
| company | String(200) | Company name |
| description | Text | Job description |
| required_skills | Text | JSON array |
| preferred_skills | Text | JSON array |
| minimum_experience | Integer | Years required |
| education_requirement | String(200) | Degree level |
| location | String(200) | Job location |
| employment_type | String(50) | full-time, part-time, etc. |
| status | String(20) | open or closed |

### Matches Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| resume_id | Integer | Foreign key to Resumes |
| job_id | Integer | Foreign key to Jobs |
| tfidf_score | Float | TF-IDF similarity % |
| skill_score | Float | Skill match % |
| experience_score | Float | Experience match % |
| education_score | Float | Education match % |
| final_score | Float | Weighted final score |
| matched_skills | Text | JSON array |
| missing_skills | Text | JSON array |
| explanation | Text | Human-readable explanation |

---

## Matching Algorithm

### Weighted Score Formula

```
final_score = (tfidf_score x 0.40) + (skill_score x 0.40) + (experience_score x 0.10) + (education_score x 0.10)
```

### Component Scores

| Component | Weight | Method |
|-----------|--------|--------|
| TF-IDF Similarity | 40% | Cosine similarity of TF-IDF vectors |
| Skill Match | 40% | Required skills matched / Total required |
| Experience | 10% | Candidate years / Required years (capped at 100%) |
| Education | 10% | Degree hierarchy comparison |

### AI-Generated Explanations
After computing the scores, Google Gemini AI generates a detailed, personalized explanation of the match quality. This provides richer, more contextual explanations than template-based approaches.

### AI Skill Suggestion
When creating or editing job postings, recruiters can click "AI Suggest" to have Gemini analyze the job description and automatically suggest required and preferred skills.

### TF-IDF Pipeline
1. Text preprocessing (lowercase, remove punctuation, normalize whitespace)
2. Stop word removal
3. TF-IDF vectorization (max 5000 features)
4. Cosine similarity between resume and job description vectors

---

## Installation

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd clod

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK data (if needed)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Create environment file
copy .env.example .env

# Initialize database and seed data
python seed.py

# Run the application
python run.py
```

The application will be available at `http://127.0.0.1:5000`

---

## Demo Accounts

### Recruiters
| Email | Password |
|-------|----------|
| ada@techcorp.com | password123 |
| emeka@startupng.com | password123 |

### Job Seekers
| Email | Password |
|-------|----------|
| chidi@email.com | password123 |
| ngozi@email.com | password123 |
| tunde@email.com | password123 |
| fatima@email.com | password123 |
| amina@email.com | password123 |

---

## Running Tests

```bash
python -m unittest tests.test_app -v
```

---

## Project Structure

```
clod/
    app/
        __init__.py          # Flask app factory
        utils.py             # Role-based access decorator
        models/
            __init__.py
            user.py          # User model
            resume.py        # Resume model
            job.py           # Job model
            match.py         # Match model
        routes/
            __init__.py
            main.py          # Home page
            auth.py          # Registration, login, logout
            seeker.py        # Job seeker dashboard and jobs
            recruiter.py     # Recruiter dashboard and job management
            resume.py        # Resume upload and profile
            jobs.py          # Job listing
            matching.py      # Matching routes
        services/
            __init__.py
            resume_parser.py # PDF/DOCX text extraction
            nlp_service.py   # NLP information extraction
            matching_service.py # TF-IDF, scoring, explanations
            recommendation_service.py # Recommendations and rankings
        templates/
            base.html        # Base template with navigation
            index.html       # Landing page
            auth/            # Login, register
            seeker/          # Seeker dashboard, jobs, resume
            recruiter/       # Recruiter dashboard, jobs, candidates
            errors/          # 404, 500 error pages
        static/
            css/style.css    # Custom styles
            js/main.js       # JavaScript utilities
    uploads/                 # Uploaded resume files
    tests/
        test_app.py          # Unit and integration tests
    config.py                # Application configuration
    run.py                   # Application entry point
    seed.py                  # Database seed script
    requirements.txt         # Python dependencies
    .env.example             # Environment variables template
```

---

## Security Features

- Password hashing using Werkzeug (pbkdf2:sha256)
- Flask-Login session management
- Role-based access control
- Secure file uploads with extension validation
- File size limits (16MB max)
- Input validation and sanitization
- CSRF protection via Flask-WTF
- Environment variable configuration
- Never stores plain-text passwords

---

## License

This project is submitted as a final-year Computer Science project.
