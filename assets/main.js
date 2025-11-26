document.addEventListener('DOMContentLoaded', () => {
    // Navbar scroll effect
    const nav = document.querySelector('nav');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });

    // Scroll Animation Observer
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');

                // Trigger counter animation if it's a stat item
                const counters = entry.target.querySelectorAll('.counter');
                counters.forEach(counter => animateCounter(counter));

                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const fadeElements = document.querySelectorAll('.fade-up');
    fadeElements.forEach(el => observer.observe(el));

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Number Counter Animation
    function animateCounter(counter) {
        const target = parseFloat(counter.getAttribute('data-target'));
        const decimals = parseInt(counter.getAttribute('data-decimals')) || 0;
        const duration = 2000; // 2 seconds
        const start = 0;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Easing function (easeOutExpo)
            const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);

            const current = start + (target - start) * ease;

            if (decimals > 0) {
                counter.innerText = current.toFixed(decimals);
            } else {
                counter.innerText = Math.round(current);
            }

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                if (decimals > 0) {
                    counter.innerText = target.toFixed(decimals);
                } else {
                    counter.innerText = target;
                }
            }
        }

        requestAnimationFrame(update);
    }

    // Seamless Video Loop (Cross-fade)
    const videos = document.querySelectorAll('.video-bg');
    if (videos.length >= 2) {
        let activeIndex = 0;
        const duration = 10; // Assume video is around 10s, or we can read duration
        const crossFadeTime = 1; // 1 second crossfade

        // Initialize
        videos[0].classList.add('active');
        videos[0].play();
        videos[1].pause();
        videos[1].currentTime = 0;

        function checkTime() {
            const activeVideo = videos[activeIndex];
            const nextIndex = (activeIndex + 1) % videos.length;
            const nextVideo = videos[nextIndex];

            // If we are near the end (crossFadeTime before end)
            if (activeVideo.duration && activeVideo.currentTime >= activeVideo.duration - crossFadeTime) {
                // Start next video
                nextVideo.play();
                nextVideo.classList.add('active');

                // Fade out current
                activeVideo.classList.remove('active');

                // Update index
                activeIndex = nextIndex;

                // Reset the old video after transition
                setTimeout(() => {
                    activeVideo.pause();
                    activeVideo.currentTime = 0;
                }, crossFadeTime * 1000);
            }

            requestAnimationFrame(checkTime);
        }

        // Wait for metadata to know duration
        videos[0].addEventListener('loadedmetadata', () => {
            requestAnimationFrame(checkTime);
        });

        // Fallback if metadata already loaded
        if (videos[0].readyState >= 1) {
            requestAnimationFrame(checkTime);
        }
    }

    // Curtain Reveal Effect for RGB to IR transition
    const revealContainer = document.querySelector('.reveal-container');
    if (revealContainer) {
        const revealLayer = revealContainer.querySelector('.reveal-layer');

        function updateReveal() {
            const rect = revealContainer.getBoundingClientRect();
            const windowHeight = window.innerHeight;

            // Start revealing when element is at bottom 1/3 of viewport
            // Complete when element is at top 1/3 of viewport
            const elementTop = rect.top;
            const elementHeight = rect.height;

            // Calculate progress: 0 when element at bottom 1/3, 1 when at top 1/3
            const startTrigger = windowHeight * 2 / 3;  // Bottom 1/3 position
            const endTrigger = windowHeight / 3;         // Top 1/3 position

            if (elementTop >= startTrigger) {
                // Before reveal starts
                revealLayer.style.width = '0%';
            } else if (elementTop <= endTrigger) {
                // After reveal completes
                revealLayer.style.width = '100%';
            } else {
                // During reveal
                const progress = (startTrigger - elementTop) / (startTrigger - endTrigger);
                revealLayer.style.width = `${progress * 100}%`;
            }
        }

        window.addEventListener('scroll', updateReveal);
        window.addEventListener('resize', updateReveal);

        // Initial update
        updateReveal();
    }

    // Technique Carousel Auto-rotation
    const carouselSlides = document.querySelectorAll('.carousel-slide');
    const techniqueTags = document.querySelectorAll('.technique-tag');
    let currentSlide = 0;
    let carouselInterval;

    function showSlide(index) {
        // Remove active class from all slides and tags
        carouselSlides.forEach(slide => slide.classList.remove('active'));
        techniqueTags.forEach(tag => tag.classList.remove('active'));

        // Add active class to current slide and tag
        carouselSlides[index].classList.add('active');
        techniqueTags[index].classList.add('active');

        currentSlide = index;
    }

    function nextSlide() {
        const next = (currentSlide + 1) % carouselSlides.length;
        showSlide(next);
    }

    function startCarousel() {
        carouselInterval = setInterval(nextSlide, 5000); // Change slide every 5 seconds
    }

    function stopCarousel() {
        clearInterval(carouselInterval);
    }

    // Tag click handlers
    techniqueTags.forEach((tag, index) => {
        tag.addEventListener('click', () => {
            stopCarousel();
            showSlide(index);
            startCarousel(); // Restart auto-rotation after manual click
        });
    });

    // Start auto-rotation if carousel exists
    if (carouselSlides.length > 0) {
        startCarousel();
    }

    // Mobile Author Interaction (Double-tap)
    const authors = document.querySelectorAll('.author');

    authors.forEach(author => {
        author.addEventListener('click', (e) => {
            // Check if we are on mobile (using the same breakpoint as CSS)
            if (window.innerWidth <= 768) {
                // If not already active, prevent navigation and show avatar
                if (!author.classList.contains('hover-active')) {
                    e.preventDefault();

                    // Remove active class from all other authors
                    authors.forEach(a => a.classList.remove('hover-active'));

                    // Add active class to clicked author
                    author.classList.add('hover-active');
                }
                // If already active, allow default behavior (navigation)
            }
        });
    });

    // Close author avatar when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.author')) {
            authors.forEach(author => author.classList.remove('hover-active'));
        }
    });
});
