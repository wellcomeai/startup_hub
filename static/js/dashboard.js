/**
 * Dashboard Logic for AI Community Club
 *
 * Handles the authenticated dashboard area including:
 *  - Auth guard (redirect when no token)
 *  - User profile loading and display
 *  - Section navigation (Overview, Team, Commissions, Profile, Subscription)
 *  - Team listing with level-1 / level-2 tabs
 *  - Commission history with filtering
 *  - Profile editing and referrer assignment
 *  - Subscription display and test activation
 *  - Logout and referral link copying
 */

'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let currentUser = null;

// ---------------------------------------------------------------------------
// Auth guard
// ---------------------------------------------------------------------------

/**
 * Ensure the visitor has a valid token. Redirect to the landing page if not.
 */
const requireAuth = () => {
    if (!isAuthenticated()) {
        window.location.href = '/static/index.html';
        return false;
    }
    return true;
};

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

/**
 * Switch the visible dashboard section.
 *
 * @param {string} sectionId - The id of the section element to show.
 */
const navigateTo = (sectionId) => {
    // Hide all sections
    document.querySelectorAll('.dashboard-section').forEach((section) => {
        section.style.display = 'none';
    });

    // Show the requested section
    const target = document.getElementById(sectionId);
    if (target) {
        target.style.display = 'block';
    }

    // Update active nav link
    document.querySelectorAll('.nav-link').forEach((link) => {
        link.classList.toggle('active', link.dataset.section === sectionId);
    });

    // Lazy-load section data
    const loaders = {
        'section-overview': loadOverview,
        'section-team': loadTeam,
        'section-commissions': loadCommissions,
        'section-profile': loadProfile,
        'section-subscription': loadSubscription,
    };

    const loader = loaders[sectionId];
    if (loader) loader();
};

/**
 * Wire sidebar / navbar links to navigateTo.
 */
const initNavigation = () => {
    document.querySelectorAll('.nav-link').forEach((link) => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            if (section) navigateTo(section);
        });
    });
};

// ---------------------------------------------------------------------------
// Overview section
// ---------------------------------------------------------------------------

const loadOverview = async () => {
    try {
        const data = await api.get('/users/me');
        currentUser = data;
        renderOverview(data);
    } catch (err) {
        showNotification('Не удалось загрузить профиль', 'error');
    }
};

const renderOverview = (user) => {
    // User greeting
    const greetEl = document.getElementById('overview-greeting');
    if (greetEl) {
        greetEl.textContent = `Привет, ${user.first_name || user.email}!`;
    }

    // Partner status badge
    const statusEl = document.getElementById('overview-partner-status');
    if (statusEl) {
        statusEl.textContent = getPartnerStatusLabel(user.partner_status);
        statusEl.style.backgroundColor = getPartnerStatusColor(user.partner_status);
    }

    // Subscription info
    const subEl = document.getElementById('overview-subscription');
    if (subEl) {
        if (user.subscription) {
            subEl.innerHTML = `
                <strong>${user.subscription.plan_name}</strong>
                (${user.subscription.billing_period === 'yearly' ? 'годовая' : 'месячная'})
                &mdash; ${user.subscription.status === 'active' ? 'Активна' : user.subscription.status}
                ${user.subscription.expires_at ? ', до ' + formatDate(user.subscription.expires_at) : ''}
            `;
        } else {
            subEl.textContent = 'Нет активной подписки';
        }
    }

    // Referral stats
    const statsMap = {
        'stat-level1': user.stats?.total_referrals_level1,
        'stat-level2': user.stats?.total_referrals_level2,
        'stat-paid-referrals': user.stats?.total_paid_referrals,
        'stat-total-earned': formatCurrency(user.stats?.total_commissions_earned || 0),
        'stat-total-paid': formatCurrency(user.stats?.total_commissions_paid || 0),
    };

    for (const [id, value] of Object.entries(statsMap)) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    // Referral link
    const refLinkEl = document.getElementById('overview-referral-link');
    if (refLinkEl && user.referral_code) {
        const link = `${window.location.origin}/static/index.html?ref=${user.referral_code}`;
        refLinkEl.textContent = link;
        refLinkEl.dataset.link = link;
    }

    const refCodeEl = document.getElementById('overview-referral-code');
    if (refCodeEl) {
        refCodeEl.textContent = user.referral_code || '';
    }

    // Referrer info
    const referrerEl = document.getElementById('overview-referrer');
    if (referrerEl) {
        if (user.referred_by) {
            referrerEl.textContent = `${user.referred_by.first_name || ''} (${user.referred_by.email})`;
        } else {
            referrerEl.textContent = 'Не указан';
        }
    }
};

