import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.application import Application
from app.models.notification import Notification
from app.services.embedding_service import (
    compute_content_hash, serialize_embedding, generate_embedding_from_analysis
)
from config import Config

app = create_app()


def _build_resume_analysis(skills, roles, domains, capabilities, responsibilities,
                           exp_level, years, edu_level, edu_field, strengths, gaps, related_skills=None):
    """Helper to build a resume semantic analysis dict."""
    return {
        'primary_roles': roles,
        'related_roles': [r for r in roles if r != roles[0]] + ['Software Developer'],
        'domains': domains,
        'direct_skills': skills,
        'related_skills': related_skills or [],
        'inferred_capabilities': capabilities,
        'key_responsibilities': responsibilities,
        'experience_level': exp_level,
        'years_of_experience': years,
        'education_level': edu_level,
        'education_field': edu_field,
        'key_strengths': strengths,
        'potential_gaps': gaps,
    }


def _build_job_analysis(primary_role, related_roles, domains, critical_skills,
                        important_skills, preferred_skills, capabilities,
                        responsibilities, exp_level, min_years, edu_req, edu_field):
    """Helper to build a job semantic analysis dict."""
    return {
        'primary_role': primary_role,
        'related_roles': related_roles,
        'domains': domains,
        'critical_skills': critical_skills,
        'important_skills': important_skills,
        'preferred_skills': preferred_skills,
        'inferred_capabilities': capabilities,
        'key_responsibilities': responsibilities,
        'experience_level': exp_level,
        'min_years_experience': min_years,
        'education_requirement': edu_req,
        'education_field': edu_field,
    }


# Pre-computed semantic analyses for seed resumes
SEED_RESUME_ANALYSES = {
    'chidi@email.com': _build_resume_analysis(
        skills=['Python', 'Flask', 'Django', 'JavaScript', 'HTML', 'CSS', 'SQL', 'Git', 'Docker', 'Machine Learning'],
        roles=['Python Developer', 'Backend Developer', 'Full Stack Developer'],
        domains=['web development', 'backend engineering', 'machine learning'],
        capabilities=['API design', 'database management', 'deployment', 'team collaboration'],
        responsibilities=['backend development', 'API development', 'database management', 'frontend development'],
        exp_level='mid', years=4, edu_level='bachelors', edu_field='Computer Science',
        strengths=['Python expertise', 'full-stack capability', 'DevOps experience'],
        gaps=['no cloud platform certification'],
        related_skills=['Python web frameworks', 'relational databases']
    ),
    'ngozi@email.com': _build_resume_analysis(
        skills=['HTML', 'CSS', 'JavaScript', 'React', 'Vue.js', 'Tailwind CSS', 'Git'],
        roles=['Frontend Developer', 'UI Developer', 'Web Developer'],
        domains=['web development', 'frontend engineering', 'UI/UX'],
        capabilities=['responsive design', 'component architecture', 'cross-browser compatibility', 'design implementation'],
        responsibilities=['frontend development', 'UI implementation', 'responsive design', 'design collaboration'],
        exp_level='mid', years=3, edu_level='bachelors', edu_field='Information Technology',
        strengths=['React and Vue.js expertise', 'responsive design', 'design system knowledge'],
        gaps=['backend development', 'database management'],
        related_skills=['JavaScript frameworks', 'CSS frameworks']
    ),
    'tunde@email.com': _build_resume_analysis(
        skills=['SQL', 'Excel', 'Python', 'Power BI', 'Tableau', 'Data Analysis'],
        roles=['Data Analyst', 'Business Intelligence Analyst', 'Reporting Analyst'],
        domains=['data analytics', 'business intelligence', 'reporting'],
        capabilities=['data visualization', 'statistical analysis', 'data-driven decision making', 'report generation'],
        responsibilities=['data analysis', 'dashboard creation', 'reporting', 'data extraction'],
        exp_level='mid', years=3, edu_level='bachelors', edu_field='Statistics',
        strengths=['data visualization', 'SQL expertise', 'Python for data analysis'],
        gaps=['machine learning', 'big data technologies'],
        related_skills=['data science', 'business intelligence tools']
    ),
    'fatima@email.com': _build_resume_analysis(
        skills=['Python', 'Flask', 'HTML', 'CSS', 'SQL', 'Git', 'Communication', 'Leadership'],
        roles=['Software Developer', 'Python Developer', 'Team Lead'],
        domains=['web development', 'backend engineering', 'team management'],
        capabilities=['team leadership', 'API design', 'project management', 'mentoring'],
        responsibilities=['software development', 'team leadership', 'code review', 'project management'],
        exp_level='mid', years=4, edu_level='bachelors', edu_field='Computer Science',
        strengths=['leadership experience', 'Python/Flask', 'team management'],
        gaps=['cloud infrastructure', 'DevOps'],
        related_skills=['Python web frameworks', 'management skills']
    ),
    'amina@email.com': _build_resume_analysis(
        skills=['Python', 'JavaScript', 'HTML', 'CSS', 'React', 'Node.js', 'SQL', 'Git'],
        roles=['Full Stack Developer', 'Software Engineer', 'Web Developer'],
        domains=['web development', 'full-stack engineering', 'software engineering'],
        capabilities=['full-stack development', 'API design', 'database management', 'responsive design'],
        responsibilities=['full-stack development', 'frontend and backend development', 'database management'],
        exp_level='entry', years=2, edu_level='bachelors', edu_field='Software Engineering',
        strengths=['full-stack versatility', 'React', 'Node.js'],
        gaps=['system design', ' DevOps', 'cloud platforms'],
        related_skills=['JavaScript frameworks', 'server-side programming']
    ),
}

