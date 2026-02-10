/**
 * Landing Page Logic for AI Community Club
 *
 * Handles:
 *  - Referral code detection from ?ref= query parameter
 *  - Tab switching between Login / Register forms
 *  - Registration and login form submissions
 *  - Loading and rendering pricing plans
 *  - Smooth-scroll navigation to page sections
 */

'use strict';

// ---------------------------------------------------------------------------
// Referral code handling
// ---------------------------------------------------------------------------

/**
 * Check the URL for a ?ref= parameter. When present, persist it in
 * localStorage and validate it against the backend so we can display an
 * invitation message.
 */
const handleReferralCode = async () => {
    const params = new URLSearchParams(window.location.search);
    const refCode = params.get('ref');

    if (refCode) {
        localStorage.setItem('referral_code', refCode.toUpperCase());
    }

    const storedCode = localStorage.getItem('referral_code');
    if (!storedCode) return;

    try {
        // Validate the referral code by attempting to look up the referrer.
        // We use the register endpoint's validation indirectly -- instead we
        // call a lightweight check. Since there is no dedicated endpoint we
        // attempt a GET to the public plans endpoint with the code as a query
        // to keep things simple. A cleaner approach would be a dedicated
        // /api/referrals/validate?code=... endpoint. For now we store the
        // code and show a generic message, catching errors silently.
        const data = await api.get(`/auth/validate-referral?code=${encodeURIComponent(storedCode)}`).catch(() => null);

        const banner = document.getElementById('referral-banner');
        if (banner) {
            if (data && data.referrer_name) {
                banner.innerHTML = `<span>&#128075; </span> ${data.referrer_name}`;
                banner.style.display = 'block';
            } else {
                // Even without server validation, show a generic message
                banner.textContent = '\u0412\u0430\u0441 \u043f\u0440\u0438\u0433\u043b\u0430\u0441\u0438\u043b\u0438 \u043f\u043e \u0440\u0435\u0444\u0435\u0440\u0430\u043b\u044c\u043d\u043e\u043c\u0443 \u043a\u043e\u0434\u0443: ' + storedCode;
                banner.style.display = 'block';
            }
        }
    } catch {
        // Validation endpoint may not exist yet -- that is okay.
    }
};

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

/**
 * Wire up the login / register tab buttons so only one form is visible
 * at a time.
 */
const initAuthTabs = () => {
    const loginTab = document.getElementById('tab-login');
    const registerTab = document.getElementById('tab-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (!loginTab || !registerTab || !loginForm || !registerForm) return;

    const activate = (activeTab, inactiveTab, showForm, hideForm) => {
        activeTab.classList.add('active');
        inactiveTab.classList.remove('active');
        showForm.style.display = 'block';
        hideForm.style.display = 'none';
    };

    loginTab.addEventListener('click', () =>
        activate(loginTab, registerTab, loginForm, registerForm),
    );

    registerTab.addEventListener('click', () =>
        activate(registerTab, loginTab, registerForm, loginForm),
    );
};

// ---------------------------------------------------------------------------
// Auth form submissions
// ---------------------------------------------------------------------------

/**
 * Handle successful authentication (shared between login & register).
 */
const handleAuthSuccess = (data) => {
    setToken(data.token);
    setUser(data.user);
    showNotification('Добро пожаловать!');
    setTimeout(() => {
        window.location.href = '/static/dashboard.html';
    }, 400);
};

/**
 * Bind the register form.
 */
const initRegisterForm = () => {
    const form = document.getElementById('register-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = form.querySelector('[name="email"]')?.value.trim();
        const password = form.querySelector('[name="password"]')?.value;
        const firstName = form.querySelector('[name="first_name"]')?.value.trim();
        const referralCode = localStorage.getItem('referral_code') || undefined;

        if (!email || !password) {
            showNotification('Заполните email и пароль', 'error');
            return;
        }

        if (password.length < 6) {
            showNotification('Пароль должен содержать минимум 6 символов', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        try {
            const data = await api.post('/auth/register', {
                email,
                password,
                first_name: firstName || undefined,
                referral_code: referralCode,
            });
            handleAuthSuccess(data);
        } catch (err) {
            showNotification(err.message || 'Ошибка регистрации', 'error');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });
};

/**
 * Bind the login form.
 */
const initLoginForm = () => {
    const form = document.getElementById('login-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = form.querySelector('[name="email"]')?.value.trim();
        const password = form.querySelector('[name="password"]')?.value;

        if (!email || !password) {
            showNotification('Заполните email и пароль', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        try {
            const data = await api.post('/auth/login', { email, password });
            handleAuthSuccess(data);
        } catch (err) {
            showNotification(err.message || 'Неверный email или пароль', 'error');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });
};

// ---------------------------------------------------------------------------
// Pricing plans
// ---------------------------------------------------------------------------

/**
 * Fetch subscription plans from the API and render them into the pricing
 * section of the landing page.
 */
const loadPricingPlans = async () => {
    const container = document.getElementById('pricing-plans');
    if (!container) return;

    try {
        const data = await api.get('/subscriptions/plans');
        const plans = data.plans || [];

        if (plans.length === 0) {
            container.innerHTML = '<p>Тарифы скоро появятся.</p>';
            return;
        }

        container.innerHTML = plans.map((plan) => {
            const features = (plan.features || [])
                .map((f) => `<li>${f}</li>`)
                .join('');

            return `
                <div class="plan-card" data-plan="${plan.code}">
                    <h3 class="plan-name">${plan.name}</h3>
                    ${plan.description ? `<p class="plan-description">${plan.description}</p>` : ''}
                    <div class="plan-price">
                        <span class="price-monthly">${formatCurrency(plan.price_monthly)}</span>
                        <span class="price-period">/ мес</span>
                    </div>
                    ${plan.price_yearly
                        ? `<div class="plan-price-yearly">
                               ${formatCurrency(plan.price_yearly)} / год
                               <span class="yearly-savings">Экономия ${formatCurrency(plan.yearly_savings)}</span>
                           </div>`
                        : ''
                    }
                    <ul class="plan-features">${features}</ul>
                    <button class="btn btn-plan" data-plan-code="${plan.code}">Выбрать</button>
                </div>
            `;
        }).join('');

        // Clicking a plan button scrolls to the auth section (or opens it)
        container.querySelectorAll('.btn-plan').forEach((btn) => {
            btn.addEventListener('click', () => {
                const authSection = document.getElementById('auth');
                if (authSection) {
                    authSection.scrollIntoView({ behavior: 'smooth' });
                }
                // Activate the register tab by default
                const registerTab = document.getElementById('tab-register');
                if (registerTab) registerTab.click();
            });
        });
    } catch (err) {
        container.innerHTML = '<p>Не удалось загрузить тарифы.</p>';
    }
};

// ---------------------------------------------------------------------------
// Smooth scroll
// ---------------------------------------------------------------------------

/**
 * Enable smooth scrolling for all anchor links whose href starts with "#".
 */
const initSmoothScroll = () => {
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', (e) => {
            const targetId = anchor.getAttribute('href').slice(1);
            if (!targetId) return;

            const target = document.getElementById(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
};

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    // If the user is already authenticated, redirect straight to dashboard
    if (isAuthenticated()) {
        window.location.href = '/static/dashboard.html';
        return;
    }

    handleReferralCode();
    initAuthTabs();
    initRegisterForm();
    initLoginForm();
    loadPricingPlans();
    initSmoothScroll();
});