// ---------------------------------------------------------------------------
// Team section
// ---------------------------------------------------------------------------

let teamData = null;

const loadTeam = async () => {
    const container = document.getElementById('team-content');
    if (!container) return;

    try {
        teamData = await api.get('/referrals/my-team');
        renderTeamTotals(teamData.totals);
        // Default to level-1 tab
        renderTeamLevel('level1');
    } catch (err) {
        container.innerHTML = '<p>Не удалось загрузить команду.</p>';
    }
};

const renderTeamTotals = (totals) => {
    const map = {
        'team-total': totals.total_team_size,
        'team-level1-count': totals.level1_count,
        'team-level1-paid': totals.level1_paid_count,
        'team-level2-count': totals.level2_count,
        'team-level2-paid': totals.level2_paid_count,
    };

    for (const [id, value] of Object.entries(map)) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
};

/**
 * Render either the level-1 or level-2 team table.
 *
 * @param {'level1'|'level2'} level
 */
const renderTeamLevel = (level) => {
    if (!teamData) return;

    // Update tab active state
    document.querySelectorAll('.team-tab').forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.level === level);
    });

    const tbody = document.getElementById('team-table-body');
    if (!tbody) return;

    const members = level === 'level1' ? teamData.level1 : teamData.level2;

    if (members.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center">Нет рефералов ${level === 'level1' ? '1-го' : '2-го'} уровня</td></tr>`;
        return;
    }

    if (level === 'level1') {
        tbody.innerHTML = members.map((m) => `
            <tr>
                <td>${m.first_name || ''} ${m.last_name || ''}</td>
                <td>${m.email}</td>
                <td>${formatDate(m.registered_at)}</td>
                <td>${m.has_active_subscription
                    ? `<span class="badge badge-success">${m.subscription_plan || 'Да'}</span>`
                    : '<span class="badge badge-muted">Нет</span>'}</td>
                <td>${m.consecutive_months || 0}</td>
                <td>${formatCurrency(m.my_commission_from_user)}</td>
            </tr>
        `).join('');
    } else {
        tbody.innerHTML = members.map((m) => `
            <tr>
                <td>${m.first_name || ''}</td>
                <td>${m.email}</td>
                <td>${formatDate(m.registered_at)}</td>
                <td>${m.has_active_subscription
                    ? '<span class="badge badge-success">Да</span>'
                    : '<span class="badge badge-muted">Нет</span>'}</td>
                <td>${m.invited_by?.first_name || ''} (${m.invited_by?.referral_code || ''})</td>
                <td>${formatCurrency(m.my_commission_from_user)}</td>
            </tr>
        `).join('');
    }
};

const initTeamTabs = () => {
    document.querySelectorAll('.team-tab').forEach((tab) => {
        tab.addEventListener('click', () => {
            const level = tab.dataset.level;
            if (level) renderTeamLevel(level);
        });
    });
};

// ---------------------------------------------------------------------------
// Commissions section
// ---------------------------------------------------------------------------

let commissionsPage = 1;
let commissionsFilter = 'all';

const loadCommissions = async () => {
    const container = document.getElementById('commissions-content');
    if (!container) return;

    try {
        const params = new URLSearchParams({
            page: commissionsPage,
            per_page: 50,
            commission_type: commissionsFilter,
        });
        const data = await api.get(`/referrals/my-commissions?${params}`);
        renderCommissionsSummary(data.summary);
        renderCommissionsTable(data.commissions);
        renderCommissionsPagination(data.pagination);
    } catch (err) {
        container.innerHTML = '<p>Не удалось загрузить комиссии.</p>';
    }
};

const renderCommissionsSummary = (summary) => {
    const map = {
        'comm-total-earned': formatCurrency(summary.total_earned),
        'comm-total-paid': formatCurrency(summary.total_paid),
        'comm-total-pending': formatCurrency(summary.total_pending),
        'comm-type-direct': formatCurrency(summary.by_type?.direct || 0),
        'comm-type-level2': formatCurrency(summary.by_type?.level2 || 0),
        'comm-type-retention': formatCurrency(summary.by_type?.retention || 0),
    };

    for (const [id, value] of Object.entries(map)) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
};