# Pre-computed semantic analyses for seed jobs
SEED_JOB_ANALYSES = {
    'Frontend Developer': _build_job_analysis(
        primary_role='Frontend Developer',
        related_roles=['UI Developer', 'Web Developer', 'React Developer'],
        domains=['web development', 'frontend engineering', 'UI/UX'],
        critical_skills=['HTML', 'CSS', 'JavaScript', 'React'],
        important_skills=['Git', 'responsive design'],
        preferred_skills=['Vue.js', 'Tailwind CSS', 'TypeScript'],
        capabilities=['responsive design', 'component architecture', 'cross-browser compatibility'],
        responsibilities=['frontend development', 'UI implementation', 'responsive design'],
        exp_level='mid', min_years=2, edu_req='bachelors', edu_field='Computer Science'
    ),
    'Backend Developer': _build_job_analysis(
        primary_role='Backend Developer',
        related_roles=['Python Developer', 'API Developer', 'Software Engineer'],
        domains=['web development', 'backend engineering', 'API development'],
        critical_skills=['Python', 'Flask', 'SQL'],
        important_skills=['Git', 'Docker'],
        preferred_skills=['PostgreSQL', 'Redis', 'AWS'],
        capabilities=['API design', 'database management', 'authentication systems'],
        responsibilities=['backend development', 'API development', 'database management'],
        exp_level='mid', min_years=3, edu_req='bachelors', edu_field='Computer Science'
    ),
    'Full Stack Developer': _build_job_analysis(
        primary_role='Full Stack Developer',
        related_roles=['Software Engineer', 'Web Developer'],
        domains=['web development', 'full-stack engineering'],
        critical_skills=['Python', 'Flask', 'JavaScript', 'HTML', 'CSS', 'SQL'],
        important_skills=['Git'],
        preferred_skills=['Docker', 'React', 'PostgreSQL'],
        capabilities=['full-stack development', 'API design', 'database management'],
        responsibilities=['full-stack development', 'frontend and backend development', 'database management'],
        exp_level='mid', min_years=2, edu_req='bachelors', edu_field='Computer Science'
    ),
    'Data Analyst': _build_job_analysis(
        primary_role='Data Analyst',
        related_roles=['Business Intelligence Analyst', 'Reporting Analyst'],
        domains=['data analytics', 'business intelligence'],
        critical_skills=['SQL', 'Excel', 'Python'],
        important_skills=['Power BI'],
        preferred_skills=['Tableau', 'Data Analysis', 'Machine Learning'],
        capabilities=['data visualization', 'statistical analysis', 'data-driven decision making'],
        responsibilities=['data analysis', 'dashboard creation', 'reporting'],
        exp_level='entry', min_years=1, edu_req='bachelors', edu_field='any'
    ),
    'Software Engineer': _build_job_analysis(
        primary_role='Software Engineer',
        related_roles=['Backend Developer', 'Full Stack Developer', 'Python Developer'],
        domains=['software engineering', 'web development'],
        critical_skills=['Python', 'SQL', 'Git'],
        important_skills=['HTML', 'CSS'],
        preferred_skills=['Docker', 'AWS', 'Machine Learning', 'JavaScript'],
        capabilities=['system design', 'code review', 'debugging', 'cross-functional collaboration'],
        responsibilities=['software development', 'code review', 'debugging', 'collaboration'],
        exp_level='mid', min_years=3, edu_req='bachelors', edu_field='Computer Science'
    ),
}


