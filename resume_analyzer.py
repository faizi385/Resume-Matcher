import re
import string
import sys
import json
import ssl
import spacy
from pathlib import Path
from typing import List, Tuple, Set, Dict, Any
from collections import Counter
import PyPDF2
import nltk

# Disable SSL certificate verification for NLTK downloads
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download required NLTK data
nltk.download('vader_lexicon', quiet=True)
nltk.download('stopwords', quiet=True)

from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load spaCy's English model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    import subprocess
    subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
    nlp = spacy.load('en_core_web_sm')

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

# Common technical skills dictionary (can be expanded)
TECH_SKILLS = {
    'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust', 'typescript'],
    'web': ['html', 'css', 'react', 'angular', 'vue', 'django', 'flask', 'node.js', 'express', 'spring', 'laravel'],
    'databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite', 'cassandra'],
    'devops': ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'jenkins', 'ansible', 'terraform', 'github actions'],
    'data_science': ['pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn', 'r', 'matplotlib', 'seaborn']
}

# ATS keywords (can be expanded based on job categories)
ATS_KEYWORDS = {
    'action_verbs': ['managed', 'led', 'developed', 'implemented', 'designed', 'created', 'improved', 'increased', 'reduced', 'optimized'],
    'soft_skills': ['leadership', 'communication', 'teamwork', 'problem-solving', 'time management', 'adaptability', 'creativity', 'work ethic']
}

# Common English stopwords
STOP_WORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
    'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
    'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
    'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
    'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't",
    'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn',
    "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't",
    'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't",
    'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"
}

def tokenize_text(text: str) -> List[str]:
    """Simple text tokenizer that splits on whitespace and removes punctuation."""
    # Remove punctuation and convert to lowercase
    text = text.lower()
    text = re.sub(f'[{re.escape(string.punctuation)}]', ' ', text)
    # Split on whitespace and remove empty strings
    tokens = [word for word in text.split() if word]
    return tokens

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = " ".join([page.extract_text() or '' for page in reader.pages])
            return text.strip()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        sys.exit(1)

