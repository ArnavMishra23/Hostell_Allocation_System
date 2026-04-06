/**
 * Hostel Room Allocation System - Main JavaScript File
 * 
 * This file contains client-side JavaScript for the web application.
 * It handles form validation, UI interactions, and AJAX requests.
 */

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, warning, info)
 */
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to document
    document.body.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

/**
 * Confirm action before proceeding
 * @param {string} message - The confirmation message
 * @returns {boolean} - True if confirmed, false otherwise
 */
function confirmAction(message) {
    return confirm(message);
}

/**
 * Format a date string
 * @param {string} dateString - The date string to format
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Format a datetime string
 * @param {string} dateString - The datetime string to format
 * @returns {string} - Formatted datetime
 */
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// =============================================================================
// FORM VALIDATION
// =============================================================================

/**
 * Validate email format
 * @param {string} email - The email to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Validate password strength
 * @param {string} password - The password to validate
 * @returns {object} - Object with isValid boolean and message
 */
function validatePassword(password) {
    const result = {
        isValid: true,
        message: ''
    };
    
    if (password.length < 8) {
        result.isValid = false;
        result.message = 'Password must be at least 8 characters long.';
    }
    
    return result;
}

/**
 * Validate CGPA value
 * @param {number} cgpa - The CGPA to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function isValidCGPA(cgpa) {
    return cgpa >= 0 && cgpa <= 10;
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });
    
    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirmAction('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
    
    // Confirm run allocation
    const runAllocationBtn = document.querySelector('#runAllocationBtn');
    if (runAllocationBtn) {
        runAllocationBtn.addEventListener('click', function(e) {
            if (!confirmAction('Are you sure you want to run the allocation algorithm? This will process all pending applications.')) {
                e.preventDefault();
            }
        });
    }
    
    // Password toggle functionality
    const togglePasswordBtns = document.querySelectorAll('.toggle-password');
    togglePasswordBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const password = form.querySelector('input[type="password"]');
            const confirmPassword = form.querySelector('input[name="confirm_password"]');
            
            if (password && confirmPassword) {
                if (password.value !== confirmPassword.value) {
                    e.preventDefault();
                    showToast('Passwords do not match!', 'danger');
                    return false;
                }
                
                const passwordValidation = validatePassword(password.value);
                if (!passwordValidation.isValid) {
                    e.preventDefault();
                    showToast(passwordValidation.message, 'danger');
                    return false;
                }
            }
            
            // Validate CGPA
            const cgpaInput = form.querySelector('input[name="cgpa"]');
            if (cgpaInput) {
                const cgpa = parseFloat(cgpaInput.value);
                if (!isValidCGPA(cgpa)) {
                    e.preventDefault();
                    showToast('CGPA must be between 0 and 10.', 'danger');
                    return false;
                }
            }
            
            return true;
        });
    });
    
    // Table row hover effect
    const tableRows = document.querySelectorAll('.table-hover tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.cursor = 'pointer';
        });
    });
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

// =============================================================================
// AJAX FUNCTIONS
// =============================================================================

/**
 * Make an AJAX GET request
 * @param {string} url - The URL to request
 * @returns {Promise} - Promise resolving to the response
 */
function ajaxGet(url) {
    return fetch(url, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    }).then(response => response.json());
}

/**
 * Make an AJAX POST request
 * @param {string} url - The URL to request
 * @param {object} data - The data to send
 * @returns {Promise} - Promise resolving to the response
 */
function ajaxPost(url, data) {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
    }).then(response => response.json());
}

// =============================================================================
// DASHBOARD FUNCTIONS
// =============================================================================

/**
 * Refresh dashboard statistics
 */
function refreshDashboardStats() {
    ajaxGet('/api/dashboard-stats')
        .then(data => {
            // Update stat cards
            document.querySelectorAll('.stat-value').forEach(el => {
                const stat = el.getAttribute('data-stat');
                if (data[stat] !== undefined) {
                    el.textContent = data[stat];
                }
            });
        })
        .catch(error => {
            console.error('Error refreshing dashboard:', error);
        });
}

/**
 * Load recent allocations
 */
function loadRecentAllocations() {
    ajaxGet('/api/recent-allocations')
        .then(data => {
            const tbody = document.querySelector('#recentAllocationsTable tbody');
            if (tbody) {
                tbody.innerHTML = data.allocations.map(allocation => `
                    <tr>
                        <td>${allocation.student_name}</td>
                        <td>${allocation.room_number}</td>
                        <td>${allocation.room_type}</td>
                        <td>${formatDate(allocation.allocation_date)}</td>
                    </tr>
                `).join('');
            }
        })
        .catch(error => {
            console.error('Error loading allocations:', error);
        });
}

// =============================================================================
// ROOM MANAGEMENT FUNCTIONS
// =============================================================================

/**
 * Toggle room status
 * @param {number} roomId - The room ID
 * @param {string} newStatus - The new status
 */
function toggleRoomStatus(roomId, newStatus) {
    ajaxPost(`/admin/rooms/${roomId}/status`, { status: newStatus })
        .then(data => {
            if (data.success) {
                showToast('Room status updated successfully!', 'success');
                // Refresh the page or update UI
                location.reload();
            } else {
                showToast(data.message || 'Failed to update room status.', 'danger');
            }
        })
        .catch(error => {
            console.error('Error updating room status:', error);
            showToast('An error occurred. Please try again.', 'danger');
        });
}

// =============================================================================
// REPORTING FUNCTIONS
// =============================================================================

/**
 * Generate occupancy chart
 * @param {string} canvasId - The canvas element ID
 * @param {object} data - The chart data
 */
function generateOccupancyChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Available', 'Occupied', 'Maintenance'],
            datasets: [{
                data: [data.available, data.occupied, data.maintenance],
                backgroundColor: ['#198754', '#dc3545', '#ffc107'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * Generate applications chart
 * @param {string} canvasId - The canvas element ID
 * @param {object} data - The chart data
 */
function generateApplicationsChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Pending', 'Allocated', 'Waitlisted', 'Rejected'],
            datasets: [{
                label: 'Applications',
                data: [data.pending, data.allocated, data.waitlisted, data.rejected],
                backgroundColor: ['#ffc107', '#198754', '#0dcaf0', '#dc3545'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// =============================================================================
// SESSION MANAGEMENT
// =============================================================================

/**
 * Check session status periodically
 * Warns user before session expires
 */
function checkSessionStatus() {
    const warningTime = 5 * 60 * 1000; // 5 minutes before expiry
    
    setInterval(() => {
        // This would typically make an AJAX call to check session
        // For now, we'll just log to console
        console.log('Session check: ' + new Date().toISOString());
    }, warningTime);
}

// Start session checking when page loads
document.addEventListener('DOMContentLoaded', function() {
    checkSessionStatus();
});

// =============================================================================
// EXPORT FUNCTIONS FOR TESTING
// =============================================================================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showToast,
        confirmAction,
        formatDate,
        formatDateTime,
        isValidEmail,
        validatePassword,
        isValidCGPA,
        ajaxGet,
        ajaxPost
    };
}