const renderCommissionsTable = (commissions) => {
    const tbody = document.getElementById('commissions-table-body');
    if (!tbody) return;

    if (commissions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center">Нет комиссий</td></tr>';
        return;
    }

    const typeLabels = {
        direct: 'Прямая',
        level2: '2-й уровень',
        retention: 'Удержание',
    };

    const statusLabels = {
        pending: 'Ожидает',
        paid: 'Выплачена',
        cancelled: 'Отменена',
    };

    tbody.innerHTML = commissions.map((c) => `
        <tr>
            <td>${formatDateTime(c.accrued_at)}</td>
            <td>${typeLabels[c.commission_type] || c.commission_type}</td>
            <td>${c.referral_level || ''}</td>
            <td>${c.payer?.first_name || ''} (${c.payer?.email || ''})</td>
            <td>${formatCurrency(c.payment_amount)}</td>
            <td>${(c.commission_rate * 100).toFixed(0)}%</td>
            <td>${formatCurrency(c.commission_amount)}</td>
            <td><span class="badge badge-${c.status === 'paid' ? 'success' : 'muted'}">${statusLabels[c.status] || c.status}</span></td>
        </tr>
    `).join('');
};

const renderCommissionsPagination = (pagination) => {
    const container = document.getElementById('commissions-pagination');
    if (!container) return;

    if (pagination.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';
    for (let i = 1; i <= pagination.total_pages; i++) {
        html += `<button class="btn btn-sm ${i === pagination.page ? 'btn-active' : ''}" data-page="${i}">${i}</button> `;
    }
    container.innerHTML = html;

    container.querySelectorAll('button[data-page]').forEach((btn) => {
        btn.addEventListener('click', () => {
            commissionsPage = parseInt(btn.dataset.page, 10);
            loadCommissions();
        });
    });
};

const initCommissionsFilters = () => {
    document.querySelectorAll('.commission-filter').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.commission-filter').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            commissionsFilter = btn.dataset.type || 'all';
            commissionsPage = 1;
            loadCommissions();
        });
    });
};

// ---------------------------------------------------------------------------
// Profile section
// ---------------------------------------------------------------------------

const loadProfile = async () => {
    try {
        const data = currentUser || await api.get('/users/me');
        currentUser = data;
        renderProfileForm(data);
        renderReferrerForm(data);
    } catch (err) {
        showNotification('Не удалось загрузить профиль', 'error');
    }
};

const renderProfileForm = (user) => {
    const form = document.getElementById('profile-form');
    if (!form) return;

    const fields = ['first_name', 'last_name', 'phone', 'telegram', 'city', 'about'];
    fields.forEach((field) => {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) input.value = user[field] || '';
    });

    const emailEl = document.getElementById('profile-email');
    if (emailEl) emailEl.textContent = user.email;
};

