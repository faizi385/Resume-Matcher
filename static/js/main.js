// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const resumeInput = document.getElementById('resume');
    const resumeLabel = document.getElementById('resumeLabel');
    const fileUpload = document.querySelector('.file-upload');
    const jobDescription = document.getElementById('job_description');
    const jdCharCount = document.getElementById('jdCharCount');
    const jdWordCount = document.getElementById('jdWordCount');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const uploadForm = document.getElementById('uploadForm');
    const loadingIndicator = document.getElementById('loading');
    const resultsSection = document.getElementById('results');
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    const spinner = document.getElementById('spinner');
    const submitBtnText = document.getElementById('submitBtnText');
    
    // Max file size (5MB)
    const MAX_FILE_SIZE = 5 * 1024 * 1024;
    
    // Initialize the application
    function init() {
        // Initialize event listeners
        initEventListeners();
        
        // Initialize UI
        updateFileLabel('Drag & drop your resume here or click to browse');
        
        // Initialize score bar
        document.getElementById('scoreBar').style.width = '0%';
        document.getElementById('matchScore').textContent = '0';
        document.getElementById('scoreText').textContent = '0%';
    }
    
    // Initialize event listeners
    function initEventListeners() {
        // File input change
        resumeInput.addEventListener('change', handleFileSelect);
        
        // Form submission
        uploadForm.addEventListener('submit', handleFormSubmit);
        
        // Job description input
        jobDescription.addEventListener('input', updateWordCount);
        
        // Drag and drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            fileUpload.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            fileUpload.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            fileUpload.addEventListener(eventName, unhighlight, false);
        });
        
        fileUpload.addEventListener('drop', handleDrop, false);
    }
    
    // Form submission handler
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData();
        const resumeFile = resumeInput.files[0];
        const jobDescriptionText = jobDescription.value.trim();
        
        // Reset any previous states
        hideError();
        
        // Validate form
        if (!resumeFile) {
            showError('Please upload a resume file');
            fileUpload.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
        
        if (!jobDescriptionText) {
            showError('Please enter a job description');
            jobDescription.focus();
            return;
        }
        
        if (jobDescriptionText.length > 5000) {
            showError('Job description is too long. Maximum 5000 characters allowed.');
            jobDescription.focus();
            return;
        }
        
        // Show loading state
        loadingIndicator.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        analyzeBtn.disabled = true;
        submitBtnText.textContent = 'Analyzing...';
        spinner.classList.remove('hidden');
        
        // Prepare form data
        formData.append('resume', resumeFile);
        formData.append('job_description_text', jobDescriptionText);
        
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'An error occurred while analyzing your resume');
            }
            
            const result = await response.json();
            displayResults(result);
            resultsSection.classList.remove('hidden');
            
            // Scroll to results with offset for fixed header
            const headerOffset = 80;
            const elementPosition = resultsSection.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
            
            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
            
        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
        } finally {
            loadingIndicator.classList.add('hidden');
            analyzeBtn.disabled = false;
            submitBtnText.textContent = 'Analyze Again';
            spinner.classList.add('hidden');
        }
    }
    
    // File selection handler
    function handleFileSelect() {
        const file = this.files[0];
        if (file) {
            if (file.size > MAX_FILE_SIZE) {
                showError('File size exceeds 5MB limit. Please choose a smaller file.');
                this.value = '';
                updateFileLabel('Drag & drop your resume here or click to browse');
                return;
            }
            updateFileLabel(file.name);
            hideError();
        }
    }
    
    // Update word and character count for job description
    function updateWordCount() {
        const text = this.value;
        const charCount = text.length;
        const wordCount = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
        
        // Update character count
        jdCharCount.textContent = `${charCount}/5000`;
        
        // Update word count
        jdWordCount.textContent = `${wordCount} ${wordCount === 1 ? 'word' : 'words'}`;
        
        // Show warning if approaching limit
        if (charCount > 4500) {
            jdCharCount.classList.add('text-red-500');
        } else {
            jdCharCount.classList.remove('text-red-500');
        }
    }
    
    // Update file label with icon
    function updateFileLabel(text) {
        const icon = '<i class="fas fa-file-alt mr-2"></i>';
        if (!resumeLabel) return; // Exit if element doesn't exist
        
        if (text) {
            // Truncate long filenames
            const maxLength = 30;
            const displayText = text.length > maxLength 
                ? '...' + text.substring(text.length - maxLength) 
                : text;
            resumeLabel.innerHTML = icon + displayText;
        } else {
            resumeLabel.innerHTML = icon + 'Choose a file or drag it here';
        }
    }
    
    // Drag and drop handlers
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        fileUpload.classList.add('border-indigo-500', 'bg-indigo-50/50');
    }
    
    function unhighlight() {
        fileUpload.classList.remove('border-indigo-500', 'bg-indigo-50/50');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length) {
            resumeInput.files = files;
            const file = files[0];
            
            if (file.size > MAX_FILE_SIZE) {
                showError('File size exceeds 5MB limit. Please choose a smaller file.');
                return;
            }
            
            updateFileLabel(file.name);
            hideError();
        }
    }
    
    // Error handling
    function showError(message) {
        errorText.textContent = message;
        errorMessage.classList.remove('hidden', 'opacity-0');
        errorMessage.classList.add('opacity-100');
        
        // Auto-hide error after 5 seconds
        setTimeout(() => {
            hideError();
        }, 5000);
    }
    
    function hideError() {
        errorMessage.classList.add('opacity-0');
        setTimeout(() => {
            errorMessage.classList.add('hidden');
        }, 300);
    }
    
    // Reset form
    function resetForm() {
        uploadForm.reset();
        updateFileLabel('Drag & drop your resume here or click to browse');
        resumeLabel.classList.remove('font-medium', 'text-gray-900');
        resumeLabel.classList.add('text-gray-500');
        
        // Reset job description counter
        jdCharCount.textContent = '0/5000';
        jdWordCount.textContent = '0 words';
        
        // Reset UI states
        resultsSection.classList.add('hidden');
        loadingIndicator.classList.add('hidden');
        hideError();
        
        // Reset button state
        analyzeBtn.disabled = false;
        submitBtnText.textContent = 'Analyze My Resume';
        spinner.classList.add('hidden');
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    // Display analysis results
    function displayResults(data) {
        // Check if we have analysis data in the response
        const analysis = data.analysis || {};
        const metrics = data.metrics || {};
        const previews = data.previews || {};
        const skills = data.skills || {};
        
        // Update detailed metrics
        document.getElementById('tfidfScore').textContent = `${analysis.tfidf_similarity || 0}%`;
        document.getElementById('keywordSimilarity').textContent = `${analysis.keyword_similarity || 0}%`;
        
        // Update skill match metrics
        const skillMatchPct = analysis.skill_match?.match_percentage || 0;
        document.getElementById('skillMatch').textContent = `${skillMatchPct}%`;
        
        // Update required skills match
        const requiredSkillsMatched = analysis.skill_match?.required_skills_matched || 0;
        const totalRequiredSkills = analysis.skill_match?.total_required_skills || 1; // Avoid division by zero
        const requiredSkillsPct = Math.round((requiredSkillsMatched / totalRequiredSkills) * 100);
        document.getElementById('requiredSkillsMatch').textContent = 
            `${requiredSkillsMatched}/${totalRequiredSkills} (${requiredSkillsPct}%)`;
            
        // Update action verbs count
        const actionVerbsCount = analysis.ats_keywords?.action_verbs?.length || 0;
        document.getElementById('actionVerbsCount').textContent = actionVerbsCount;
        
        // Update score with animation
        const score = Math.round(analysis.overall_score || 0);
        const scoreElement = document.getElementById('matchScore');
        const scoreBar = document.getElementById('scoreBar');
        const scoreText = document.getElementById('scoreText');
        const matchStatus = document.getElementById('matchStatus');
        
        // Set status text based on score
        let statusText = '';
        let statusClass = '';
        
        if (score >= 80) {
            statusText = 'Excellent Match!';
            statusClass = 'text-green-600 bg-green-100';
        } else if (score >= 60) {
            statusText = 'Good Match';
            statusClass = 'text-blue-600 bg-blue-100';
        } else if (score >= 40) {
            statusText = 'Moderate Match';
            statusClass = 'text-yellow-600 bg-yellow-100';
        } else {
            statusText = 'Needs Improvement';
            statusClass = 'text-red-600 bg-red-100';
        }
        
        // Update status badge
        const statusBadge = document.querySelector('#matchStatus').parentNode;
        statusBadge.className = `text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full ${statusClass}`;
        matchStatus.textContent = statusText;
        
        // Animate score counter
        let currentScore = 0;
        const scoreInterval = setInterval(() => {
            if (currentScore >= score) {
                clearInterval(scoreInterval);
                scoreElement.textContent = score;
                scoreBar.style.width = `${score}%`;
                scoreText.textContent = `${score}%`;
            } else {
                currentScore++;
                scoreElement.textContent = currentScore;
                scoreBar.style.width = `${currentScore}%`;
                scoreText.textContent = `${currentScore}%`;
                
                // Update progress bar color based on score
                if (currentScore >= 80) {
                    scoreBar.className = 'progress-bar bg-gradient-to-r from-green-500 to-green-400';
                } else if (currentScore >= 60) {
                    scoreBar.className = 'progress-bar bg-gradient-to-r from-blue-500 to-blue-400';
                } else if (currentScore >= 40) {
                    scoreBar.className = 'progress-bar bg-gradient-to-r from-yellow-500 to-yellow-400';
                } else {
                    scoreBar.className = 'progress-bar bg-gradient-to-r from-red-500 to-red-400';
                }
            }
        }, 20);
        
        // Update missing skills
        const keywordsContainer = document.getElementById('missingKeywords');
        keywordsContainer.innerHTML = '';
        
        // Get missing skills from the analysis
        const missingSkills = [];
        if (analysis.skill_match && analysis.skill_match.missing) {
            for (const [category, skills] of Object.entries(analysis.skill_match.missing)) {
                if (skills && skills.length > 0) {
                    missingSkills.push(...skills.map(skill => ({
                        name: skill,
                        category: category.replace('_', ' ').toLowerCase()
                    })));
                }
            }
        }
        
        if (missingSkills.length > 0) {
            // Take top 15 missing skills
            const topMissingSkills = missingSkills.slice(0, 15);
            
            // Update keyword count
            document.getElementById('keywordCount').textContent = topMissingSkills.length;
            
            // Add skills with animation
            topMissingSkills.forEach((skill, index) => {
                setTimeout(() => {
                    const skillEl = document.createElement('div');
                    skillEl.className = 'keyword-tag animate__animated animate__fadeInUp flex items-center';
                    skillEl.style.animationDelay = `${index * 0.05}s`;
                    skillEl.innerHTML = `
                        <span class="font-semibold">${skill.name}</span>
                        <span class="text-xs opacity-75 ml-1">(${skill.category})</span>
                    `;
                    keywordsContainer.appendChild(skillEl);
                }, 50 * index);
            });
            
            document.getElementById('missingKeywordsSection').classList.remove('hidden');
        } else {
            document.getElementById('missingKeywordsSection').classList.add('hidden');
        }
        
        // Format and display preview text with syntax highlighting
        const formatPreviewText = (text) => {
            if (!text) return '<span class="text-gray-500">No preview available</span>';
            // Simple text formatting
            return text.length > 1000 
                ? text.substring(0, 1000) + '<span class="text-gray-400">... (truncated)</span>' 
                : text;
        };
        
        // Update previews with formatted text
        document.getElementById('resumePreview').innerHTML = formatPreviewText(previews.resume || '');
        document.getElementById('jdPreview').innerHTML = formatPreviewText(previews.job_description || '');
        
        // Update word counts
        document.getElementById('resumeWordCount').textContent = metrics.resume_length || 0;
        document.getElementById('jdWordCount').textContent = metrics.jd_length || 0;
    }
    
        // Mobile menu functionality
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', function() {
            const expanded = this.getAttribute('aria-expanded') === 'true' || false;
            this.setAttribute('aria-expanded', !expanded);
            mobileMenu.classList.toggle('hidden');
            
            // Toggle between menu and close icon
            const icon = this.querySelector('i');
            if (expanded) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            } else {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            }
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!mobileMenuButton.contains(event.target) && !mobileMenu.contains(event.target)) {
                mobileMenu.classList.add('hidden');
                mobileMenuButton.setAttribute('aria-expanded', 'false');
                const icon = mobileMenuButton.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    }
    
    // Close mobile menu when a link is clicked
    const mobileLinks = mobileMenu.querySelectorAll('a, button');
    mobileLinks.forEach(link => {
        link.addEventListener('click', function() {
            mobileMenu.classList.add('hidden');
            mobileMenuButton.setAttribute('aria-expanded', 'false');
            const icon = mobileMenuButton.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        });
    });

    // Initialize the application when the DOM is loaded
    init();
});
