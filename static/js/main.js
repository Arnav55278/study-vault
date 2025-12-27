// static/js/main.js

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Confirm delete actions
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this?');
}

// Copy to clipboard function
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        alert('Copied to clipboard!');
    }).catch(function(err) {
        console.error('Failed to copy: ', err);
    });
}

// File size validation before upload
function validateFileSize(input, maxSizeMB) {
    const maxSize = maxSizeMB * 1024 * 1024; // Convert to bytes
    const files = input.files;
    
    for (let i = 0; i < files.length; i++) {
        if (files[i].size > maxSize) {
            alert(`File "${files[i].name}" is too large. Maximum size is ${maxSizeMB}MB.`);
            input.value = '';
            return false;
        }
    }
    return true;
}