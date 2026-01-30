from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
import PyPDF2
from resume_analyzer import analyze_resume

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({'error': 'Resume file is required'}), 400
    
    if 'job_description_text' not in request.form or not request.form['job_description_text'].strip():
        return jsonify({'error': 'Job description is required'}), 400
    
    resume_file = request.files['resume']
    job_description_text = request.form['job_description_text']
    
    if resume_file.filename == '':
        return jsonify({'error': 'No resume file selected'}), 400
    
    if not allowed_file(resume_file.filename):
        return jsonify({'error': 'Invalid file type for resume. Allowed types are PDF and TXT'}), 400
    
    try:
        # Save resume temporarily
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(resume_file.filename))
        resume_file.save(resume_path)
        
        # Save job description to a temporary file
        jd_path = os.path.join(app.config['UPLOAD_FOLDER'], 'job_description.txt')
        with open(jd_path, 'w', encoding='utf-8') as f:
            f.write(job_description_text)
        
        # Debug: Check if files exist and are readable
        if not os.path.exists(resume_path):
            return jsonify({'error': f'Resume file not found at {resume_path}'}), 500
            
        if not os.path.exists(jd_path):
            return jsonify({'error': f'Job description file not found at {jd_path}'}), 500
            
        # Read the resume text for preview first to catch any read errors
        try:
            if resume_path.lower().endswith('.pdf'):
                with open(resume_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    resume_text = ' '.join([page.extract_text() or '' for page in pdf_reader.pages])
            else:
                with open(resume_path, 'r', encoding='utf-8') as f:
                    resume_text = f.read()
                    
            # Read the job description text for preview
            with open(jd_path, 'r', encoding='utf-8') as f:
                jd_text = f.read()
                
            # If we got here, files were read successfully, now analyze
            result = analyze_resume(resume_path, jd_path)
            
        except Exception as e:
            return jsonify({
                'error': f'Error reading files: {str(e)}',
                'resume_path': resume_path,
                'jd_path': jd_path,
                'files_exist': {
                    'resume': os.path.exists(resume_path),
                    'job_description': os.path.exists(jd_path)
                }
            }), 500
        
        # Prepare the response
        response_data = {
            'analysis': result.get('analysis', {}),
            'metrics': {
                'resume_length': len(resume_text.split()),
                'jd_length': len(jd_text.split()),
                'unique_skills': sum(len(skills) for skills in result.get('skills', {}).get('resume_skills', {}).values()),
                'jd_skills_count': sum(len(skills) for skills in result.get('skills', {}).get('jd_skills', {}).values())
            },
            'previews': {
                'resume': resume_text[:1000],  # First 1000 chars for preview
                'job_description': jd_text[:1000]  # First 1000 chars for preview
            },
            'skills': result.get('skills', {})
        }
        
        # Add ATS compatibility data if available
        if 'ats_compatibility' in result:
            response_data['ats_compatibility'] = result['ats_compatibility']
        
        # Clean up
        os.remove(resume_path)
        os.remove(jd_path)
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
