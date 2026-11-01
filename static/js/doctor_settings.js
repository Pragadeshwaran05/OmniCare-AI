/**
 * OMNICARE AI — DOCTOR SETTINGS CONTROLLER
 * Full client-side interactivity, asynchronous toggles,
 * theme management, compact sidebar, and data export.
 */

document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // ============================================================
    // TOAST NOTIFICATIONS
    // ============================================================
    const toastContainer = document.getElementById("settingsToastContainer");

    function showToast(message, type = "success") {
        if (!toastContainer) return;

        const toast = document.createElement("div");
        toast.className = `settings-toast ${type}`;

        const iconSvg = type === "success"
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>'
            : type === "error"
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'
            : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#087f79" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';

        toast.innerHTML = `
            ${iconSvg}
            <span>${message}</span>
        `;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(30px)";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // ============================================================
    // MODAL HELPERS
    // ============================================================
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add("open");
            document.body.style.overflow = "hidden";
        }
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove("open");
            document.body.style.overflow = "";
        }
    }

    document.querySelectorAll(".settings-modal-overlay").forEach((modal) => {
        modal.addEventListener("click", function (e) {
            if (e.target === this) {
                closeModal(this.id);
            }
        });
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            document.querySelectorAll(".settings-modal-overlay.open").forEach((m) => {
                closeModal(m.id);
            });
        }
    });

    document.querySelectorAll("[data-close-modal]").forEach((btn) => {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-close-modal");
            closeModal(targetId);
        });
    });


    // ============================================================
    // NOTIFICATION TOGGLES
    // ============================================================
    function setupNotificationToggle(elemId, prefKey) {
        const toggle = document.getElementById(elemId);
        if (!toggle) return;

        toggle.addEventListener("change", function () {
            const isChecked = this.checked;
            const payload = {};
            payload[prefKey] = isChecked;

            fetch("/doctor/settings/api/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast("Notification preference updated.");
                    } else {
                        // Rollback on failure
                        toggle.checked = !isChecked;
                        showToast(data.error || "Failed to update preference.", "error");
                    }
                })
                .catch((err) => {
                    toggle.checked = !isChecked;
                    console.error("Settings toggle error:", err);
                    showToast("Network error updating preference.", "error");
                });
        });
    }

    setupNotificationToggle("toggleAccessRequests", "notify_access_requests");
    setupNotificationToggle("toggleAccessExpiry", "notify_access_expiry");
    setupNotificationToggle("toggleSystemUpdates", "notify_system_updates");


    // ============================================================
    // APPEARANCE: THEME SELECTION
    // ============================================================
    const themeButtons = document.querySelectorAll("[data-theme-choice]");

    function applyTheme(choice) {
        const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        let effectiveTheme = choice;
        if (choice === "system") {
            effectiveTheme = prefersDark ? "dark" : "light";
        }

        if (effectiveTheme === "dark") {
            document.documentElement.setAttribute("data-theme", "dark");
            document.documentElement.classList.add("theme-dark");
        } else {
            document.documentElement.setAttribute("data-theme", "light");
            document.documentElement.classList.remove("theme-dark");
        }

        try {
            localStorage.setItem("omnicare_theme", choice);
        } catch (e) {}

        themeButtons.forEach((btn) => {
            if (btn.getAttribute("data-theme-choice") === choice) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });
    }

    // Set initial active state from localStorage or attribute
    const currentTheme = localStorage.getItem("omnicare_theme") || "light";
    applyTheme(currentTheme);

    themeButtons.forEach((btn) => {
        btn.addEventListener("click", function () {
            const choice = this.getAttribute("data-theme-choice");
            applyTheme(choice);

            fetch("/doctor/settings/api/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ theme: choice }),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast(`Theme updated to ${choice.charAt(0).toUpperCase() + choice.slice(1)}.`);
                    }
                })
                .catch((err) => console.error("Theme save error:", err));
        });
    });


    // ============================================================
    // APPEARANCE: SIDEBAR VIEW SELECTION
    // ============================================================
    const sidebarButtons = document.querySelectorAll("[data-sidebar-choice]");

    function applySidebarMode(choice) {
        if (choice === "compact" && window.innerWidth > 700) {
            document.documentElement.classList.add("sidebar-compact");
        } else {
            document.documentElement.classList.remove("sidebar-compact");
        }

        try {
            localStorage.setItem("omnicare_sidebar", choice);
        } catch (e) {}

        sidebarButtons.forEach((btn) => {
            if (btn.getAttribute("data-sidebar-choice") === choice) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });
    }

    const currentSidebar = localStorage.getItem("omnicare_sidebar") || "expanded";
    applySidebarMode(currentSidebar);

    sidebarButtons.forEach((btn) => {
        btn.addEventListener("click", function () {
            const choice = this.getAttribute("data-sidebar-choice");
            applySidebarMode(choice);

            fetch("/doctor/settings/api/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sidebar_mode: choice }),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast(`Sidebar mode updated to ${choice.charAt(0).toUpperCase() + choice.slice(1)}.`);
                    }
                })
                .catch((err) => console.error("Sidebar mode save error:", err));
        });
    });


    // ============================================================
    // ACCOUNT SETTINGS MODALS (PROFILE, PROFESSIONAL, PREFS)
    // ============================================================
    const rowEditProfile = document.getElementById("rowEditProfile");
    const rowEditProfessional = document.getElementById("rowEditProfessional");
    const rowEditWorkingPrefs = document.getElementById("rowEditWorkingPrefs");

    if (rowEditProfile) {
        rowEditProfile.addEventListener("click", () => openModal("modalEditProfileSettings"));
    }

    if (rowEditProfessional) {
        rowEditProfessional.addEventListener("click", () => openModal("modalEditProfessionalSettings"));
    }

    if (rowEditWorkingPrefs) {
        rowEditWorkingPrefs.addEventListener("click", () => openModal("modalEditWorkingPrefsSettings"));
    }

    // Form Edit Profile
    const formEditProfile = document.getElementById("formEditProfileSettings");
    if (formEditProfile) {
        formEditProfile.addEventListener("submit", function (e) {
            e.preventDefault();

            const fullName = document.getElementById("settingsFullName").value.trim();
            const phone = document.getElementById("settingsPhone").value.trim();
            const hospitalName = document.getElementById("settingsHospitalName").value.trim();
            const hospitalAddress = document.getElementById("settingsHospitalAddress").value.trim();

            if (!fullName) {
                showToast("Full Name is required.", "error");
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";

            fetch("/doctor/profile/api/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    full_name: fullName,
                    phone: phone,
                    hospital_name: hospitalName,
                    hospital_address: hospitalAddress,
                }),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Changes";

                    if (data.success) {
                        showToast("Profile details updated successfully.");
                        closeModal("modalEditProfileSettings");
                        // Update header name if present
                        const hdrName = document.getElementById("headerDoctorName");
                        if (hdrName) hdrName.textContent = `Dr. ${data.profile.full_name}`;
                    } else {
                        showToast(data.error || "Failed to update profile.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Changes";
                    console.error("Edit profile error:", err);
                    showToast("Network error updating profile.", "error");
                });
        });
    }

    // Form Edit Professional Details
    const formEditProfessional = document.getElementById("formEditProfessionalSettings");
    if (formEditProfessional) {
        formEditProfessional.addEventListener("submit", function (e) {
            e.preventDefault();

            const qualification = document.getElementById("settingsQualification").value.trim();
            const specialization = document.getElementById("settingsSpecialization").value.trim();
            const department = document.getElementById("settingsDepartment").value.trim();
            const experienceYears = parseInt(document.getElementById("settingsExperience").value, 10) || 0;

            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";

            fetch("/doctor/profile/api/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    qualification: qualification,
                    specialization: specialization,
                    department: department,
                    experience_years: experienceYears,
                }),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Changes";

                    if (data.success) {
                        showToast("Professional details updated successfully.");
                        closeModal("modalEditProfessionalSettings");
                    } else {
                        showToast(data.error || "Failed to update professional details.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Changes";
                    console.error("Edit professional error:", err);
                    showToast("Network error updating details.", "error");
                });
        });
    }

    // Form Edit Working Preferences
    const formEditWorkingPrefs = document.getElementById("formEditWorkingPrefsSettings");
    if (formEditWorkingPrefs) {
        formEditWorkingPrefs.addEventListener("submit", function (e) {
            e.preventDefault();

            const selectedDays = [];
            formEditWorkingPrefs.querySelectorAll('input[name="consultation_days"]:checked').forEach((chk) => {
                selectedDays.push(chk.value);
            });

            if (selectedDays.length === 0) {
                showToast("Please select at least one consultation day.", "error");
                return;
            }

            const startTime = document.getElementById("settingsStartTime").value.trim();
            const endTime = document.getElementById("settingsEndTime").value.trim();
            const mode = document.getElementById("settingsConsultationMode").value;

            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";

            fetch("/doctor/profile/api/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    consultation_days: selectedDays,
                    consultation_start_time: startTime,
                    consultation_end_time: endTime,
                    consultation_mode: mode,
                }),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Preferences";

                    if (data.success) {
                        showToast("Working preferences saved successfully.");
                        closeModal("modalEditWorkingPrefsSettings");
                    } else {
                        showToast(data.error || "Failed to save preferences.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Preferences";
                    console.error("Save preferences error:", err);
                    showToast("Network error saving preferences.", "error");
                });
        });
    }


    // ============================================================
    // SECURITY: CHANGE PASSWORD
    // ============================================================
    const btnOpenChangePassword = document.getElementById("btnOpenChangePassword");
    const formChangePassword = document.getElementById("formChangePasswordSettings");
    const inputNewPass = document.getElementById("settingsNewPassword");
    const inputConfirmPass = document.getElementById("settingsConfirmPassword");
    const ruleLength = document.getElementById("settingsRuleLength");
    const ruleAlpha = document.getElementById("settingsRuleAlphanumeric");

    if (btnOpenChangePassword) {
        btnOpenChangePassword.addEventListener("click", () => {
            openModal("modalChangePasswordSettings");
        });
    }

    // Toggle password visibility
    document.querySelectorAll(".password-toggle-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
            const targetInputId = this.getAttribute("data-target-input");
            const input = document.getElementById(targetInputId);
            if (!input) return;

            if (input.type === "password") {
                input.type = "text";
                this.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>';
            } else {
                input.type = "password";
                this.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
            }
        });
    });

    if (inputNewPass) {
        inputNewPass.addEventListener("input", function () {
            const val = this.value;
            if (val.length >= 8) {
                if (ruleLength) ruleLength.style.color = "#059669";
            } else {
                if (ruleLength) ruleLength.style.color = "";
            }

            if (/[A-Za-z]/.test(val) && /[0-9]/.test(val)) {
                if (ruleAlpha) ruleAlpha.style.color = "#059669";
            } else {
                if (ruleAlpha) ruleAlpha.style.color = "";
            }
        });
    }

    if (formChangePassword) {
        formChangePassword.addEventListener("submit", function (e) {
            e.preventDefault();

            const curPass = document.getElementById("settingsCurrentPassword").value;
            const newPass = inputNewPass.value;
            const confPass = inputConfirmPass.value;

            if (!curPass) {
                showToast("Please enter your current password.", "error");
                return;
            }

            if (newPass.length < 8) {
                showToast("New password must be at least 8 characters long.", "error");
                return;
            }

            if (!/[A-Za-z]/.test(newPass) || !/[0-9]/.test(newPass)) {
                showToast("New password must contain letters and numbers.", "error");
                return;
            }

            if (newPass !== confPass) {
                showToast("New password and confirmation do not match.", "error");
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = "Updating...";

            fetch("/doctor/settings/api/change-password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    current_password: curPass,
                    new_password: newPass,
                    confirm_password: confPass,
                }),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Password";

                    if (data.success) {
                        showToast(data.message || "Password changed successfully.");
                        closeModal("modalChangePasswordSettings");
                        formChangePassword.reset();
                    } else {
                        showToast(data.error || "Failed to update password.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Password";
                    console.error("Change password error:", err);
                    showToast("Network error updating password.", "error");
                });
        });
    }


    // ============================================================
    // SECURITY: 2FA & ACTIVE SESSIONS
    // ============================================================
    const btnOpen2FA = document.getElementById("btnOpen2FA");
    if (btnOpen2FA) {
        btnOpen2FA.addEventListener("click", () => openModal("modalTwoFactorSettings"));
    }

    const btnOpenSessions = document.getElementById("btnOpenSessions");
    if (btnOpenSessions) {
        btnOpenSessions.addEventListener("click", () => openModal("modalActiveSessionsSettings"));
    }

    const btnTerminateSession = document.getElementById("btnTerminateSession");
    if (btnTerminateSession) {
        btnTerminateSession.addEventListener("click", function () {
            if (!confirm("Are you sure you want to sign out of this workstation?")) {
                return;
            }
            window.location.href = "/doctor/logout";
        });
    }


    // ============================================================
    // DATA & PRIVACY: EXPORT DATA & DELETE ACCOUNT
    // ============================================================
    const btnDownloadData = document.getElementById("btnDownloadData");
    if (btnDownloadData) {
        btnDownloadData.addEventListener("click", function () {
            showToast("Generating clinical profile and audit export...", "info");
            window.location.href = "/doctor/settings/api/export";
        });
    }

    const btnOpenDeleteAccount = document.getElementById("btnOpenDeleteAccount");
    const formDeleteAccount = document.getElementById("formDeleteAccount");

    if (btnOpenDeleteAccount) {
        btnOpenDeleteAccount.addEventListener("click", () => openModal("modalDeleteAccountSettings"));
    }

    if (formDeleteAccount) {
        formDeleteAccount.addEventListener("submit", function (e) {
            e.preventDefault();

            const password = document.getElementById("inputDeletePassword").value;
            const confirmText = document.getElementById("inputDeleteConfirmText").value.trim();

            if (!password) {
                showToast("Please enter your current password.", "error");
                return;
            }

            if (confirmText !== "DELETE MY ACCOUNT") {
                showToast('Please type "DELETE MY ACCOUNT" exactly to confirm.', "error");
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = "Deactivating Account...";

            fetch("/doctor/settings/api/delete-account", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password_confirm: password }),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast("Account deactivated. Logging out...", "success");
                        setTimeout(() => {
                            window.location.href = "/doctor/login";
                        }, 1800);
                    } else {
                        submitBtn.disabled = false;
                        submitBtn.textContent = "Deactivate My Account";
                        showToast(data.error || "Failed to deactivate account.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Deactivate My Account";
                    console.error("Account delete error:", err);
                    showToast("Network error deactivating account.", "error");
                });
        });
    }


    // ============================================================
    // CONNECTED SERVICES STATUS REFRESH
    // ============================================================
    function refreshServicesStatus() {
        fetch("/doctor/settings/api/services/status")
            .then((res) => res.json())
            .then((data) => {
                if (data.success && data.services) {
                    const sbPill = document.getElementById("statusPillSupabase");
                    const sbText = document.getElementById("statusTextSupabase");
                    if (sbPill && sbText) {
                        const sbStatus = data.services.supabase.status;
                        sbText.textContent = sbStatus;
                        sbPill.className = `status-pill ${sbStatus.toLowerCase().replace(" ", "-")}`;
                    }

                    const gmPill = document.getElementById("statusPillGemini");
                    const gmText = document.getElementById("statusTextGemini");
                    if (gmPill && gmText) {
                        const gmStatus = data.services.gemini.status;
                        gmText.textContent = gmStatus;
                        gmPill.className = `status-pill ${gmStatus.toLowerCase().replace(" ", "-")}`;
                    }
                }
            })
            .catch((err) => console.error("Services check error:", err));
    }

    refreshServicesStatus();
});
