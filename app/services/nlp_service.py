import re
import json

SKILLS_DICTIONARY = {
    'programming': [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby',
        'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'bash',
        'sql', 'html', 'css', 'sass', 'scss'
    ],
    'frameworks': [
        'flask', 'django', 'fastapi', 'spring', 'react', 'angular', 'vue',
        'node.js', 'express', 'next.js', 'nuxt.js', 'laravel', 'rails',
        'bootstrap', 'tailwind', 'tailwind css', 'jquery', 'jquery'
    ],
    'databases': [
        'mysql', 'postgresql', 'mongodb', 'sqlite', 'oracle', 'sql server',
        'redis', 'elasticsearch', 'cassandra', 'firebase', 'dynamodb'
    ],
    'tools': [
        'git', 'github', 'gitlab', 'docker', 'kubernetes', 'jenkins', 'aws',
        'azure', 'gcp', 'linux', 'nginx', 'apache', 'vim', 'vscode', 'jira',
        'terraform', 'ansible', 'ci/cd', 'devops'
    ],
    'data': [
        'machine learning', 'deep learning', 'data analysis', 'data science',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'nlp',
        'natural language processing', 'computer vision', 'power bi', 'tableau',
        'excel', 'spark', 'hadoop', 'etl'
    ],
    'professional': [
        'communication', 'leadership', 'teamwork', 'project management',
        'problem solving', 'critical thinking', 'time management',
        'analytical skills', 'attention to detail', 'creativity',
        'adaptability', 'collaboration', 'presentation', 'negotiation'
    ],
    'soft_skills': [
        'team player', 'self-motivated', 'detail-oriented', 'fast learner',
        ' multitasking', 'organized', 'proactive', 'results-driven'
    ]
}


def get_all_skills():
    """Return a flat list of all skills."""
    all_skills = []
    for category in SKILLS_DICTIONARY.values():
        all_skills.extend(category)
    return list(set(all_skills))


def extract_skills(text):
    """Extract skills from text using dictionary matching."""
    if not text:
        return []

    text_lower = text.lower()
    found_skills = []

    for category_skills in SKILLS_DICTIONARY.values():
        for skill in category_skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                if skill not in found_skills:
                    found_skills.append(skill)

    return found_skills


def extract_email(text):
    """Extract email address from text."""
    if not text:
        return ''
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    return match.group(0) if match else ''


