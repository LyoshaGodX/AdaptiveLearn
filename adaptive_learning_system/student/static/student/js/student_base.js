// AdaptiveLearn Student Module - Base JavaScript

document.addEventListener('DOMContentLoaded', function() {
    
    // =========================
    // PROGRESS BAR ANIMATIONS
    // =========================
    
    function animateProgressBars() {
        const progressBars = document.querySelectorAll('.progress-fill');
        
        progressBars.forEach(bar => {
            const targetWidth = bar.getAttribute('data-width') || bar.style.width;
            if (targetWidth) {
                bar.style.width = '0%';
                setTimeout(() => {
                    bar.style.width = targetWidth;
                }, 100);
            }
        });
    }
    
    // =========================
    // CARD HOVER EFFECTS
    // =========================
    
    function initCardEffects() {
        const cards = document.querySelectorAll('.dashboard-card, .stat-card');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    }
    
    // =========================
    // SMOOTH SCROLLING
    // =========================
    
    function initSmoothScrolling() {
        const navLinks = document.querySelectorAll('a[href^="#"]');
        
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
    
    // =========================
    // NOTIFICATION SYSTEM
    // =========================
    
    function initNotifications() {
        const alerts = document.querySelectorAll('.alert');
        
        alerts.forEach(alert => {
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (alert.classList.contains('show')) {
                    alert.classList.remove('show');
                    setTimeout(() => {
                        alert.remove();
                    }, 300);
                }
            }, 5000);
        });
    }
    
    // =========================
    // RESPONSIVE NAVIGATION
    // =========================
    
    function initResponsiveNav() {
        const navToggle = document.querySelector('.nav-toggle');
        const navMenu = document.querySelector('.nav-tabs-compact');
        
        if (navToggle && navMenu) {
            navToggle.addEventListener('click', function() {
                navMenu.classList.toggle('active');
            });
            
            // Close menu when clicking outside
            document.addEventListener('click', function(e) {
                if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                    navMenu.classList.remove('active');
                }
            });
        }
    }
    
    // =========================
    // SKILL LEVEL INDICATORS
    // =========================
    
    function updateSkillIndicators() {
        const skillItems = document.querySelectorAll('.skill-item');
        
        skillItems.forEach(item => {
            const progressBar = item.querySelector('.progress-fill');
            const levelBadge = item.querySelector('.skill-level');
            
            if (progressBar && levelBadge) {
                const percentage = parseInt(progressBar.getAttribute('data-width') || progressBar.style.width);
                let level, className;
                
                if (percentage >= 90) {
                    level = 'Отлично';
                    className = 'excellent';
                } else if (percentage >= 70) {
                    level = 'Хорошо';
                    className = 'good';
                } else if (percentage >= 50) {
                    level = 'Удовлетворительно';
                    className = 'satisfactory';
                } else {
                    level = 'Требует улучшения';
                    className = 'needs-improvement';
                }
                
                levelBadge.textContent = level;
                levelBadge.className = `skill-level ${className}`;
                progressBar.className = `progress-fill ${className}`;
            }
        });
    }
    
    // =========================
    // STATISTICS COUNTER
    // =========================
    
    function animateCounters() {
        const counters = document.querySelectorAll('.card-value');
        
        counters.forEach(counter => {
            const target = parseInt(counter.textContent.replace(/[^\d]/g, ''));
            const duration = 2000; // 2 seconds
            const increment = target / (duration / 16); // 60fps
            let current = 0;
            
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                
                // Preserve original formatting (%, etc.)
                const originalText = counter.textContent;
                const suffix = originalText.replace(/[\d\s]/g, '');
                counter.textContent = Math.floor(current) + suffix;
            }, 16);
        });
    }
    
    // =========================
    // ACTIVITY TIMELINE
    // =========================
    
    function initActivityTimeline() {
        const timeline = document.querySelector('.activity-timeline');
        if (!timeline) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, {
            threshold: 0.1
        });
        
        const activityItems = document.querySelectorAll('.activity-item');
        activityItems.forEach(item => observer.observe(item));
    }
    
    // =========================
    // THEME SWITCHING (Future feature)
    // =========================
    
    function initThemeSwitch() {
        const themeToggle = document.querySelector('.theme-toggle');
        if (!themeToggle) return;
        
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
        });
        
        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
        }
    }
    
    // =========================
    // INITIALIZATION
    // =========================
    
    // Initialize all features
    animateProgressBars();
    initCardEffects();
    initSmoothScrolling();
    initNotifications();
    initResponsiveNav();
    updateSkillIndicators();
    initActivityTimeline();
    initThemeSwitch();
    
    // Animate counters with delay for better UX
    setTimeout(animateCounters, 500);
    
    // Re-run progress bar animation on window resize
    window.addEventListener('resize', function() {
        setTimeout(animateProgressBars, 100);
    });
    
});

// =========================
// UTILITY FUNCTIONS
// =========================

// Format percentage for display
function formatPercentage(value, decimals = 0) {
    return parseFloat(value).toFixed(decimals) + '%';
}

// Get mastery level from percentage
function getMasteryLevel(percentage) {
    if (percentage >= 90) return 'excellent';
    if (percentage >= 70) return 'good';
    if (percentage >= 50) return 'satisfactory';
    return 'needs-improvement';
}

// Get progress color based on level
function getProgressColor(level) {
    const colors = {
        'excellent': '#10b981',
        'good': '#059669',
        'satisfactory': '#f59e0b',
        'needs-improvement': '#ef4444'
    };
    return colors[level] || colors['needs-improvement'];
}

// Export for use in other modules
window.StudentUtils = {
    formatPercentage,
    getMasteryLevel,
    getProgressColor
};
