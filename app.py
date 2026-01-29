from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
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
        
        # Analyze the resume
        result = analyze_resume(resume_path, jd_path)
        
        # Clean up
        os.remove(resume_path)
        os.remove(jd_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