const initProfileForm = () => {
    const form = document.getElementById('profile-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const payload = {};
        for (const [key, value] of formData.entries()) {
            payload[key] = value.trim() || null;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        try {
            const data = await api.put('/users/me', payload);
            currentUser = { ...currentUser, ...data };
            showNotification('Профиль обновлён');
        } catch (err) {
            showNotification(err.message || 'Ошибка обновления профиля', 'error');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });
};

const renderReferrerForm = (user) => {
    const container = document.getElementById('set-referrer-container');
    if (!container) return;

    if (user.referred_by) {
        container.innerHTML = `
            <p>Ваш реферер: <strong>${user.referred_by.first_name || ''}</strong>
            (${user.referred_by.email})</p>
        `;
    }
    // If no referrer, the form is shown by default in the HTML
};

const initSetReferrerForm = () => {
    const form = document.getElementById('set-referrer-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const codeInput = form.querySelector('[name="referral_code"]');
        const code = codeInput?.value.trim();

        if (!code) {
            showNotification('Введите реферальный код', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        try {
            const data = await api.post('/users/me/set-referrer', { referral_code: code });
            showNotification('Реферер установлен');

            // Update the UI
            const container = document.getElementById('set-referrer-container');
            if (container && data.referred_by) {
                container.innerHTML = `
                    <p>Ваш реферер: <strong>${data.referred_by.first_name || ''}</strong>
                    (код: ${data.referred_by.referral_code})</p>
                `;
            }

            // Refresh currentUser
            currentUser = await api.get('/users/me');
        } catch (err) {
            showNotification(err.message || 'Ошибка установки реферера', 'error');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });
};

// ---------------------------------------------------------------------------
// Subscription section
// ---------------------------------------------------------------------------

const loadSubscription = async () => {
    await Promise.all([
        loadCurrentSubscription(),
        loadSubscriptionPlans(),
    ]);
};

const loadCurrentSubscription = async () => {
    const container = document.getElementById('current-subscription');
    if (!container) return;

    try {
        const data = await api.get('/subscriptions/my');

        if (data.has_subscription && data.subscription) {
            const sub = data.subscription;
            container.innerHTML = `
                <div class="subscription-card active">
                    <h4>${sub.plan_name}</h4>
                    <p>Статус: <strong>${sub.status === 'active' ? 'Активна' : sub.status}</strong></p>
                    <p>Период: ${sub.billing_period === 'yearly' ? 'Годовая' : 'Месячная'}</p>
                    <p>Начало: ${formatDate(sub.started_at)}</p>
                    <p>Окончание: ${formatDate(sub.expires_at)}</p>
                    <p>Осталось дней: <strong>${sub.days_remaining}</strong></p>
                    <p>Месяцев подряд: ${sub.consecutive_months}</p>
                </div>
            `;
        } else {
            container.innerHTML = '<p>У вас нет активной подписки.</p>';
        }
    } catch (err) {
        container.innerHTML = '<p>Не удалось загрузить подписку.</p>';
    }
};

const loadSubscriptionPlans = async () => {
    const container = document.getElementById('subscription-plans');
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
                    <h4>${plan.name}</h4>
                    ${plan.description ? `<p class="plan-description">${plan.description}</p>` : ''}
                    <div class="plan-price">
                        ${formatCurrency(plan.price_monthly)} / мес
                    </div>
                    ${plan.price_yearly
                        ? `<div class="plan-price-yearly">
                               ${formatCurrency(plan.price_yearly)} / год
                               (экономия ${formatCurrency(plan.yearly_savings)})
                           </div>`
                        : ''
                    }
                    <ul class="plan-features">${features}</ul>
                    <button class="btn btn-activate-test" data-plan-code="${plan.code}">
                        Тестовая активация
                    </button>
                </div>
            `;
        }).join('');

        // Bind test-activate buttons
        container.querySelectorAll('.btn-activate-test').forEach((btn) => {
            btn.addEventListener('click', () => activateTestSubscription(btn.dataset.planCode));
        });
    } catch (err) {
        container.innerHTML = '<p>Не удалось загрузить тарифы.</p>';
    }
};

/**
 * Activate a test subscription (no real payment).
 *
 * @param {string} planCode
 */
const activateTestSubscription = async (planCode) => {
    if (!planCode) return;

    try {
        const data = await api.post('/subscriptions/activate-test', {
            plan_code: planCode,
            months: 1,
        });

        showNotification('Подписка активирована (тест)');

        // Refresh subscription display
        await loadCurrentSubscription();

        // Refresh user data so overview also reflects changes
        currentUser = await api.get('/users/me');
    } catch (err) {
        showNotification(err.message || 'Ошибка активации подписки', 'error');
    }
};

// ---------------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------------

const initLogout = () => {
    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            logout();
        });
    }
};

// ---------------------------------------------------------------------------
// Referral link copy
// ---------------------------------------------------------------------------

const initCopyReferralLink = () => {
    const copyBtn = document.getElementById('btn-copy-referral');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const linkEl = document.getElementById('overview-referral-link');
            const link = linkEl?.dataset.link || linkEl?.textContent;
            if (link) {
                copyToClipboard(link);
            }
        });
    }
};

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    if (!requireAuth()) return;

    initNavigation();
    initTeamTabs();
    initCommissionsFilters();
    initProfileForm();
    initSetReferrerForm();
    initLogout();
    initCopyReferralLink();

    // Show the overview section by default
    navigateTo('section-overview');
});
