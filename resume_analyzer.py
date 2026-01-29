import re
import string
import sys
from pathlib import Path
from typing import List, Tuple, Set

import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

def preprocess_text(text: str) -> str:
    """
    Preprocess the input text by:
    1. Converting to lowercase
    2. Removing URLs
    3. Removing punctuation and numbers
    4. Removing short words and stopwords
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs and email addresses
    text = re.sub(r'https?://\S+|www\.\S+|\S+@\S+', '', text)
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove standalone numbers and words containing numbers
    text = re.sub(r'\b\d+\b|\w*\d\w*', '', text)
    
    # Tokenize and filter
    tokens = tokenize_text(text)
    filtered_tokens = [word for word in tokens if word not in STOP_WORDS and len(word) > 2]
    
    return ' '.join(filtered_tokens)

def calculate_similarity(resume_text: str, job_description: str) -> Tuple[float, List[str]]:
    """
    Calculate cosine similarity between resume and job description.
    Returns similarity score and top missing keywords.
    """
    # Initialize TF-IDF Vectorizer
    vectorizer = TfidfVectorizer()
    
    # Create TF-IDF matrices
    tfidf_matrix = vectorizer.fit_transform([job_description, resume_text])
    
    # Calculate cosine similarity
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    
    # Get feature names (words in the vocabulary)
    feature_names = vectorizer.get_feature_names_out()
    
    # Get TF-IDF scores for job description
    job_desc_vector = tfidf_matrix[0]
    resume_vector = tfidf_matrix[1]
    
    # Find important words in job description that are missing or have low score in resume
    job_desc_scores = job_desc_vector.toarray()[0]
    resume_scores = resume_vector.toarray()[0]
    
    # Get top 10 important words from job description
    top_indices = job_desc_scores.argsort()[-10:][::-1]
    
    # Find missing or low-scoring keywords
    missing_keywords = []
    for idx in top_indices:
        if job_desc_scores[idx] > 0 and (resume_scores[idx] == 0 or resume_scores[idx] < 0.1):
            missing_keywords.append(feature_names[idx])
    
    return similarity * 100, missing_keywords[:5]  # Return top 5 missing keywords

def analyze_resume(resume_path: str, jd_path: str) -> dict:
    """
    Analyze a resume against a job description and return the results as a dictionary.
    
    Args:
        resume_path: Path to the resume file (PDF or TXT)
        jd_path: Path to the job description file (TXT)
        
    Returns:
        dict: Dictionary containing analysis results
    """
    try:
        # Read and process resume
        if resume_path.lower().endswith('.pdf'):
            resume_text = extract_text_from_pdf(resume_path)
            if not resume_text.strip():
                return {
                    'error': 'Could not extract text from PDF. The file might be corrupted or password protected.'
                }
        else:
            resume_text = read_text_file(resume_path)
        
        # Read and process job description
        job_desc_text = read_text_file(jd_path)
        
        # Preprocess texts
        processed_resume = preprocess_text(resume_text)
        processed_job_desc = preprocess_text(job_desc_text)
        
        # Calculate similarity and get missing keywords
        similarity_score, missing_keywords = calculate_similarity(processed_resume, processed_job_desc)
        
        # Prepare results
        result = {
            'success': True,
            'score': round(similarity_score, 1),
            'missing_keywords': missing_keywords[:10],  # Return top 10 missing keywords
            'resume_text': resume_text[:1000] + '...' if len(resume_text) > 1000 else resume_text,
            'job_desc_text': job_desc_text[:1000] + '...' if len(job_desc_text) > 1000 else job_desc_text
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python resume_analyzer.py <resume_file> <job_description_file>")
        print("Supported formats: PDF or TXT for resume, TXT for job description")
        sys.exit(1)
    
    resume_path = sys.argv[1]
    jd_path = sys.argv[2]
    
    # Check if files exist
    if not Path(resume_path).exists():
        print(f"Error: Resume file '{resume_path}' not found.")
        sys.exit(1)
    
    if not Path(jd_path).exists():
        print(f"Error: Job description file '{jd_path}' not found.")
        sys.exit(1)
    
    print("\nProcessing resume and job description...")
    
    result = analyze_resume(resume_path, jd_path)
    
    if not result.get('success', False):
        print(f"\nAn error occurred: {result.get('error', 'Unknown error')}")
        print("Please make sure the input files are valid and try again.")
        sys.exit(1)
    
    # Display results
    print("\n" + "="*50)
    print(f"Resume Match Score: {result['score']}%")
    
    if result['missing_keywords']:
        print("\nTop Missing Keywords:")
        for i, keyword in enumerate(result['missing_keywords'], 1):
            print(f"{i}. {keyword}")
    else:
        print("\nGreat! Your resume covers all important keywords from the job description.")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
