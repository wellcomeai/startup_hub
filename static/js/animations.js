/* ============================================================
   AI Community Club — Animations Controller
   Scroll reveals, typewriter, counters, navbar scroll detection
   NO business logic — purely visual enhancements
   ============================================================ */

(function () {
  'use strict';

  /* ───────────────────────────────────────────────
   * 1. Scroll-triggered Reveal (IntersectionObserver)
   * ─────────────────────────────────────────────── */
  function initScrollReveal() {
    var revealEls = document.querySelectorAll('.reveal, .reveal-scale, .stagger-children');
    if (!revealEls.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    revealEls.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* ───────────────────────────────────────────────
   * 2. Typewriter Effect for Terminal Blocks
   * ─────────────────────────────────────────────── */
  function initTypewriter() {
    var typewriterEls = document.querySelectorAll('[data-typewriter]');
    if (!typewriterEls.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          runTypewriter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    typewriterEls.forEach(function (el) {
      observer.observe(el);
    });
  }

  function runTypewriter(container) {
    var lines = container.querySelectorAll('.tw-line');
    var delay = 0;

    lines.forEach(function (line) {
      var text = line.getAttribute('data-text') || line.textContent;
      var speed = parseInt(line.getAttribute('data-speed'), 10) || 30;
      var lineDelay = parseInt(line.getAttribute('data-delay'), 10) || 300;

      line.textContent = '';
      line.style.visibility = 'visible';

      setTimeout(function () {
        var i = 0;
        function type() {
          if (i < text.length) {
            line.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
          }
        }
        type();
      }, delay);

      delay += lineDelay + (text.length * speed);
    });
  }

  /* ───────────────────────────────────────────────
   * 3. Count-Up Animation
   * ─────────────────────────────────────────────── */
  function initCountUp() {
    var countEls = document.querySelectorAll('[data-count-to]');
    if (!countEls.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    countEls.forEach(function (el) {
      observer.observe(el);
    });
  }

  function animateCount(el) {
    var target = parseInt(el.getAttribute('data-count-to'), 10);
    var suffix = el.getAttribute('data-count-suffix') || '';
    var prefix = el.getAttribute('data-count-prefix') || '';
    var duration = 2000;
    var startTime = null;

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = Math.floor(eased * target);
      el.textContent = prefix + current.toLocaleString('ru-RU') + suffix;

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = prefix + target.toLocaleString('ru-RU') + suffix;
      }
    }

    requestAnimationFrame(step);
  }

  /* ───────────────────────────────────────────────
   * 4. Navbar Scroll Detection
   * ─────────────────────────────────────────────── */
  function initNavbarScroll() {
    var navbar = document.querySelector('.navbar');
    if (!navbar) return;

    var scrolled = false;
    window.addEventListener('scroll', function () {
      var isScrolled = window.scrollY > 20;
      if (isScrolled !== scrolled) {
        scrolled = isScrolled;
        navbar.classList.toggle('scrolled', scrolled);
      }
    }, { passive: true });
  }

  /* ───────────────────────────────────────────────
   * 5. Mobile Navigation Toggle
   * ─────────────────────────────────────────────── */
  function initMobileNav() {
    var toggle = document.querySelector('.navbar__toggle');
    var links = document.querySelector('.navbar__links');
    if (!toggle || !links) return;

    toggle.addEventListener('click', function () {
      toggle.classList.toggle('open');
      links.classList.toggle('open');
      document.body.style.overflow = links.classList.contains('open') ? 'hidden' : '';
    });

    // Close menu on link click
    links.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        toggle.classList.remove('open');
        links.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  /* ───────────────────────────────────────────────
   * 6. Mobile Sidebar (Dashboard)
   * ─────────────────────────────────────────────── */
  function initMobileSidebar() {
    var sidebarToggle = document.querySelector('.sidebar-toggle');
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.sidebar-overlay');
    if (!sidebarToggle || !sidebar) return;

    function openSidebar() {
      sidebar.classList.add('open');
      if (overlay) overlay.classList.add('visible');
      document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
      sidebar.classList.remove('open');
      if (overlay) overlay.classList.remove('visible');
      document.body.style.overflow = '';
    }

    sidebarToggle.addEventListener('click', openSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // Close sidebar on nav link click (mobile)
    sidebar.querySelectorAll('.sidebar__link').forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.innerWidth < 1024) {
          closeSidebar();
        }
      });
    });
  }

  /* ───────────────────────────────────────────────
   * 7. Smooth Scroll for anchor links
   * ─────────────────────────────────────────────── */
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
      anchor.addEventListener('click', function (e) {
        var target = document.querySelector(this.getAttribute('href'));
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  /* ───────────────────────────────────────────────
   * Initialize All
   * ─────────────────────────────────────────────── */
  function init() {
    initScrollReveal();
    initTypewriter();
    initCountUp();
    initNavbarScroll();
    initMobileNav();
    initMobileSidebar();
    initSmoothScroll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
