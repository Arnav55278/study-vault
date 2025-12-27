// ============================================
// StudyVault - Main JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize all components
    initBackToTop();
    initStarButtons();
    initUploadZone();
    initRatingStars();
    initSearchSuggestions();
    initAutoHideAlerts();
    initMobileNav();
    
});

// Back to Top Button
function initBackToTop() {
    const backToTopBtn = document.getElementById('backToTop');
    if (!backToTopBtn) return;
    
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            backToTopBtn.style.display = 'flex';
        } else {
            backToTopBtn.style.display = 'none';
        }
    });
    
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// Star/Favourite Buttons
function initStarButtons() {
    document.querySelectorAll('.star-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const type = this.dataset.type;
            const id = this.dataset.id;
            const icon = this.querySelector('i');
            const countSpan = this.querySelector('span');
            
            fetch(`/star/${type}/${id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'starred') {
                    icon.classList.remove('bi-star');
                    icon.classList.add('bi-star-fill');
                    this.classList.add('active');
                    if (countSpan) {
                        countSpan.textContent = parseInt(countSpan.textContent) + 1;
                    }
                } else {
                    icon.classList.remove('bi-star-fill');
                    icon.classList.add('bi-star');
                    this.classList.remove('active');
                    if (countSpan) {
                        countSpan.textContent = Math.max(0, parseInt(countSpan.textContent) - 1);
                    }
                }
            })
            .catch(err => console.error('Star error:', err));
        });
    });
}

// Upload Zone Drag & Drop
function initUploadZone() {
    const uploadZone = document.querySelector('.upload-zone');
    const fileInput = document.getElementById('fileInput');
    
    if (!uploadZone || !fileInput) return;
    
    uploadZone.addEventListener('click', () => fileInput.click());
    
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        fileInput.files = e.dataTransfer.files;
        updateFileList(fileInput.files);
    });
    
    fileInput.addEventListener('change', () => {
        updateFileList(fileInput.files);
    });
}

function updateFileList(files) {
    const fileList = document.getElementById('fileList');
    if (!fileList) return;
    
    fileList.innerHTML = '';
    
    if (files.length === 0) {
        fileList.innerHTML = '<p class="text-muted">No files selected</p>';
        return;
    }
    
    Array.from(files).forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item d-flex align-items-center p-2 mb-2 bg-light rounded';
        item.innerHTML = `
            <i class="bi ${getFileIcon(file.name)} me-2 fs-4"></i>
            <div class="flex-grow-1">
                <div class="fw-medium">${file.name}</div>
                <small class="text-muted">${formatFileSize(file.size)}</small>
            </div>
            <span class="badge bg-secondary">${getFileExtension(file.name)}</span>
        `;
        fileList.appendChild(item);
    });
}

// Rating Stars
function initRatingStars() {
    const ratingContainers = document.querySelectorAll('.rating-input');
    
    ratingContainers.forEach(container => {
        const stars = container.querySelectorAll('i');
        const input = container.querySelector('input[type="hidden"]');
        
        stars.forEach((star, index) => {
            star.addEventListener('click', () => {
                const value = index + 1;
                input.value = value;
                
                stars.forEach((s, i) => {
                    if (i < value) {
                        s.classList.remove('bi-star');
                        s.classList.add('bi-star-fill');
                    } else {
                        s.classList.remove('bi-star-fill');
                        s.classList.add('bi-star');
                    }
                });
            });
            
            star.addEventListener('mouseenter', () => {
                stars.forEach((s, i) => {
                    if (i <= index) {
                        s.classList.add('text-warning');
                    }
                });
            });
            
            star.addEventListener('mouseleave', () => {
                stars.forEach(s => s.classList.remove('text-warning'));
            });
        });
    });
}

// Search Suggestions
function initSearchSuggestions() {
    const searchInput = document.querySelector('.search-form input[name="q"]');
    if (!searchInput) return;
    
    let timeout;
    const suggestionsContainer = document.createElement('div');
    suggestionsContainer.className = 'search-suggestions';
    searchInput.parentElement.appendChild(suggestionsContainer);
    
    searchInput.addEventListener('input', function() {
        clearTimeout(timeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            suggestionsContainer.innerHTML = '';
            suggestionsContainer.style.display = 'none';
            return;
        }
        
        timeout = setTimeout(() => {
            fetch(`/api/search/suggest?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length === 0) {
                        suggestionsContainer.style.display = 'none';
                        return;
                    }
                    
                    suggestionsContainer.innerHTML = data.map(item => `
                        <a href="${item.url}" class="suggestion-item">
                            <i class="bi ${item.type === 'folder' ? 'bi-folder' : 'bi-file-earmark'} me-2"></i>
                            ${item.name}
                        </a>
                    `).join('');
                    suggestionsContainer.style.display = 'block';
                })
                .catch(err => console.error('Search error:', err));
        }, 300);
    });
    
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
            suggestionsContainer.style.display = 'none';
        }
    });
}

// Auto-hide Alerts
function initAutoHideAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
        if (!alert.classList.contains('alert-permanent')) {
            setTimeout(() => {
                alert.style.transition = 'opacity 0.5s';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            }, 5000);
        }
    });
}

// Mobile Navigation
function initMobileNav() {
    // Hide bottom nav on scroll down, show on scroll up
    let lastScrollTop = 0;
    const mobileNav = document.querySelector('.mobile-bottom-nav');
    
    if (!mobileNav) return;
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            mobileNav.style.transform = 'translateY(100%)';
        } else {
            mobileNav.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop;
    });
    
    mobileNav.style.transition = 'transform 0.3s ease';
}

// Utility Functions
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'pdf': 'bi-file-earmark-pdf text-danger',
        'jpg': 'bi-file-earmark-image text-success',
        'jpeg': 'bi-file-earmark-image text-success',
        'png': 'bi-file-earmark-image text-success',
        'gif': 'bi-file-earmark-image text-success',
        'mp3': 'bi-file-earmark-music text-warning',
        'mp4': 'bi-file-earmark-play text-primary',
        'doc': 'bi-file-earmark-word text-info',
        'docx': 'bi-file-earmark-word text-info',
        'ppt': 'bi-file-earmark-ppt text-danger',
        'pptx': 'bi-file-earmark-ppt text-danger',
        'txt': 'bi-file-earmark-text text-secondary'
    };
    return icons[ext] || 'bi-file-earmark text-secondary';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileExtension(filename) {
    return filename.split('.').pop().toUpperCase();
}

// Copy to Clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Copy failed:', err);
    });
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <i class="bi bi-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
        ${message}
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Confirm Delete
function confirmDelete(message = 'Are you sure you want to delete this?') {
    return confirm(message);
}