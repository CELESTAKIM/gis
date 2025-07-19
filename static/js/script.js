// static/js/script.js
document.addEventListener('DOMContentLoaded', function () {
    // Flash message dismissal with animation and icon
    const flashMessages = document.querySelectorAll('.flash-messages .alert');
    flashMessages.forEach(msg => {
        msg.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-20px)';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });

    // Like/Unlike functionality with icon feedback
    const likeButtons = document.querySelectorAll('.like-btn');
    likeButtons.forEach(button => {
        button.addEventListener('click', async function () {
            const videoId = this.dataset.videoId;
            const currentLikesCountSpan = document.getElementById('current-likes-count');
            const libraryLikesCountSpan = document.getElementById(`likes-count-${videoId}`);
            const icon = this.querySelector('i');
            const text = this.querySelector('.likes-text');

            try {
                const response = await fetch(`/like_video/${videoId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();

                if (data.success) {
                    if (data.liked) {
                        this.classList.add('liked');
                        icon.className = 'fas fa-heart';
                        text.textContent = 'Unlike';
                        this.style.background = 'var(--primary-green)';
                    } else {
                        this.classList.remove('liked');
                        icon.className = 'far fa-heart';
                        text.textContent = 'Like';
                        this.style.background = 'var(--gradient)';
                    }
                    if (currentLikesCountSpan) {
                        currentLikesCountSpan.textContent = data.likes_count;
                        animateCount(currentLikesCountSpan, data.likes_count);
                    }
                    if (libraryLikesCountSpan) {
                        libraryLikesCountSpan.textContent = data.likes_count;
                        animateCount(libraryLikesCountSpan, data.likes_count);
                    }
                } else {
                    showError(data.message || 'Failed to like/unlike video.');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('An error occurred. Please try again.');
            }
        });
    });

    // Enroll functionality with icon and animation
    const enrollButtons = document.querySelectorAll('.enroll-btn');
    enrollButtons.forEach(button => {
        button.addEventListener('click', async function () {
            const videoId = this.dataset.videoId;
            const icon = this.querySelector('i');

            try {
                const response = await fetch(`/enroll_video/${videoId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();

                if (data.success) {
                    this.textContent = 'Enrolled';
                    this.classList.add('enrolled-btn');
                    this.disabled = true;
                    icon.className = 'fas fa-check-circle';
                    this.style.transition = 'all 0.3s ease';
                    this.style.transform = 'scale(1.05)';
                    setTimeout(() => (this.style.transform = 'scale(1)'), 300);
                    showSuccess(data.message);
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showError(data.message || 'Failed to enroll in video.');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('An error occurred during enrollment.');
            }
        });
    });

    // Copy M-Pesa Number functionality with icon feedback
    const copyMpesaBtn = document.querySelector('.copy-mpesa-btn');
    if (copyMpesaBtn) {
        copyMpesaBtn.addEventListener('click', function () {
            const mpesaNumber = this.dataset.mpesaNumber;
            const icon = this.querySelector('i');

            navigator.clipboard.writeText(mpesaNumber).then(() => {
                const messageDiv = document.getElementById('mpesa-copy-message');
                messageDiv.innerHTML = `<i class="fas fa-check-circle"></i> Copied ${mpesaNumber}! Thank you for supporting our facilitators!`;
                messageDiv.classList.add('copy-success-message');
                messageDiv.style.display = 'block';
                messageDiv.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                messageDiv.style.opacity = '1';
                messageDiv.style.transform = 'translateY(0)';
                setTimeout(() => {
                    messageDiv.style.opacity = '0';
                    messageDiv.style.transform = 'translateY(-20px)';
                    setTimeout(() => (messageDiv.style.display = 'none'), 500);
                }, 5000);
                icon.className = 'fas fa-check';
                setTimeout(() => (icon.className = 'far fa-copy'), 1000);
            }).catch(err => {
                console.error('Failed to copy M-Pesa number:', err);
                showError(`Failed to copy number. Please copy manually: ${mpesaNumber}`);
            });
        });
    }

    // Dismiss Ad functionality with animation
    const dismissAdButtons = document.querySelectorAll('.dismiss-ad-btn');
    dismissAdButtons.forEach(button => {
        button.addEventListener('click', async function () {
            const adId = this.dataset.adId;
            const adElement = document.getElementById(`ad-${adId}`);

            try {
                const response = await fetch(`/dismiss_ad/${adId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();

                if (data.success && adElement) {
                    adElement.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
                    adElement.style.opacity = '0';
                    adElement.style.transform = 'translateY(-20px)';
                    setTimeout(() => adElement.remove(), 500);
                } else {
                    showError(data.message || 'Failed to dismiss ad.');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('An error occurred. Please try again.');
            }
        });
    });

    // Navigation toggle for mobile
    const navToggle = document.querySelector('.nav-toggle');
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            const navUl = document.querySelector('nav ul');
            navUl.classList.toggle('active');
            const icon = navToggle.querySelector('i');
            icon.className = navUl.classList.contains('active') ? 'fas fa-times' : 'fas fa-bars';
        });
    }

    // Sidebar toggle for admin
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.toggle('active');
            const icon = sidebarToggle.querySelector('i');
            icon.className = sidebar.classList.contains('active') ? 'fas fa-chevron-left' : 'fas fa-chevron-right';
        });
    }

    // Smooth scroll for internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Form input animation
    const inputs = document.querySelectorAll('.form-group input, .form-group textarea, .form-group select');
    inputs.forEach(input => {
        input.addEventListener('focus', function () {
            this.parentElement.classList.add('focused');
        });
        input.addEventListener('blur', function () {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });

    // Helper function for count animation
    function animateCount(element, target) {
        let start = parseInt(element.textContent) || 0;
        const duration = 500;
        const increment = target > start ? 1 : -1;
        const range = Math.abs(target - start);
        const stepTime = Math.abs(Math.floor(duration / range));
        
        const timer = setInterval(() => {
            start += increment;
            element.textContent = start;
            if (start === target) clearInterval(timer);
        }, stepTime);
    }

    // Helper function for success message
    function showSuccess(message) {
        const div = document.createElement('div');
        div.className = 'alert alert-success';
        div.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
        document.querySelector('.flash-messages').appendChild(div);
        setTimeout(() => {
            div.style.opacity = '0';
            div.style.transform = 'translateY(-20px)';
            setTimeout(() => div.remove(), 500);
        }, 5000);
    }

    // Helper function for error message
    function showError(message) {
        const div = document.createElement('div');
        div.className = 'alert alert-danger';
        div.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        document.querySelector('.flash-messages').appendChild(div);
        setTimeout(() => {
            div.style.opacity = '0';
            div.style.transform = 'translateY(-20px)';
            setTimeout(() => div.remove(), 500);
        }, 5000);
    }
});