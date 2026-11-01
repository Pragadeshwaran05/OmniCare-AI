/**
 * ============================================================
 * OMNICARE AI — DOCTOR PORTAL: ACCESS & AUDIT LOG CONTROLLER
 * Full client-side integration with backend REST endpoints.
 * Safe DOM rendering, responsive tab management, and modals.
 * ============================================================
 */

(function () {
    'use strict';

    // State
    const state = {
        activeTab: 'patients',
        summary: {
            total_requests: 0,
            active_access: 0,
            pending_requests: 0,
            revoked_expired: 0
        },
        patients: {
            page: 1,
            per_page: 10,
            status: 'all',
            type: 'all',
            q: '',
            total: 0,
            total_pages: 1
        },
        requests: {
            page: 1,
            per_page: 10,
            status: 'all',
            q: '',
            total: 0,
            total_pages: 1
        },
        audit: {
            page: 1,
            per_page: 12,
            action: '',
            patient_id: '',
            start_date: '',
            end_date: '',
            q: '',
            total: 0,
            total_pages: 1
        },
        selectedPatientForRequest: null,
        notifications: [],
        unreadNotificationsCount: 0
    };

    // Helper: Escape HTML to prevent XSS
    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Helper: Debounce function for search inputs
    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // Helper: Format ISO timestamp
    function formatDateTime(isoString) {
        if (!isoString) return '—';
        try {
            const dt = new Date(isoString);
            if (isNaN(dt.getTime())) return String(isoString);
            return dt.toLocaleString('en-US', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });
        } catch (e) {
            return String(isoString);
        }
    }

    // Helper: Relative time string
    function timeAgo(isoString) {
        if (!isoString) return '';
        try {
            const dt = new Date(isoString);
            const now = new Date();
            const diffSeconds = Math.floor((now - dt) / 1000);
            if (diffSeconds < 60) return 'Just now';
            if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
            if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
            return `${Math.floor(diffSeconds / 86400)}d ago`;
        } catch (e) {
            return '';
        }
    }

    // ============================================================
    // API 1: LOAD ACCESS SUMMARY (4 OVERVIEW CARDS)
    // ============================================================
    async function loadSummary() {
        try {
            const res = await fetch('/doctor/access-audit/api/summary');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.success && data.summary) {
                state.summary = data.summary;
                updateOverviewCards();
            }
        } catch (err) {
            console.error('Failed to load access summary:', err);
        }
    }

    function updateOverviewCards() {
        const totalEl = document.getElementById('overviewTotalRequests');
        const activeEl = document.getElementById('overviewActiveAccess');
        const pendingEl = document.getElementById('overviewPendingRequests');
        const revokedEl = document.getElementById('overviewRevokedExpired');

        if (totalEl) totalEl.textContent = state.summary.total_requests;
        if (activeEl) activeEl.textContent = state.summary.active_access;
        if (pendingEl) pendingEl.textContent = state.summary.pending_requests;
        if (revokedEl) revokedEl.textContent = state.summary.revoked_expired;
    }

    // ============================================================
    // TAB 1: MY PATIENT ACCESS
    // ============================================================
    async function loadPatients() {
        const tbody = document.getElementById('patientsTableBody');
        const loadingEl = document.getElementById('patientsLoading');
        const emptyEl = document.getElementById('patientsEmpty');
        const errorEl = document.getElementById('patientsError');
        const countBadge = document.getElementById('patientCountBadge');

        if (loadingEl) loadingEl.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
        if (tbody) tbody.innerHTML = '';

        try {
            const params = new URLSearchParams({
                page: state.patients.page,
                per_page: state.patients.per_page,
                status: state.patients.status,
                type: state.patients.type,
                q: state.patients.q
            });

            const res = await fetch(`/doctor/access-audit/api/patients?${params.toString()}`);
            if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
            const data = await res.json();

            if (loadingEl) loadingEl.style.display = 'none';

            if (!data.success) {
                if (errorEl) {
                    errorEl.style.display = 'block';
                    errorEl.textContent = data.error || 'Failed to load authorized patients.';
                }
                return;
            }

            state.patients.total = data.total || 0;
            state.patients.total_pages = data.total_pages || 1;
            if (countBadge) countBadge.textContent = state.patients.total;

            renderPatientsTable(data.patients || []);
            renderPatientsPagination();

        } catch (err) {
            if (loadingEl) loadingEl.style.display = 'none';
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Unable to connect to patient access service. Please check your network.';
            }
            console.error('Error fetching patients:', err);
        }
    }

    function renderPatientsTable(patients) {
        const tbody = document.getElementById('patientsTableBody');
        const emptyEl = document.getElementById('patientsEmpty');
        if (!tbody) return;

        if (!patients || patients.length === 0) {
            if (emptyEl) emptyEl.style.display = 'block';
            return;
        }

        let html = '';
        patients.forEach(pt => {
            const statusClass = pt.status.toLowerCase();
            const typeClass = (pt.access_type || 'temporary').toLowerCase();
            const canView = pt.can_view_records;

            html += `
                <tr>
                    <td class="col-patient-id">
                        <span class="patient-id-badge" title="${escapeHtml(pt.patient_id)}">
                            ${escapeHtml(pt.health_id || pt.patient_id.substring(0, 8))}
                        </span>
                    </td>
                    <td class="col-patient-name">
                        <div class="patient-name-cell">${escapeHtml(pt.patient_name)}</div>
                        <div class="patient-sub-meta">${escapeHtml(pt.gender || '')}</div>
                    </td>
                    <td class="col-access-type">
                        <span class="type-badge type-${typeClass}">
                            ${escapeHtml(pt.access_type)}
                        </span>
                    </td>
                    <td class="col-granted-at">
                        <div class="date-time-cell">${escapeHtml(pt.granted_display)}</div>
                    </td>
                    <td class="col-expiry">
                        <div class="date-time-cell">${escapeHtml(pt.expires_display)}</div>
                    </td>
                    <td class="col-status">
                        <span class="status-pill ${statusClass}">
                            ● ${escapeHtml(formatStatusLabel(pt.status))}
                        </span>
                    </td>
                    <td class="col-actions" style="text-align: right;">
                        <div class="action-btn-group">
                            ${canView ? `
                                <a href="/doctor/patient-workspace/${encodeURIComponent(pt.patient_id)}" class="btn-table-action primary" title="Open Patient Workspace">
                                    View Records &rarr;
                                </a>
                            ` : `
                                <button type="button" class="btn-table-action" disabled title="Access has expired or is inactive" style="opacity: 0.5; cursor: not-allowed;">
                                    View Records
                                </button>
                            `}
                            <button type="button" class="btn-table-action" onclick="window.OmniCareAudit.viewConsent('${escapeHtml(pt.access_id)}')">
                                Consent
                            </button>
                            <button type="button" class="btn-table-action" onclick="window.OmniCareAudit.filterAuditForPatient('${escapeHtml(pt.patient_id)}')">
                                History
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    function formatStatusLabel(st) {
        if (!st) return 'Unknown';
        if (st === 'expiring_soon') return 'Expiring Soon';
        return st.charAt(0).toUpperCase() + st.slice(1);
    }

    function renderPatientsPagination() {
        const infoEl = document.getElementById('patientsPageInfo');
        const prevBtn = document.getElementById('patientsPrevBtn');
        const nextBtn = document.getElementById('patientsNextBtn');

        if (infoEl) {
            infoEl.textContent = `Page ${state.patients.page} of ${state.patients.total_pages} (${state.patients.total} patients)`;
        }
        if (prevBtn) prevBtn.disabled = state.patients.page <= 1;
        if (nextBtn) nextBtn.disabled = state.patients.page >= state.patients.total_pages;
    }

    // ============================================================
    // TAB 2: ACCESS REQUESTS
    // ============================================================
    async function loadRequests() {
        const tbody = document.getElementById('requestsTableBody');
        const loadingEl = document.getElementById('requestsLoading');
        const emptyEl = document.getElementById('requestsEmpty');
        const errorEl = document.getElementById('requestsError');
        const countBadge = document.getElementById('requestsCountBadge');

        if (loadingEl) loadingEl.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
        if (tbody) tbody.innerHTML = '';

        try {
            const params = new URLSearchParams({
                page: state.requests.page,
                per_page: state.requests.per_page,
                status: state.requests.status,
                q: state.requests.q
            });

            const res = await fetch(`/doctor/access-audit/api/requests?${params.toString()}`);
            if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
            const data = await res.json();

            if (loadingEl) loadingEl.style.display = 'none';

            if (!data.success) {
                if (errorEl) {
                    errorEl.style.display = 'block';
                    errorEl.textContent = data.error || 'Failed to load access requests.';
                }
                return;
            }

            state.requests.total = data.total || 0;
            state.requests.total_pages = data.total_pages || 1;
            if (countBadge) countBadge.textContent = state.requests.total;

            renderRequestsTable(data.requests || []);
            renderRequestsPagination();

        } catch (err) {
            if (loadingEl) loadingEl.style.display = 'none';
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Unable to retrieve access requests. Please try again.';
            }
            console.error('Error fetching requests:', err);
        }
    }

    function renderRequestsTable(requests) {
        const tbody = document.getElementById('requestsTableBody');
        const emptyEl = document.getElementById('requestsEmpty');
        if (!tbody) return;

        if (!requests || requests.length === 0) {
            if (emptyEl) emptyEl.style.display = 'block';
            return;
        }

        let html = '';
        requests.forEach(req => {
            const st = (req.status || 'pending').toLowerCase();
            const typeClass = (req.access_type || 'temporary').toLowerCase();
            const isPending = (st === 'pending');
            const isInactive = ['rejected', 'cancelled', 'expired'].includes(st);

            html += `
                <tr>
                    <td class="col-req-id">
                        <span class="patient-id-badge" title="${escapeHtml(req.id)}">
                            ${escapeHtml(req.id.substring(0, 8))}...
                        </span>
                    </td>
                    <td class="col-req-name">
                        <div class="patient-name-cell">${escapeHtml(req.patient_name)}</div>
                        <div class="patient-sub-meta" title="${escapeHtml(req.purpose)}">${escapeHtml(req.purpose)}</div>
                    </td>
                    <td class="col-req-health-id">
                        <span class="patient-id-badge">${escapeHtml(req.health_id)}</span>
                    </td>
                    <td class="col-req-type">
                        <span class="type-badge type-${typeClass}">${escapeHtml(req.access_type)}</span>
                    </td>
                    <td class="col-req-requested-at">
                        <div class="date-time-cell">${escapeHtml(req.requested_display)}</div>
                    </td>
                    <td class="col-req-status">
                        <span class="status-pill ${st}">
                            ● ${escapeHtml(formatStatusLabel(st))}
                        </span>
                    </td>
                    <td class="col-req-actions" style="text-align: right;">
                        <div class="action-btn-group">
                            <button type="button" class="btn-table-action" onclick="window.OmniCareAudit.viewConsent('${escapeHtml(req.id)}')">
                                View
                            </button>
                            ${isPending ? `
                                <button type="button" class="btn-table-action danger" onclick="window.OmniCareAudit.cancelRequest('${escapeHtml(req.id)}')">
                                    Cancel
                                </button>
                            ` : ''}
                            ${isInactive ? `
                                <button type="button" class="btn-table-action primary" onclick="window.OmniCareAudit.prefillRequestAgain('${escapeHtml(req.health_id || req.patient_id)}')">
                                    Request Again
                                </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    function renderRequestsPagination() {
        const infoEl = document.getElementById('requestsPageInfo');
        const prevBtn = document.getElementById('requestsPrevBtn');
        const nextBtn = document.getElementById('requestsNextBtn');

        if (infoEl) {
            infoEl.textContent = `Page ${state.requests.page} of ${state.requests.total_pages} (${state.requests.total} requests)`;
        }
        if (prevBtn) prevBtn.disabled = state.requests.page <= 1;
        if (nextBtn) nextBtn.disabled = state.requests.page >= state.requests.total_pages;
    }

    // ============================================================
    // TAB 3: AUDIT ACTIVITY LOG
    // ============================================================
    async function loadAuditLogs() {
        const tbody = document.getElementById('auditTableBody');
        const loadingEl = document.getElementById('auditLoading');
        const emptyEl = document.getElementById('auditEmpty');
        const errorEl = document.getElementById('auditError');
        const countBadge = document.getElementById('auditCountBadge');

        if (loadingEl) loadingEl.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
        if (tbody) tbody.innerHTML = '';

        try {
            const params = new URLSearchParams({
                page: state.audit.page,
                per_page: state.audit.per_page,
                action: state.audit.action,
                patient_id: state.audit.patient_id,
                start_date: state.audit.start_date,
                end_date: state.audit.end_date,
                q: state.audit.q
            });

            const res = await fetch(`/doctor/access-audit/api/logs?${params.toString()}`);
            if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
            const data = await res.json();

            if (loadingEl) loadingEl.style.display = 'none';

            if (!data.success) {
                if (errorEl) {
                    errorEl.style.display = 'block';
                    errorEl.textContent = data.error || 'Failed to load audit activity trail.';
                }
                return;
            }

            state.audit.total = data.total || 0;
            state.audit.total_pages = data.total_pages || 1;
            if (countBadge) countBadge.textContent = state.audit.total;

            renderAuditTable(data.logs || []);
            renderAuditPagination();

        } catch (err) {
            if (loadingEl) loadingEl.style.display = 'none';
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Unable to query audit activity log.';
            }
            console.error('Error fetching audit logs:', err);
        }
    }

    function renderAuditTable(logs) {
        const tbody = document.getElementById('auditTableBody');
        const emptyEl = document.getElementById('auditEmpty');
        if (!tbody) return;

        if (!logs || logs.length === 0) {
            if (emptyEl) emptyEl.style.display = 'block';
            return;
        }

        let html = '';
        logs.forEach(log => {
            const statusClass = (log.status || 'success').toLowerCase();
            const actionLabel = log.action_display || log.action || 'Unknown Event';
            const patientsList = log.patient_ids && log.patient_ids.length > 0
                ? log.patient_ids.map(p => escapeHtml(p.substring(0, 8))).join(', ')
                : '—';

            // Extract concise summary details from metadata
            let detailsText = '';
            if (log.metadata) {
                if (log.metadata.query) {
                    detailsText = `Query: "${escapeHtml(log.metadata.query)}"`;
                } else if (log.metadata.purpose) {
                    detailsText = `Purpose: ${escapeHtml(log.metadata.purpose)}`;
                } else if (log.metadata.view) {
                    detailsText = `View: ${escapeHtml(log.metadata.view)}`;
                } else if (log.metadata.reason) {
                    detailsText = `Reason: ${escapeHtml(log.metadata.reason)}`;
                } else if (log.metadata.abnormal_count !== undefined) {
                    detailsText = `Abnormal: ${log.metadata.abnormal_count}, Overdue: ${log.metadata.followup_count || 0}`;
                } else {
                    const keys = Object.keys(log.metadata);
                    detailsText = keys.length ? `${keys.length} metadata property(s)` : 'Standard activity event';
                }
            }

            html += `
                <tr>
                    <td class="col-audit-id">
                        <span class="patient-id-badge" title="${escapeHtml(log.id)}">
                            ${escapeHtml(log.id.substring(0, 8))}
                        </span>
                    </td>
                    <td class="col-audit-activity">
                        <div style="font-weight: 700; color: var(--text-navy); line-height: 1.3;">
                            ${escapeHtml(actionLabel)}
                        </div>
                    </td>
                    <td class="col-audit-patients">
                        <span class="patient-id-badge">${patientsList}</span>
                    </td>
                    <td class="col-audit-details">
                        <div class="audit-details-cell" title="${escapeHtml(detailsText)}">
                            ${detailsText}
                        </div>
                    </td>
                    <td class="col-audit-timestamp">
                        <div class="date-time-cell">
                            ${escapeHtml(formatDateTime(log.timestamp))}
                        </div>
                    </td>
                    <td class="col-audit-result">
                        <span class="status-pill ${statusClass}">
                            ● ${escapeHtml(log.status || 'SUCCESS')}
                        </span>
                    </td>
                    <td class="col-audit-actions" style="text-align: right;">
                        <button type="button" class="btn-table-action" onclick="window.OmniCareAudit.viewAuditDetail('${escapeHtml(log.id)}')">
                            Inspect
                        </button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    function renderAuditPagination() {
        const infoEl = document.getElementById('auditPageInfo');
        const prevBtn = document.getElementById('auditPrevBtn');
        const nextBtn = document.getElementById('auditNextBtn');

        if (infoEl) {
            infoEl.textContent = `Page ${state.audit.page} of ${state.audit.total_pages} (${state.audit.total} events)`;
        }
        if (prevBtn) prevBtn.disabled = state.audit.page <= 1;
        if (nextBtn) nextBtn.disabled = state.audit.page >= state.audit.total_pages;
    }

    // ============================================================
    // HEADER BELL: ACCESS NOTIFICATIONS DROPDOWN
    // ============================================================
    function updateBellBadge() {
        const countBadge = document.getElementById('notifCountBadge');
        const bellBadge = document.getElementById('headerBellBadge');

        if (countBadge) countBadge.textContent = state.notifications.length;
        if (bellBadge) {
            if (state.unreadNotificationsCount > 0) {
                bellBadge.textContent = state.unreadNotificationsCount;
                bellBadge.style.display = 'block';
            } else {
                bellBadge.textContent = '0';
                bellBadge.style.display = 'none';
            }
        }
    }

    function toggleNotificationDropdown() {
        const dropdown = document.getElementById('notifDropdown');
        if (!dropdown) return;
        if (dropdown.classList.contains('open')) {
            closeNotificationDropdown();
        } else {
            openNotificationDropdown();
        }
    }

    function openNotificationDropdown() {
        const dropdown = document.getElementById('notifDropdown');
        const bellBtn = document.getElementById('notifBellBtn');
        if (!dropdown) return;
        dropdown.classList.add('open');
        if (bellBtn) {
            bellBtn.classList.add('active');
            bellBtn.setAttribute('aria-expanded', 'true');
        }
        loadNotifications();
    }

    function closeNotificationDropdown() {
        const dropdown = document.getElementById('notifDropdown');
        const bellBtn = document.getElementById('notifBellBtn');
        if (!dropdown) return;
        dropdown.classList.remove('open');
        if (bellBtn) {
            bellBtn.classList.remove('active');
            bellBtn.setAttribute('aria-expanded', 'false');
        }
    }

    async function loadNotifications() {
        const listEl = document.getElementById('notificationsScrollArea');

        // Show loading state if currently empty
        if (listEl && state.notifications.length === 0) {
            listEl.innerHTML = `
                <div class="loading-state-wrapper" style="padding: 28px 10px;">
                    <div class="spinner"></div>
                    <p style="font-size: 12px; margin: 4px 0 0;">Loading notifications...</p>
                </div>
            `;
        }

        try {
            const res = await fetch('/doctor/access-audit/api/notifications?limit=25');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (data.success) {
                state.notifications = data.notifications || [];
                state.unreadNotificationsCount = data.unread_count || 0;
                updateBellBadge();
                renderNotificationsList();
            } else {
                throw new Error(data.error || 'Failed to load notifications');
            }
        } catch (err) {
            console.error('Error loading notifications:', err);
            if (listEl && state.notifications.length === 0) {
                listEl.innerHTML = `
                    <div class="empty-data-state" style="padding: 24px 10px; color: #dc2626;">
                        <div class="empty-state-icon" style="font-size: 24px;">⚠️</div>
                        <div class="empty-state-title" style="font-size: 13px; color: #dc2626;">Failed to Load Notifications</div>
                        <p class="empty-state-desc" style="font-size: 11px;">Could not retrieve notifications.</p>
                        <button type="button" class="btn-table-action" style="margin-top: 8px;" onclick="window.OmniCareAudit.loadNotifications()">Retry</button>
                    </div>
                `;
            }
        }
    }

    function renderNotificationsList() {
        const listEl = document.getElementById('notificationsScrollArea');
        if (!listEl) return;

        if (!state.notifications || state.notifications.length === 0) {
            listEl.innerHTML = `
                <div class="empty-data-state" style="padding: 36px 12px;">
                    <div class="empty-state-icon" style="font-size: 32px;">🔔</div>
                    <div class="empty-state-title" style="font-size: 14px;">All Caught Up</div>
                    <div class="empty-state-desc" style="font-size: 11px;">No access updates or expiring permissions right now.</div>
                </div>
            `;
            return;
        }

        let html = '';
        state.notifications.forEach(n => {
            const isUnread = !n.is_read;
            let icon = n.icon || '🔔';
            let iconBoxClass = 'icon-blue';
            let badgeClass = n.type || 'info';

            if (n.type === 'warning' || n.badge === 'Expiring Soon') {
                icon = '⚠️';
                iconBoxClass = 'icon-amber';
                badgeClass = 'warning';
            } else if (n.type === 'success' || n.badge === 'Access Granted') {
                icon = '🛡️';
                iconBoxClass = 'icon-green';
                badgeClass = 'success';
            } else if (n.badge === 'Unauthorized Access Attempt') {
                icon = '🚨';
                iconBoxClass = 'icon-red';
                badgeClass = 'danger';
            } else if (n.type === 'danger' || n.badge === 'Access Revoked' || n.badge === 'Access Request Rejected') {
                icon = (n.badge === 'Access Revoked') ? '🚫' : '❌';
                iconBoxClass = 'icon-red';
                badgeClass = 'danger';
            } else if (n.type === 'pending' || n.badge === 'Pending Approval' || n.badge === 'Access Request Pending') {
                icon = '⏱️';
                iconBoxClass = 'icon-amber';
                badgeClass = 'pending';
            } else if (n.type === 'expired' || n.badge === 'Access Expired') {
                icon = '⌛';
                iconBoxClass = 'icon-slate';
                badgeClass = 'expired';
            }

            const patientNamePill = n.patient_name
                ? `<span class="notif-patient-tag" title="Patient: ${escapeHtml(n.patient_name)}">👤 ${escapeHtml(n.patient_name)}</span>`
                : '';

            html += `
                <div class="notif-item ${isUnread ? 'unread' : ''}" 
                     role="button"
                     tabindex="0"
                     onclick="window.OmniCareAudit.onNotificationClick('${escapeHtml(n.id)}', '${escapeHtml(n.link || '')}', '${escapeHtml(n.request_id || '')}', '${escapeHtml(n.patient_id || '')}', '${escapeHtml(n.type || '')}')"
                     onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();this.click();}"
                     title="${escapeHtml(n.title)}">
                    <div class="notif-icon-box ${iconBoxClass}">
                        ${icon}
                    </div>
                    <div class="notif-content">
                        <div class="notif-item-top">
                            <span class="notif-badge-tag ${badgeClass}">
                                ${escapeHtml(n.badge)}
                            </span>
                            <span class="notif-time">${timeAgo(n.timestamp)}</span>
                        </div>
                        <div class="notif-item-title">${escapeHtml(n.title)}</div>
                        <div class="notif-item-message">${escapeHtml(n.message)}</div>
                        ${patientNamePill}
                    </div>
                    ${isUnread ? '<div class="notif-unread-dot" title="Unread notification"></div>' : ''}
                </div>
            `;
        });

        listEl.innerHTML = html;
    }

    // ============================================================
    // MODAL 1: REQUEST PATIENT ACCESS WORKFLOW
    // ============================================================
    function openRequestModal(prefillIdentifier) {
        const modal = document.getElementById('requestAccessModal');
        const input = document.getElementById('reqPatientSearchInput');
        const resultsBox = document.getElementById('modalSearchResults');
        const selectedPreview = document.getElementById('selectedPatientPreview');
        const purposeInput = document.getElementById('reqPurposeInput');
        const errorEl = document.getElementById('requestModalError');

        state.selectedPatientForRequest = null;
        if (input) input.value = prefillIdentifier || '';
        if (resultsBox) resultsBox.innerHTML = '';
        if (selectedPreview) selectedPreview.style.display = 'none';
        if (purposeInput) purposeInput.value = 'Clinical consultation and medical history review';
        if (errorEl) errorEl.style.display = 'none';

        if (prefillIdentifier) {
            searchPatientsInModal(prefillIdentifier);
        }

        if (modal) modal.classList.add('open');
    }

    function closeRequestModal() {
        const modal = document.getElementById('requestAccessModal');
        if (modal) modal.classList.remove('open');
    }

    async function searchPatientsInModal(query) {
        const resultsBox = document.getElementById('modalSearchResults');
        if (!resultsBox) return;

        const q = (query || '').trim();
        if (q.length < 2) {
            resultsBox.innerHTML = '';
            return;
        }

        resultsBox.innerHTML = '<div style="padding: 10px; font-size: 12px; color: var(--text-muted); text-align: center;">Searching patients...</div>';

        try {
            const res = await fetch(`/doctor/access-audit/api/search-patient?q=${encodeURIComponent(q)}`);
            const data = await res.json();

            if (!data.success || !data.patients || data.patients.length === 0) {
                resultsBox.innerHTML = `<div style="padding: 10px; font-size: 12px; color: var(--text-muted); text-align: center;">No patient found for "${escapeHtml(q)}". Check Health ID.</div>`;
                return;
            }

            let html = '<div class="patient-search-results-list">';
            data.patients.forEach(p => {
                html += `
                    <div class="patient-search-item" onclick="window.OmniCareAudit.selectPatient('${escapeHtml(p.id)}', '${escapeHtml(p.full_name)}', '${escapeHtml(p.health_id)}', '${escapeHtml(p.gender || '')}')">
                        <div>
                            <div style="font-weight: 700; color: var(--text-navy); font-size: 13px;">${escapeHtml(p.full_name)}</div>
                            <div style="font-size: 11px; color: var(--text-muted);">Health ID: ${escapeHtml(p.health_id)} | Gender: ${escapeHtml(p.gender || 'Not specified')}</div>
                        </div>
                        <button type="button" class="btn-table-action primary" style="font-size: 11px;">Select</button>
                    </div>
                `;
            });
            html += '</div>';

            resultsBox.innerHTML = html;

        } catch (err) {
            resultsBox.innerHTML = '<div style="padding: 10px; font-size: 12px; color: #dc2626; text-align: center;">Error looking up patients.</div>';
        }
    }

    function selectPatient(id, name, healthId, gender) {
        state.selectedPatientForRequest = { id, name, healthId, gender };
        const resultsBox = document.getElementById('modalSearchResults');
        const selectedPreview = document.getElementById('selectedPatientPreview');
        const prevName = document.getElementById('prevPatientName');
        const prevId = document.getElementById('prevPatientId');

        if (resultsBox) resultsBox.innerHTML = '';
        if (prevName) prevName.textContent = name;
        if (prevId) prevId.textContent = `Health ID: ${healthId}`;
        if (selectedPreview) selectedPreview.style.display = 'flex';
    }

    async function submitAccessRequest() {
        const errorEl = document.getElementById('requestModalError');
        const submitBtn = document.getElementById('submitRequestBtn');

        if (errorEl) errorEl.style.display = 'none';

        if (!state.selectedPatientForRequest) {
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Please search and select a patient first.';
            }
            return;
        }

        const accessTypeEl = document.getElementById('reqAccessTypeSelect');
        const durationEl = document.getElementById('reqDurationSelect');
        const purposeEl = document.getElementById('reqPurposeInput');

        const accessType = accessTypeEl ? accessTypeEl.value : 'temporary';
        const durationHours = durationEl ? parseInt(durationEl.value, 10) : 4;
        const purpose = purposeEl ? purposeEl.value.trim() : 'Clinical consultation';

        if (!purpose) {
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Please specify the clinical purpose of access.';
            }
            return;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';
        }

        try {
            const res = await fetch('/doctor/access-audit/api/requests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_id: state.selectedPatientForRequest.id,
                    access_type: accessType,
                    duration_hours: durationHours,
                    purpose: purpose
                })
            });

            const data = await res.json();
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Access Request';
            }

            if (!data.success) {
                if (errorEl) {
                    errorEl.style.display = 'block';
                    errorEl.textContent = data.error || 'Failed to submit request.';
                }
                return;
            }

            // Success: Close modal, refresh tabs
            closeRequestModal();
            loadSummary();
            loadRequests();
            loadNotifications();
            switchTab('requests');

            alert('✓ Access request submitted successfully. The patient has been notified to authorize consent.');

        } catch (err) {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Access Request';
            }
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Network error while submitting access request.';
            }
        }
    }

    // ============================================================
    // MODAL 2: CONSENT DETAILS
    // ============================================================
    async function viewConsent(requestId) {
        const modal = document.getElementById('consentDetailModal');
        const bodyEl = document.getElementById('consentModalBody');
        const footerBtn = document.getElementById('consentOpenWorkspaceBtn');

        if (!modal || !bodyEl) return;
        bodyEl.innerHTML = '<div class="loading-state-wrapper"><div class="spinner"></div><p>Verifying authorization record...</p></div>';
        modal.classList.add('open');

        try {
            const res = await fetch(`/doctor/access-audit/api/consent/${encodeURIComponent(requestId)}`);
            const data = await res.json();

            if (!data.success || !data.consent) {
                bodyEl.innerHTML = `<div class="empty-data-state"><div class="empty-state-title" style="color: #dc2626;">Error</div><p class="empty-state-desc">${escapeHtml(data.error || 'Consent record not found.')}</p></div>`;
                return;
            }

            const c = data.consent;
            const scopesList = (c.authorized_scopes || []).map(s => `<li>✓ ${escapeHtml(s.name)} (<strong>${escapeHtml(s.status)}</strong>)</li>`).join('');

            bodyEl.innerHTML = `
                <div style="margin-bottom: 16px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">PATIENT IDENTIFIER</div>
                    <div style="font-size: 16px; font-weight: 800; color: var(--text-navy);">${escapeHtml(c.patient_name)}</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Health ID: ${escapeHtml(c.health_id)} | Gender: ${escapeHtml(c.gender)}</div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; background: #f8fafc; padding: 12px; border-radius: 8px;">
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">ACCESS TYPE</div>
                        <div style="font-weight: 700; font-size: 13px; text-transform: capitalize;">${escapeHtml(c.access_type)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">STATUS</div>
                        <div style="font-weight: 700; font-size: 13px;">${escapeHtml(formatStatusLabel(c.status))}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">GRANTED AT</div>
                        <div style="font-size: 12px;">${escapeHtml(formatDateTime(c.approved_at) || '—')}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">EXPIRY DATE</div>
                        <div style="font-size: 12px;">${escapeHtml(c.expires_at ? formatDateTime(c.expires_at) : 'Permanent')}</div>
                    </div>
                </div>

                <div style="margin-bottom: 16px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">CLINICAL PURPOSE</div>
                    <div style="font-size: 13px; color: var(--text-slate); margin-top: 4px;">${escapeHtml(c.purpose)}</div>
                </div>

                <div style="margin-bottom: 16px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">AUTHORIZED DATA SCOPES</div>
                    <ul style="padding-left: 18px; margin: 6px 0; font-size: 12px; color: var(--text-slate); line-height: 1.6;">
                        ${scopesList}
                    </ul>
                </div>

                <div class="consent-notice-box">
                    <strong>Legal Notice:</strong> Under HIPAA & GDPR standards, access to medical records is granted exclusively for licensed clinical use. All queries, record views, and document extractions are logged permanently in the doctor's immutable audit trail.
                </div>
            `;

            if (footerBtn) {
                if (c.is_active && c.patient_id) {
                    footerBtn.style.display = 'inline-flex';
                    footerBtn.href = `/doctor/patient-workspace/${encodeURIComponent(c.patient_id)}`;
                } else {
                    footerBtn.style.display = 'none';
                }
            }

        } catch (err) {
            bodyEl.innerHTML = '<div class="empty-data-state"><p class="empty-state-desc" style="color: #dc2626;">Failed to load consent details.</p></div>';
        }
    }

    function closeConsentModal() {
        const modal = document.getElementById('consentDetailModal');
        if (modal) modal.classList.remove('open');
    }

    // ============================================================
    // MODAL 3: AUDIT ACTIVITY INSPECTION
    // ============================================================
    async function viewAuditDetail(logId) {
        const modal = document.getElementById('auditDetailModal');
        const bodyEl = document.getElementById('auditModalBody');

        if (!modal || !bodyEl) return;
        bodyEl.innerHTML = '<div class="loading-state-wrapper"><div class="spinner"></div><p>Fetching immutable audit details...</p></div>';
        modal.classList.add('open');

        try {
            const res = await fetch(`/doctor/access-audit/api/logs/${encodeURIComponent(logId)}`);
            const data = await res.json();

            if (!data.success || !data.log) {
                bodyEl.innerHTML = `<div class="empty-data-state"><p class="empty-state-desc" style="color: #dc2626;">Audit log not found.</p></div>`;
                return;
            }

            const l = data.log;
            const metaPretty = JSON.stringify(l.metadata || {}, null, 2);

            bodyEl.innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; background: #f8fafc; padding: 14px; border-radius: 8px;">
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">LOG ENTRY ID</div>
                        <div style="font-family: monospace; font-size: 11px; font-weight: 700;">${escapeHtml(l.id)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">STATUS RESULT</div>
                        <div style="font-weight: 800; color: ${l.status === 'SUCCESS' ? '#059669' : '#dc2626'}; font-size: 12px;">${escapeHtml(l.status)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">ACTIVITY TYPE</div>
                        <div style="font-weight: 700; font-size: 13px;">${escapeHtml(l.action_display || l.action)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">TIMESTAMP (UTC)</div>
                        <div style="font-size: 12px;">${escapeHtml(formatDateTime(l.timestamp))}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">CLIENT IP</div>
                        <div style="font-size: 12px;">${escapeHtml(l.client_ip || '127.0.0.1')}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-muted);">PATIENTS IN SCOPE</div>
                        <div style="font-size: 12px;">${escapeHtml(l.patient_count || 0)} patient(s)</div>
                    </div>
                </div>

                <div style="margin-bottom: 12px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">AUDIT METADATA & PARAMETERS</div>
                    <pre style="background: #0f172a; color: #38bdf8; padding: 12px; border-radius: 6px; font-size: 11px; overflow-x: auto; margin-top: 6px; max-height: 220px;">${escapeHtml(metaPretty)}</pre>
                </div>
            `;

        } catch (err) {
            bodyEl.innerHTML = '<div class="empty-data-state"><p class="empty-state-desc" style="color: #dc2626;">Error retrieving audit record.</p></div>';
        }
    }

    function closeAuditModal() {
        const modal = document.getElementById('auditDetailModal');
        if (modal) modal.classList.remove('open');
    }

    // ============================================================
    // CANCEL PENDING REQUEST
    // ============================================================
    async function cancelRequest(requestId) {
        if (!confirm('Are you sure you want to cancel this pending access request?')) {
            return;
        }

        try {
            const res = await fetch(`/doctor/access-audit/api/requests/${encodeURIComponent(requestId)}/cancel`, {
                method: 'POST'
            });
            const data = await res.json();

            if (!data.success) {
                alert(data.error || 'Unable to cancel access request.');
                return;
            }

            alert('✓ Access request cancelled.');
            loadSummary();
            loadRequests();
            loadNotifications();
        } catch (err) {
            alert('Failed to connect to server. Please try again.');
        }
    }

    // ============================================================
    // NOTIFICATION INTERACTIONS & ACTIONS
    // ============================================================
    async function onNotificationClick(notificationId, targetLink, requestId, patientId, type) {
        // Optimistically mark as read in local state
        const notif = state.notifications.find(n => n.id === notificationId);
        if (notif && !notif.is_read) {
            notif.is_read = true;
            state.unreadNotificationsCount = Math.max(0, state.unreadNotificationsCount - 1);
            updateBellBadge();
            renderNotificationsList();
        }

        // Call backend API to persist read state
        try {
            await fetch(`/doctor/access-audit/api/notifications/${encodeURIComponent(notificationId)}/read`, {
                method: 'POST'
            });
        } catch (e) {
            console.error('Error marking notification as read:', e);
        }

        // Close dropdown
        closeNotificationDropdown();

        // 1. Direct record workspace link if authorized
        if (targetLink && targetLink !== '#' && targetLink !== 'null' && targetLink !== '') {
            window.location.href = targetLink;
            return;
        }

        // 2. Security alert / unauthorized attempt -> Audit Tab
        if (type === 'danger' && !patientId) {
            switchTab('audit');
            return;
        }

        // 3. Pending request or rejected/cancelled request -> Requests Tab
        if (requestId || type === 'pending') {
            switchTab('requests');
            return;
        }

        // 4. Patient related -> Patients Tab
        if (patientId) {
            switchTab('patients');
        }
    }

    async function markAllNotificationsRead() {
        const unreadIds = state.notifications.filter(n => !n.is_read).map(n => n.id);
        if (unreadIds.length === 0) return;

        // Optimistically update local state immediately
        state.notifications.forEach(n => { n.is_read = true; });
        state.unreadNotificationsCount = 0;
        updateBellBadge();
        renderNotificationsList();

        try {
            await fetch('/doctor/access-audit/api/notifications/all/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notification_ids: unreadIds })
            });
        } catch (err) {
            console.error('Error marking all notifications read:', err);
            loadNotifications();
        }
    }

    // ============================================================
    // TAB NAVIGATION
    // ============================================================
    function switchTab(tabName) {
        state.activeTab = tabName;

        // Tab buttons
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Tab panels
        document.querySelectorAll('.tab-content-panel').forEach(panel => {
            if (panel.id === `${tabName}TabPanel`) {
                panel.classList.add('active');
            } else {
                panel.classList.remove('active');
            }
        });

        // Fetch tab data
        if (tabName === 'patients') {
            loadPatients();
        } else if (tabName === 'requests') {
            loadRequests();
        } else if (tabName === 'audit') {
            loadAuditLogs();
        }
    }

    // Filter audit directly for a specific patient
    function filterAuditForPatient(patientId) {
        state.audit.patient_id = patientId;
        state.audit.page = 1;
        const patientInput = document.getElementById('auditPatientFilter');
        if (patientInput) patientInput.value = patientId;
        switchTab('audit');
    }

    function prefillRequestAgain(identifier) {
        openRequestModal(identifier);
    }

    // ============================================================
    // DOM READY & EVENT BINDINGS
    // ============================================================
    document.addEventListener('DOMContentLoaded', () => {
        // Tab buttons
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                switchTab(btn.dataset.tab);
            });
        });

        // Open Request Access Modal
        const openReqBtn = document.getElementById('openRequestAccessBtn');
        if (openReqBtn) {
            openReqBtn.addEventListener('click', () => openRequestModal());
        }

        // Header bell button toggle
        const bellBtn = document.getElementById('notifBellBtn');
        if (bellBtn) {
            bellBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleNotificationDropdown();
            });
        }

        // Dropdown Close button
        const closeDropdownBtn = document.getElementById('closeNotifDropdownBtn');
        if (closeDropdownBtn) {
            closeDropdownBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                closeNotificationDropdown();
            });
        }

        // Dropdown Refresh button
        const refreshNotifBtn = document.getElementById('refreshNotifBtn');
        if (refreshNotifBtn) {
            refreshNotifBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                loadNotifications();
            });
        }

        // Stop clicks inside dropdown from bubbling and closing it
        const dropdownEl = document.getElementById('notifDropdown');
        if (dropdownEl) {
            dropdownEl.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }

        // Outside click closes notification dropdown
        document.addEventListener('click', (e) => {
            const bellContainer = document.getElementById('notifBellContainer');
            if (bellContainer && !bellContainer.contains(e.target)) {
                closeNotificationDropdown();
            }
        });

        // Escape key closes notification dropdown
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' || e.key === 'Esc') {
                const dropdown = document.getElementById('notifDropdown');
                if (dropdown && dropdown.classList.contains('open')) {
                    closeNotificationDropdown();
                    const bBtn = document.getElementById('notifBellBtn');
                    if (bBtn) bBtn.focus();
                }
            }
        });

        // Header search bar (searches active tab)
        const headerSearch = document.getElementById('headerSearchInput');
        if (headerSearch) {
            headerSearch.addEventListener('input', debounce((e) => {
                const q = e.target.value.trim();
                if (state.activeTab === 'patients') {
                    state.patients.q = q;
                    state.patients.page = 1;
                    loadPatients();
                } else if (state.activeTab === 'requests') {
                    state.requests.q = q;
                    state.requests.page = 1;
                    loadRequests();
                } else if (state.activeTab === 'audit') {
                    state.audit.q = q;
                    state.audit.page = 1;
                    loadAuditLogs();
                }
            }, 350));
        }

        // Patient Tab Filters
        const ptStatusSelect = document.getElementById('patientsStatusFilter');
        if (ptStatusSelect) {
            ptStatusSelect.addEventListener('change', (e) => {
                state.patients.status = e.target.value;
                state.patients.page = 1;
                loadPatients();
            });
        }

        const ptTypeSelect = document.getElementById('patientsTypeFilter');
        if (ptTypeSelect) {
            ptTypeSelect.addEventListener('change', (e) => {
                state.patients.type = e.target.value;
                state.patients.page = 1;
                loadPatients();
            });
        }

        const ptSearchInput = document.getElementById('patientsSearchInput');
        if (ptSearchInput) {
            ptSearchInput.addEventListener('input', debounce((e) => {
                state.patients.q = e.target.value.trim();
                state.patients.page = 1;
                loadPatients();
            }, 300));
        }

        const ptPrevBtn = document.getElementById('patientsPrevBtn');
        if (ptPrevBtn) {
            ptPrevBtn.addEventListener('click', () => {
                if (state.patients.page > 1) {
                    state.patients.page--;
                    loadPatients();
                }
            });
        }

        const ptNextBtn = document.getElementById('patientsNextBtn');
        if (ptNextBtn) {
            ptNextBtn.addEventListener('click', () => {
                if (state.patients.page < state.patients.total_pages) {
                    state.patients.page++;
                    loadPatients();
                }
            });
        }

        // Requests Tab Filters
        const reqStatusSelect = document.getElementById('requestsStatusFilter');
        if (reqStatusSelect) {
            reqStatusSelect.addEventListener('change', (e) => {
                state.requests.status = e.target.value;
                state.requests.page = 1;
                loadRequests();
            });
        }

        const reqSearchInput = document.getElementById('requestsSearchInput');
        if (reqSearchInput) {
            reqSearchInput.addEventListener('input', debounce((e) => {
                state.requests.q = e.target.value.trim();
                state.requests.page = 1;
                loadRequests();
            }, 300));
        }

        const reqPrevBtn = document.getElementById('requestsPrevBtn');
        if (reqPrevBtn) {
            reqPrevBtn.addEventListener('click', () => {
                if (state.requests.page > 1) {
                    state.requests.page--;
                    loadRequests();
                }
            });
        }

        const reqNextBtn = document.getElementById('requestsNextBtn');
        if (reqNextBtn) {
            reqNextBtn.addEventListener('click', () => {
                if (state.requests.page < state.requests.total_pages) {
                    state.requests.page++;
                    loadRequests();
                }
            });
        }

        // Audit Tab Filters
        const auditActionSelect = document.getElementById('auditActionFilter');
        if (auditActionSelect) {
            auditActionSelect.addEventListener('change', (e) => {
                state.audit.action = e.target.value;
                state.audit.page = 1;
                loadAuditLogs();
            });
        }

        const auditPatientFilter = document.getElementById('auditPatientFilter');
        if (auditPatientFilter) {
            auditPatientFilter.addEventListener('input', debounce((e) => {
                state.audit.patient_id = e.target.value.trim();
                state.audit.page = 1;
                loadAuditLogs();
            }, 350));
        }

        const auditStartDate = document.getElementById('auditStartDate');
        if (auditStartDate) {
            auditStartDate.addEventListener('change', (e) => {
                state.audit.start_date = e.target.value;
                state.audit.page = 1;
                loadAuditLogs();
            });
        }

        const auditEndDate = document.getElementById('auditEndDate');
        if (auditEndDate) {
            auditEndDate.addEventListener('change', (e) => {
                state.audit.end_date = e.target.value;
                state.audit.page = 1;
                loadAuditLogs();
            });
        }

        const auditResetBtn = document.getElementById('auditResetFiltersBtn');
        if (auditResetBtn) {
            auditResetBtn.addEventListener('click', () => {
                state.audit.action = '';
                state.audit.patient_id = '';
                state.audit.start_date = '';
                state.audit.end_date = '';
                state.audit.q = '';
                state.audit.page = 1;

                if (auditActionSelect) auditActionSelect.value = '';
                if (auditPatientFilter) auditPatientFilter.value = '';
                if (auditStartDate) auditStartDate.value = '';
                if (auditEndDate) auditEndDate.value = '';
                loadAuditLogs();
            });
        }

        const auditPrevBtn = document.getElementById('auditPrevBtn');
        if (auditPrevBtn) {
            auditPrevBtn.addEventListener('click', () => {
                if (state.audit.page > 1) {
                    state.audit.page--;
                    loadAuditLogs();
                }
            });
        }

        const auditNextBtn = document.getElementById('auditNextBtn');
        if (auditNextBtn) {
            auditNextBtn.addEventListener('click', () => {
                if (state.audit.page < state.audit.total_pages) {
                    state.audit.page++;
                    loadAuditLogs();
                }
            });
        }

        // Modal Patient Search
        const modalPatientSearch = document.getElementById('reqPatientSearchInput');
        if (modalPatientSearch) {
            modalPatientSearch.addEventListener('input', debounce((e) => {
                searchPatientsInModal(e.target.value);
            }, 300));
        }

        const submitReqBtn = document.getElementById('submitRequestBtn');
        if (submitReqBtn) {
            submitReqBtn.addEventListener('click', submitAccessRequest);
        }

        const markAllNotifBtn = document.getElementById('markAllNotifReadBtn');
        if (markAllNotifBtn) {
            markAllNotifBtn.addEventListener('click', markAllNotificationsRead);
        }

        // Initial Data Fetch
        loadSummary();
        loadPatients();
        loadNotifications();
    });

    // Expose public methods for inline onclicks
    window.OmniCareAudit = {
        viewConsent,
        closeConsentModal,
        viewAuditDetail,
        closeAuditModal,
        openRequestModal,
        closeRequestModal,
        selectPatient,
        cancelRequest,
        prefillRequestAgain,
        filterAuditForPatient,
        onNotificationClick,
        loadNotifications,
        markAllNotificationsRead,
        toggleNotificationDropdown,
        openNotificationDropdown,
        closeNotificationDropdown
    };
})();