def seed_database():
    with app.app_context():
        db.drop_all()
        db.create_all()

        print('Creating users...')

        recruiters = []
        for name, email in [
            ('Ada Okafor', 'ada@techcorp.com'),
            ('Emeka Nwosu', 'emeka@startupng.com')
        ]:
            user = User(name=name, email=email, role='recruiter')
            user.set_password('password123')
            db.session.add(user)
            recruiters.append(user)

        seekers = []
        for name, email in [
            ('Chidi Eze', 'chidi@email.com'),
            ('Ngozi Oba', 'ngozi@email.com'),
            ('Tunde Adesanya', 'tunde@email.com'),
            ('Fatima Bello', 'fatima@email.com'),
            ('Amina Yusuf', 'amina@email.com')
        ]:
            user = User(name=name, email=email, role='job_seeker')
            user.set_password('password123')
            db.session.add(user)
            seekers.append(user)

        db.session.commit()
        print(f'  Created {len(recruiters)} recruiters, {len(seekers)} seekers')

        print('Creating jobs...')
        jobs_data = [
            {
                'recruiter': recruiters[0],
                'title': 'Frontend Developer',
                'company': 'TechCorp Nigeria',
                'description': 'We are looking for a skilled Frontend Developer to join our team. You will be responsible for building and maintaining user interfaces for our web applications.\n\nResponsibilities:\n- Develop responsive web interfaces using HTML, CSS, and JavaScript\n- Implement UI designs using Tailwind CSS or Bootstrap\n- Build interactive features with React or Vue.js\n- Write clean, maintainable code\n- Collaborate with designers and backend developers\n\nRequirements:\n- 2+ years experience in frontend development\n- Strong HTML, CSS, JavaScript skills\n- Experience with React or Vue.js\n- Knowledge of responsive design principles\n- Git version control',
                'required_skills': ['HTML', 'CSS', 'JavaScript', 'React', 'Git'],
                'preferred_skills': ['Vue.js', 'Tailwind CSS', 'TypeScript'],
                'min_exp': 2,
                'education': 'bachelor',
                'location': 'Lagos, Nigeria',
                'type': 'full-time'
            },
            {
                'recruiter': recruiters[0],
                'title': 'Backend Developer',
                'company': 'TechCorp Nigeria',
                'description': 'We are seeking a Backend Developer to design and implement server-side logic for our applications.\n\nResponsibilities:\n- Design and develop RESTful APIs using Python and Flask\n- Manage databases including PostgreSQL and MySQL\n- Implement authentication and authorization systems\n- Write unit and integration tests\n- Deploy applications using Docker\n\nRequirements:\n- 3+ years experience in backend development\n- Strong Python programming skills\n- Experience with Flask or Django\n- SQL database expertise\n- Git and GitHub workflow',
                'required_skills': ['Python', 'Flask', 'SQL', 'Git', 'Docker'],
                'preferred_skills': ['PostgreSQL', 'Redis', 'AWS'],
                'min_exp': 3,
                'education': 'bachelor',
                'location': 'Lagos, Nigeria',
                'type': 'full-time'
            },
            {
                'recruiter': recruiters[1],
                'title': 'Full Stack Developer',
                'company': 'StartupNG',
                'description': 'Join our team as a Full Stack Developer. You will work on both frontend and backend of our web platform.\n\nResponsibilities:\n- Build full-stack web applications using Python Flask and JavaScript\n- Design and manage SQL databases\n- Create responsive user interfaces with HTML, CSS, and JavaScript\n- Implement API endpoints and integrate frontend with backend\n- Deploy and maintain applications\n\nRequirements:\n- 2+ years full-stack development experience\n- Python and Flask proficiency\n- JavaScript and HTML/CSS skills\n- SQL database management\n- Git version control',
                'required_skills': ['Python', 'Flask', 'JavaScript', 'HTML', 'CSS', 'SQL', 'Git'],
                'preferred_skills': ['Docker', 'React', 'PostgreSQL'],
                'min_exp': 2,
                'education': 'bachelor',
                'location': 'Remote',
                'type': 'full-time'
            },
            {
                'recruiter': recruiters[1],
                'title': 'Data Analyst',
                'company': 'StartupNG',
                'description': 'We are looking for a Data Analyst to help us make data-driven decisions.\n\nResponsibilities:\n- Analyze large datasets to extract insights\n- Create data visualizations and dashboards using Power BI or Tableau\n- Write SQL queries for data extraction\n- Perform statistical analysis using Python\n- Create reports and presentations for stakeholders\n\nRequirements:\n- 1+ years experience in data analysis\n- Strong SQL skills\n- Proficiency in Excel and Power BI or Tableau\n- Python for data analysis (pandas, numpy)\n- Good communication skills',
                'required_skills': ['SQL', 'Excel', 'Python', 'Power BI'],
                'preferred_skills': ['Tableau', 'Data Analysis', 'Machine Learning'],
                'min_exp': 1,
                'education': 'bachelor',
                'location': 'Abuja, Nigeria',
                'type': 'full-time'
            },
            {
                'recruiter': recruiters[0],
                'title': 'Software Engineer',
                'company': 'TechCorp Nigeria',
                'description': 'We are hiring a Software Engineer to design and build scalable software solutions.\n\nResponsibilities:\n- Design and develop software applications\n- Write clean, efficient, and maintainable code\n- Participate in code reviews\n- Troubleshoot and debug applications\n- Collaborate with cross-functional teams\n\nRequirements:\n- 3+ years software engineering experience\n- Strong programming skills in Python or Java\n- Experience with web frameworks (Flask, Django, or Spring)\n- Database design and management\n- Problem-solving and critical thinking skills',
                'required_skills': ['Python', 'SQL', 'Git', 'HTML', 'CSS'],
                'preferred_skills': ['Docker', 'AWS', 'Machine Learning', 'JavaScript'],
                'min_exp': 3,
                'education': 'bachelor',
                'location': 'Lagos, Nigeria',
                'type': 'full-time'
            }
        ]

        jobs = []
        for jd in jobs_data:
            analysis = SEED_JOB_ANALYSES.get(jd['title'], {})
            content_hash = compute_content_hash(
                f"{jd['title']}|{jd['description']}|{json.dumps(jd['required_skills'])}|{json.dumps(jd['preferred_skills'])}|{jd['min_exp']}|{jd['education']}"
            )
            embedding = generate_embedding_from_analysis(analysis)

            job = Job(
                recruiter_id=jd['recruiter'].id,
                title=jd['title'],
                company=jd['company'],
                description=jd['description'],
                required_skills=json.dumps(jd['required_skills']),
                preferred_skills=json.dumps(jd['preferred_skills']),
                minimum_experience=jd['min_exp'],
                education_requirement=jd['education'],
                location=jd['location'],
                employment_type=jd['type'],
                content_hash=content_hash,
                analysis_status='completed',
                analysis_version=Config.CURRENT_ANALYSIS_VERSION,
                analysis_model='seed-data',
                semantic_analysis=json.dumps(analysis) if analysis else None,
                semantic_embedding=serialize_embedding(embedding),
            )
            db.session.add(job)
            jobs.append(job)

        db.session.commit()
        print(f'  Created {len(jobs)} jobs')

        print('Creating resumes...')

        resumes_data = [
            {
                'user': seekers[0],
                'name': 'Chidi Eze',
                'email': 'chidi@email.com',
                'phone': '+234 801 234 5678',
                'raw_text': 'Chidi Eze\nEmail: chidi@email.com\nPhone: +234 801 234 5678\n\nSKILLS\nPython, Flask, Django, JavaScript, HTML, CSS, SQL, Git, Docker, Machine Learning\n\nEDUCATION\nB.Sc. Computer Science\nUniversity of Lagos\n2019\n\nWORK EXPERIENCE\nSenior Developer\nTechStart Inc.\nJan 2021 - Present\n- Led development of Python Flask web applications\n- Implemented REST APIs and managed PostgreSQL databases\n- Deployed applications using Docker and AWS\n\nJunior Developer\nCodeHouse\nJun 2019 - Dec 2020\n- Built frontend interfaces with HTML, CSS, JavaScript\n- Assisted with Python backend development',
                'skills': ['python', 'flask', 'django', 'javascript', 'html', 'css', 'sql', 'git', 'docker', 'machine learning'],
                'education': [{'degree': 'B.Sc. Computer Science', 'field': 'Computer Science', 'institution': 'University of Lagos', 'year': '2019'}],
                'experience': [
                    {'title': 'Senior Developer', 'company': 'TechStart Inc.', 'dates': 'Jan 2021 - Present', 'description': 'Led development of Python Flask web applications'},
                    {'title': 'Junior Developer', 'company': 'CodeHouse', 'dates': 'Jun 2019 - Dec 2020', 'description': 'Built frontend with HTML, CSS, JavaScript'}
                ]
            },
            {
                'user': seekers[1],
                'name': 'Ngozi Oba',
                'email': 'ngozi@email.com',
                'phone': '+234 802 345 6789',
                'raw_text': 'Ngozi Oba\nEmail: ngozi@email.com\nPhone: +234 802 345 6789\n\nSKILLS\nHTML, CSS, JavaScript, React, Vue.js, Tailwind CSS, Git\n\nEDUCATION\nB.Sc. Information Technology\nObafemi Awolowo University\n2020\n\nWORK EXPERIENCE\nFrontend Developer\nDesignHub\nMar 2021 - Present\n- Build responsive web interfaces using React and Vue.js\n- Implement designs with Tailwind CSS\n- Collaborate with UX designers\n\nWeb Developer Intern\nWebCo\nJan 2020 - Jun 2020\n- Assisted in building HTML/CSS pages',
                'skills': ['html', 'css', 'javascript', 'react', 'vue.js', 'tailwind css', 'git'],
                'education': [{'degree': 'B.Sc. Information Technology', 'field': 'Information Technology', 'institution': 'Obafemi Awolowo University', 'year': '2020'}],
                'experience': [
                    {'title': 'Frontend Developer', 'company': 'DesignHub', 'dates': 'Mar 2021 - Present', 'description': 'Build responsive web interfaces using React and Vue.js'},
                    {'title': 'Web Developer Intern', 'company': 'WebCo', 'dates': 'Jan 2020 - Jun 2020', 'description': 'Built HTML/CSS pages'}
                ]
            },
            {
                'user': seekers[2],
                'name': 'Tunde Adesanya',
                'email': 'tunde@email.com',
                'phone': '+234 803 456 7890',
                'raw_text': 'Tunde Adesanya\nEmail: tunde@email.com\nPhone: +234 803 456 7890\n\nSKILLS\nSQL, Excel, Python, Power BI, Tableau, Data Analysis\n\nEDUCATION\nB.Sc. Statistics\nUniversity of Ibadan\n2021\n\nWORK EXPERIENCE\nData Analyst\nDataViz Ltd.\nFeb 2022 - Present\n- Analyzed datasets and created dashboards in Power BI\n- Wrote complex SQL queries for data extraction\n- Created Excel reports for management\n\nResearch Intern\nUniversity of Ibadan\nJul 2021 - Jan 2022\n- Assisted with data collection and analysis',
                'skills': ['sql', 'excel', 'python', 'power bi', 'tableau', 'data analysis'],
                'education': [{'degree': 'B.Sc. Statistics', 'field': 'Statistics', 'institution': 'University of Ibadan', 'year': '2021'}],
                'experience': [
                    {'title': 'Data Analyst', 'company': 'DataViz Ltd.', 'dates': 'Feb 2022 - Present', 'description': 'Analyzed datasets and created dashboards in Power BI'},
                    {'title': 'Research Intern', 'company': 'University of Ibadan', 'dates': 'Jul 2021 - Jan 2022', 'description': 'Data collection and analysis'}
                ]
            },
            {
                'user': seekers[3],
                'name': 'Fatima Bello',
                'email': 'fatima@email.com',
                'phone': '+234 804 567 8901',
                'raw_text': 'Fatima Bello\nEmail: fatima@email.com\nPhone: +234 804 567 8901\n\nSKILLS\nPython, Flask, HTML, CSS, SQL, Git, Communication, Leadership\n\nEDUCATION\nB.Sc. Computer Science\nAhmadu Bello University\n2020\n\nWORK EXPERIENCE\nSoftware Developer\nInnoTech Solutions\nJan 2021 - Present\n- Developed Python Flask web applications\n- Built REST APIs and managed SQLite databases\n- Led a team of 3 junior developers\n\nFreelance Developer\nSelf-employed\n2019 - 2021\n- Built websites for small businesses using HTML, CSS, JavaScript',
                'skills': ['python', 'flask', 'html', 'css', 'sql', 'git', 'communication', 'leadership'],
                'education': [{'degree': 'B.Sc. Computer Science', 'field': 'Computer Science', 'institution': 'Ahmadu Bello University', 'year': '2020'}],
                'experience': [
                    {'title': 'Software Developer', 'company': 'InnoTech Solutions', 'dates': 'Jan 2021 - Present', 'description': 'Developed Python Flask web applications'},
                    {'title': 'Freelance Developer', 'company': 'Self-employed', 'dates': '2019 - 2021', 'description': 'Built websites for small businesses'}
                ]
            },
            {
                'user': seekers[4],
                'name': 'Amina Yusuf',
                'email': 'amina@email.com',
                'phone': '+234 805 678 9012',
                'raw_text': 'Amina Yusuf\nEmail: amina@email.com\nPhone: +234 805 678 9012\n\nSKILLS\nPython, JavaScript, HTML, CSS, React, Node.js, SQL, Git\n\nEDUCATION\nB.Sc. Software Engineering\nFederal University of Technology Minna\n2021\n\nWORK EXPERIENCE\nJunior Full Stack Developer\nWebDev Studio\nSep 2021 - Present\n- Built frontend interfaces with React and JavaScript\n- Developed backend APIs using Node.js and Python\n- Managed MySQL databases\n\nIntern\nTechHub\nJun 2021 - Aug 2021\n- Assisted in building web applications',
                'skills': ['python', 'javascript', 'html', 'css', 'react', 'node.js', 'sql', 'git'],
                'education': [{'degree': 'B.Sc. Software Engineering', 'field': 'Software Engineering', 'institution': 'Federal University of Technology Minna', 'year': '2021'}],
                'experience': [
                    {'title': 'Junior Full Stack Developer', 'company': 'WebDev Studio', 'dates': 'Sep 2021 - Present', 'description': 'Built frontend and backend for web applications'},
                    {'title': 'Intern', 'company': 'TechHub', 'dates': 'Jun 2021 - Aug 2021', 'description': 'Assisted in building web applications'}
                ]
            }
        ]

        for rd in resumes_data:
            analysis = SEED_RESUME_ANALYSES.get(rd['email'], {})
            content_hash = compute_content_hash(rd['raw_text'])
            embedding = generate_embedding_from_analysis(analysis)

            resume = Resume(
                user_id=rd['user'].id,
                filename=f'resume_{rd["user"].id}.docx',
                file_type='docx',
                raw_text=rd['raw_text'],
                candidate_name=rd['name'],
                email=rd['email'],
                phone=rd['phone'],
                skills=json.dumps(rd['skills']),
                education=json.dumps(rd['education']),
                work_experience=json.dumps(rd['experience']),
                content_hash=content_hash,
                analysis_status='completed',
                analysis_version=Config.CURRENT_ANALYSIS_VERSION,
                analysis_model='seed-data',
                semantic_analysis=json.dumps(analysis) if analysis else None,
                semantic_embedding=serialize_embedding(embedding),
            )
            db.session.add(resume)

        db.session.commit()
        print(f'  Created {len(resumes_data)} resumes')

        print('Creating applications...')
        applications_data = [
            (seekers[0], jobs[0], 'shortlisted'),  # Chidi applied to Frontend, shortlisted
            (seekers[0], jobs[1], 'pending'),       # Chidi applied to Backend, pending
            (seekers[1], jobs[0], 'pending'),       # Ngozi applied to Frontend, pending
            (seekers[2], jobs[3], 'rejected'),      # Tunde applied to Data Analyst, rejected
            (seekers[3], jobs[2], 'shortlisted'),   # Fatima applied to Full Stack, shortlisted
            (seekers[4], jobs[4], 'pending'),       # Amina applied to Software Engineer, pending
            (seekers[1], jobs[2], 'pending'),       # Ngozi applied to Full Stack, pending
            (seekers[3], jobs[0], 'pending'),       # Fatima applied to Frontend, pending
        ]

        for seeker, job, status in applications_data:
            application = Application(user_id=seeker.id, job_id=job.id, status=status)
            db.session.add(application)

        db.session.commit()
        print(f'  Created {len(applications_data)} applications')

        print('Creating notifications...')
        notifications_data = [
            (seekers[0].id, recruiters[0].id, jobs[0].id,
             'Congratulations! You have been shortlisted for the position "Frontend Developer" at TechCorp Nigeria. Please check your email for next steps.'),
            (seekers[2].id, recruiters[1].id, jobs[3].id,
             'Update on your application for "Data Analyst" at StartupNG. Unfortunately, we will not be moving forward with your application at this time.'),
            (seekers[3].id, recruiters[1].id, jobs[2].id,
             'Congratulations! You have been shortlisted for the position "Full Stack Developer" at StartupNG. Please check your email for next steps.'),
        ]

        for user_id, recruiter_id, job_id, message in notifications_data:
            notif = Notification(user_id=user_id, recruiter_id=recruiter_id, job_id=job_id, message=message)
            db.session.add(notif)

        db.session.commit()
        print(f'  Created {len(notifications_data)} notifications')

        print('\nSeed data created successfully!')
        print(f'All documents pre-analyzed (analysis_version={Config.CURRENT_ANALYSIS_VERSION})')
        print('\nDemo accounts:')
        print('  Recruiters:')
        print('    ada@techcorp.com / password123')
        print('    emeka@startupng.com / password123')
        print('  Job Seekers:')
        print('    chidi@email.com / password123')
        print('    ngozi@email.com / password123')
        print('    tunde@email.com / password123')
        print('    fatima@email.com / password123')
        print('    amina@email.com / password123')


if __name__ == '__main__':
    seed_database()