def extract_phone(text):
    """Extract phone number from text (Nigerian and international formats)."""
    if not text:
        return ''

    patterns = [
        r'\+?234[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{4}',
        r'\+?234[\s-]?\d{4}[\s-]?\d{3}[\s-]?\d{3}',
        r'\+?\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}',
        r'\(?\d{3,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}',
        r'\d{10,14}'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(0)
            if len(re.sub(r'\D', '', phone)) >= 8:
                return phone.strip()

    return ''


def extract_name(text, email=''):
    """Extract candidate name from text (typically the first line)."""
    if not text:
        return ''

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    for line in lines[:5]:
        if re.match(r'^[A-Z][a-z]+(?:\s[A-Z][a-z]+)+$', line):
            return line
        if re.match(r'^[A-Z][a-z]+\s[A-Z]\.\s[A-Z][a-z]+$', line):
            return line
        if re.match(r'^[A-Z][a-z]+\s[A-Z][a-z]+$', line):
            words = line.split()
            if all(w[0].isupper() for w in words if w):
                return line

    for line in lines[:3]:
        clean = re.sub(r'[^\w\s]', '', line).strip()
        words = clean.split()
        if 2 <= len(words) <= 4:
            if all(w[0].isupper() if w else False for w in words):
                return clean

    return ''


def extract_education(text):
    """Extract education information from text."""
    if not text:
        return []

    education_entries = []
    degree_patterns = [
        r'(?:B\.?Sc\.?|Bachelor(?:\'s)?(?:\s+of)?(?:\s+Science)?)\s+(?:in\s+)?([^\n,]+)',
        r'(?:B\.?A\.?|Bachelor(?:\'s)?(?:\s+of)?(?:\s+Arts)?)\s+(?:in\s+)?([^\n,]+)',
        r'(?:M\.?Sc\.?|Master(?:\'s)?(?:\s+of)?(?:\s+Science)?)\s+(?:in\s+)?([^\n,]+)',
        r'(?:M\.?A\.?|Master(?:\'s)?(?:\s+of)?(?:\s+Arts)?)\s+(?:in\s+)?([^\n,]+)',
        r'(?:MBA|Master(?:\'s)?(?:\s+of)?(?:\s+Business\s+Administration)?)\s*(?:in\s+)?([^\n,]*)',
        r'(?:Ph\.?D\.?|Doctor(?:\'s)?(?:\s+of)?)\s+(?:in\s+)?([^\n,]+)',
        r'(?:Diploma|Certificate)\s+(?:in\s+)?([^\n,]+)',
        r'\b(ND|HND)\s+(?:in\s+)?([^\n,]+)',
    ]

    year_pattern = r'(?:19|20)\d{2}'
    institution_keywords = ['university', 'college', 'institute', 'school', 'academy', 'polytechnic']

    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        for pattern in degree_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if match.lastindex and match.lastindex >= 2:
                    degree_prefix = match.group(1).strip()
                    field = match.group(2).strip() if match.group(2) else ''
                    degree = f'{degree_prefix} {field}'.strip() if field else degree_prefix
                else:
                    field = match.group(1).strip() if match.group(1) else ''
                    degree = match.group(0).strip()

                year_match = re.search(year_pattern, line)
                year = year_match.group(0) if year_match else ''

                institution = ''
                for j in range(max(0, i - 2), min(len(lines), i + 3)):
                    for kw in institution_keywords:
                        if kw in lines[j].lower():
                            institution = lines[j].strip()
                            break
                    if institution:
                        break

                education_entries.append({
                    'degree': degree,
                    'field': field,
                    'institution': institution,
                    'year': year
                })
                break

    return education_entries


def extract_experience(text):
    """Extract work experience information from text."""
    if not text:
        return []

    experience_entries = []
    date_pattern = r'(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\s*[-–—]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|Present|Current)'
    duration_pattern = r'(\d+)\s*(?:\+\s*)?(?:years?|yrs?)'

    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        date_match = re.search(date_pattern, line, re.IGNORECASE)
        if date_match:
            title = ''
            company = ''
            dates = date_match.group(0)

            if i > 0:
                prev_line = lines[i - 1].strip()
                if prev_line and not re.search(date_pattern, prev_line, re.IGNORECASE):
                    title = prev_line

            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and not re.search(date_pattern, next_line, re.IGNORECASE):
                    if any(kw in next_line.lower() for kw in ['inc', 'ltd', 'corp', 'company', 'co.', 'llc', 'plc']):
                        company = next_line

            description_lines = []
            j = i + 1
            while j < len(lines) and j < i + 8:
                desc_line = lines[j].strip()
                if desc_line and not re.search(date_pattern, desc_line, re.IGNORECASE):
                    if desc_line.startswith(('- ', '• ', '* ', '– ')):
                        description_lines.append(desc_line[2:].strip())
                    elif len(desc_line) > 20:
                        description_lines.append(desc_line)
                j += 1

            if title or company:
                experience_entries.append({
                    'title': title,
                    'company': company,
                    'dates': dates,
                    'description': ' '.join(description_lines[:5])
                })

        i += 1

    if not experience_entries:
        duration_match = re.search(duration_pattern, text, re.IGNORECASE)
        if duration_match:
            experience_entries.append({
                'title': '',
                'company': '',
                'dates': f'{duration_match.group(1)} years experience',
                'description': ''
            })

    return experience_entries


def calculate_years_experience(experience_list):
    """Calculate total years of experience from experience entries."""
    total_years = 0
    for exp in experience_list:
        dates = exp.get('dates', '')
        if 'present' in dates.lower() or 'current' in dates.lower():
            year_match = re.findall(r'\d{4}', dates)
            if len(year_match) >= 1:
                start_year = int(year_match[0])
                total_years += max(0, 2026 - start_year)
        else:
            year_match = re.findall(r'\d{4}', dates)
            if len(year_match) >= 2:
                start_year = int(year_match[0])
                end_year = int(year_match[1])
                total_years += max(0, end_year - start_year)

    if total_years == 0:
        for exp in experience_list:
            duration_match = re.search(r'(\d+)\s*(?:\+\s*)?(?:years?|yrs?)', exp.get('dates', ''), re.IGNORECASE)
            if duration_match:
                total_years += int(duration_match.group(1))

    return total_years


def extract_resume_info(text):
    """Extract all structured information from resume text."""
    email = extract_email(text)
    phone = extract_phone(text)
    name = extract_name(text, email)
    skills = extract_skills(text)
    education = extract_education(text)
    experience = extract_experience(text)
    years_experience = calculate_years_experience(experience)

    return {
        'candidate_name': name,
        'email': email,
        'phone': phone,
        'skills': skills,
        'education': education,
        'work_experience': experience,
        'years_experience': years_experience
    }
