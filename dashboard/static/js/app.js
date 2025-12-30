// dashboard/static/js/app.js

// Utility functions
const utils = {
    formatDate(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },
    
    formatScore(score) {
        if (!score) return 'N/A';
        return parseFloat(score).toFixed(1);
    },
    
    getScoreClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 70) return 'good';
        if (score >= 60) return 'fair';
        return 'poor';
    },
    
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type}`;
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
};

// Generation progress tracking
function trackGeneration(taskId) {
    const eventSource = new EventSource(`/api/generate/stream/${taskId}`);
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        // Update progress bar
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = data.progress + '%';
        }
        
        // Update message
        const messageEl = document.getElementById('progress-message');
        if (messageEl) {
            messageEl.textContent = data.message;
        }
        
        // Handle completion
        if (data.status === 'completed') {
            eventSource.close();
            utils.showToast('Variant generated successfully!', 'success');
            
            setTimeout(() => {
                window.location.href = '/jobs';
            }, 2000);
        }
        
        // Handle failure
        if (data.status === 'failed') {
            eventSource.close();
            utils.showToast('Generation failed: ' + data.error, 'error');
        }
    };
    
    eventSource.onerror = function() {
        eventSource.close();
        utils.showToast('Connection lost. Please refresh the page.', 'error');
    };
}

// Delete confirmation
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this?');
}

// Make utilities globally available
window.utils = utils;
window.trackGeneration = trackGeneration;
window.confirmDelete = confirmDelete;