def read_text_file(file_path: str) -> str:
    """Read text content from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        print(f"Error reading text file: {e}")
        sys.exit(1)

def extract_skills(text: str) -> Dict[str, List[str]]:
    """
    Extract skills from text using NLP and predefined skill categories.
    Returns a dictionary of skill categories and their corresponding skills found.
    """
    doc = nlp(text.lower())
    
    # Extract noun chunks and named entities
    noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks]
    named_entities = [ent.text.lower() for ent in doc.ents]
    
    # Combine all possible skill indicators
    all_terms = set(token.text.lower() for token in doc if not token.is_stop and not token.is_punct)
    all_terms.update(noun_chunks)
    all_terms.update(named_entities)
    
    # Match against skill categories
    found_skills = {category: [] for category in TECH_SKILLS}
    
    for category, skills in TECH_SKILLS.items():
        for skill in skills:
            if skill in text.lower():
                found_skills[category].append(skill)
    
    return found_skills

def analyze_sentiment(text: str) -> Dict[str, float]:
    """
    Analyze the sentiment of the job description.
    Returns a dictionary with sentiment scores.
    """
    return sia.polarity_scores(text)

def extract_ats_keywords(text: str) -> Dict[str, List[str]]:
    """
    Extract ATS-relevant keywords from text.
    Returns a dictionary of keyword categories and found keywords.
    """
    found_keywords = {category: [] for category in ATS_KEYWORDS}
    
    for category, keywords in ATS_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text.lower():
                found_keywords[category].append(keyword)
    
    return found_keywords

def preprocess_text(text: str, remove_stopwords: bool = True) -> str:
    """
    Enhanced text preprocessing with NLP capabilities.
    """
    # Basic cleaning
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+|\S+@\S+', '', text)  # URLs and emails
    text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation but keep word boundaries
    
    # Tokenize and lemmatize
    doc = nlp(text)
    tokens = [token.lemma_ for token in doc if token.text.strip() != '']
    
    # Remove stopwords if needed
    if remove_stopwords:
        tokens = [token for token in tokens if token.lower() not in STOP_WORDS and len(token) > 2]
    
    return ' '.join(tokens)

def calculate_similarity(resume_text: str, job_description: str) -> Dict[str, Any]:
    """
    Enhanced similarity analysis with multiple metrics.
    Returns a dictionary with similarity scores and detailed analysis.
    """
    # Preprocess texts
    preprocessed_jd = preprocess_text(job_description)
    preprocessed_resume = preprocess_text(resume_text)
    
    # 1. TF-IDF based similarity
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
    tfidf_matrix = vectorizer.fit_transform([preprocessed_jd, preprocessed_resume])
    tfidf_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    
    # 2. Count vectorizer for exact keyword matching
    count_vectorizer = CountVectorizer(ngram_range=(1, 2), stop_words='english')
    count_matrix = count_vectorizer.fit_transform([preprocessed_jd, preprocessed_resume])
    count_similarity = cosine_similarity(count_matrix[0:1], count_matrix[1:2])[0][0]
    
    # 3. Extract and compare skills
    jd_skills = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)
    
    # Calculate skill match score
    matched_skills = {}
    missing_skills = {}
    
    for category, skills in jd_skills.items():
        matched = [skill for skill in skills if skill in resume_skills.get(category, [])]
        missing = [skill for skill in skills if skill not in resume_skills.get(category, [])]
        
        if matched:
            matched_skills[category] = matched
        if missing:
            missing_skills[category] = missing
    
    # 4. Sentiment analysis of job description
    sentiment = analyze_sentiment(job_description)
    
    # 5. ATS keyword analysis
    ats_keywords = extract_ats_keywords(resume_text)
    
    # Calculate ATS score
    ats_score = calculate_ats_score(ats_keywords)
    
    # Calculate overall score (weighted average)
    overall_score = (tfidf_similarity * 0.4 + 
                    count_similarity * 0.3 + 
                    (sum(len(skills) for skills in matched_skills.values()) / 
                     max(1, sum(len(skills) for skills in jd_skills.values())) * 0.3))
    
    return {
        'overall_score': round(overall_score * 100, 2),  # Convert to percentage
        'tfidf_similarity': round(tfidf_similarity * 100, 2),
        'keyword_similarity': round(count_similarity * 100, 2),
        'skill_match': {
            'matched': matched_skills,
            'missing': missing_skills,
            'match_percentage': round(len([s for skills in matched_skills.values() for s in skills]) / 
                                 max(1, len([s for skills in jd_skills.values() for s in skills])) * 100, 2)
        },
        'sentiment': sentiment,
        'ats_keywords': ats_keywords,
        'recommendations': generate_recommendations(matched_skills, missing_skills, ats_keywords)
    }

def generate_recommendations(matched_skills: Dict[str, List[str]], 
                          missing_skills: Dict[str, List[str]], 
                          ats_keywords: Dict[str, List[str]]) -> List[str]:
    """Generate actionable recommendations based on analysis."""
    recommendations = []
    
    # Skill-based recommendations
    if missing_skills:
        for category, skills in missing_skills.items():
            if skills:
                recommendations.append(
                    f"Consider adding experience with {', '.join(skills[:3])} "
                    f"to better match the job requirements in the {category.replace('_', ' ')} category."
                )
    
    # ATS keyword recommendations
    missing_action_verbs = [verb for verb in ATS_KEYWORDS['action_verbs'] 
                          if verb not in ats_keywords.get('action_verbs', [])]
    
    if missing_action_verbs:
        recommendations.append(
            f"Try starting bullet points with strong action verbs like "
            f"{', '.join(missing_action_verbs[:3])} to make your resume more impactful."
        )
    
    # General recommendations
    if not recommendations:
        recommendations.append("Your resume looks strong! Consider quantifying your achievements "
                            "with specific metrics to make it even better.")
    
    return recommendations

def analyze_resume(resume_path: str, jd_path: str) -> Dict[str, Any]:
    """
    Enhanced resume analysis with AI-powered features.
    """
    try:
        # Read and process files
        if resume_path.lower().endswith('.pdf'):
            resume_text = extract_text_from_pdf(resume_path)
        else:
            resume_text = read_text_file(resume_path)
        
        job_description = read_text_file(jd_path)
        
        # Extract raw text for display
        resume_preview = ' '.join(resume_text.split()[:100]) + ('...' if len(resume_text.split()) > 100 else '')
        jd_preview = ' '.join(job_description.split()[:100]) + ('...' if len(job_description.split()) > 100 else '')
        
        # Perform analysis
        analysis = calculate_similarity(resume_text, job_description)
        
        # Extract ATS keywords and calculate score
        ats_keywords = extract_ats_keywords(resume_text)
        ats_score = calculate_ats_score(ats_keywords)
        
        # Extract skills separately for detailed display
        resume_skills = extract_skills(resume_text)
        jd_skills = extract_skills(job_description)
        
        # Prepare response
        return {
            'analysis': analysis,
            'metrics': {
                'resume_length': len(resume_text.split()),
                'jd_length': len(job_description.split()),
                'unique_skills': sum(len(skills) for skills in resume_skills.values()),
                'jd_skills_count': sum(len(skills) for skills in jd_skills.values())
            },
            'previews': {
                'resume': resume_preview,
                'job_description': jd_preview
            },
            'skills': {
                'resume_skills': resume_skills,
                'jd_skills': jd_skills
            },
            'sentiment': analyze_sentiment(job_description),
            'ats_compatibility': {
                'keywords_found': ats_keywords,
                'score': ats_score
            }
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'message': 'An error occurred during analysis.'
        }

def calculate_ats_score(keywords_found: Dict[str, List[str]]) -> float:
    """Calculate ATS compatibility score based on found keywords."""
    total_keywords = sum(len(keywords) for keywords in ATS_KEYWORDS.values())
    found_keywords = sum(len(keywords) for keywords in keywords_found.values())
    
    return round((found_keywords / max(1, total_keywords)) * 100, 2)

def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python resume_analyzer.py <resume_path> <job_description_path>")
        sys.exit(1)
    
    resume_path = sys.argv[1]
    jd_path = sys.argv[2]
    
    # Check if files exist
    if not Path(resume_path).exists():
        print(f"Error: Resume file not found at {resume_path}")
        sys.exit(1)
    
    if not Path(jd_path).exists():
        print(f"Error: Job description file not found at {jd_path}")
        sys.exit(1)
    
    try:
        results = analyze_resume(resume_path, jd_path)
        
        if 'error' in results:
            print(f"Error: {results['error']}")
            print(f"Message: {results.get('message', 'No additional details')}")
            sys.exit(1)
        
        # Print formatted results
        print("\n" + "="*50)
        print("RESUME ANALYSIS REPORT".center(50))
        print("="*50)
        
        # Overall Score
        print(f"\n{' Overall Match Score: ':{'='}^50}")
        print(f"\n{results['analysis']['overall_score']}% match with job description\n")
        
        # Detailed Scores
        print(f"\n{' Detailed Analysis ':{'-'}^50}")
        print(f"TF-IDF Similarity: {results['analysis']['tfidf_similarity']}%")
        print(f"Keyword Similarity: {results['analysis']['keyword_similarity']}%")
        print(f"Skill Match: {results['analysis']['skill_match']['match_percentage']}%")
        
        # Skills Analysis
        print(f"\n{' Skills Analysis ':{'-'}^50}")
        for category, skills in results['analysis']['skill_match']['matched'].items():
            if skills:  # Only show categories with skills
                print(f"\n{category.replace('_', ' ').title()}:")
                print(f"   Matched: {', '.join(skills[:5])}" + 
                     ("..." if len(skills) > 5 else ""))
        
        missing_skills = results['analysis']['skill_match']['missing']
        if any(skills for skills in missing_skills.values()):
            print("\nMissing Skills:")
            for category, skills in missing_skills.items():
                if skills:
                    print(f"- {category.replace('_', ' ').title()}: {', '.join(skills[:3])}" + 
                         ("..." if len(skills) > 3 else ""))
        
        # Recommendations
        print(f"\n{' Recommendations ':{'-'}^50}")
        for i, rec in enumerate(results['analysis'].get('recommendations', []), 1):
            print(f"{i}. {rec}")
        
        # ATS Compatibility
        print(f"\n{' ATS Compatibility ':{'-'}^50}")
        if 'ats_compatibility' in results and 'score' in results['ats_compatibility']:
            print(f"Score: {results['ats_compatibility']['score']}%")
            if 'keywords_found' in results['ats_compatibility']:
                print("\nFound Keywords:")
                for category, keywords in results['ats_compatibility']['keywords_found'].items():
                    if keywords:  # Only show categories with found keywords
                        print(f"- {category.replace('_', ' ').title()}: {', '.join(keywords[:5])}" + 
                             ("..." if len(keywords) > 5 else ""))
        else:
            print("ATS compatibility data not available")
        
        # Preview
        print(f"\n{' Document Previews ':{'-'}^50}")
        print("\nResume Preview:")
        print(results['previews']['resume'])
        
        print("\nJob Description Preview:")
        print(results['previews']['job_description'])
        
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"\n{' ERROR ':{'*'}^50}")
        print(f"An error occurred: {str(e)}")
        print("\nPlease ensure you have all required dependencies installed.")
        print("You may need to run: pip install -r requirements.txt")
        print("*" * 50 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
