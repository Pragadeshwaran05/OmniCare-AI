/**
 * OMNICARE AI — DOCTOR PROFILE JAVASCRIPT CONTROLLER
 * Full client-side interactivity, asynchronous uploads,
 * live preview, and modal management.
 */

document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // ============================================================
    // TOAST NOTIFICATION SYSTEM
    // ============================================================
    const toastContainer = document.getElementById("profileToastContainer");

    function showToast(message, type = "success") {
        if (!toastContainer) return;

        const toast = document.createElement("div");
        toast.className = `profile-toast ${type}`;

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
    // MODAL OPEN / CLOSE LOGIC
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

    // Global click outside to dismiss modals
    document.querySelectorAll(".profile-modal-overlay").forEach((modal) => {
        modal.addEventListener("click", function (e) {
            if (e.target === this) {
                closeModal(this.id);
            }
        });
    });

    // Global ESC key to dismiss modals
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            document.querySelectorAll(".profile-modal-overlay.open").forEach((m) => {
                closeModal(m.id);
            });
        }
    });

    // Close buttons
    document.querySelectorAll("[data-close-modal]").forEach((btn) => {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-close-modal");
            closeModal(targetId);
        });
    });


    // ============================================================
    // PROFILE PHOTO UPLOAD & REMOVAL
    // ============================================================
    const photoInput = document.getElementById("profilePhotoInput");
    const btnChangePhoto = document.getElementById("btnChangePhoto");
    const btnRemovePhoto = document.getElementById("btnRemovePhoto");
    const avatarContainer = document.getElementById("avatarContainer");

    if (btnChangePhoto && photoInput) {
        btnChangePhoto.addEventListener("click", () => photoInput.click());
    }

    if (photoInput) {
        photoInput.addEventListener("change", function () {
            const file = this.files[0];
            if (!file) return;

            // Validate format
            const validTypes = ["image/jpeg", "image/png", "image/webp"];
            if (!validTypes.includes(file.type)) {
                showToast("Please select a JPG, PNG, or WEBP image.", "error");
                this.value = "";
                return;
            }

            // Validate size (5MB)
            if (file.size > 5 * 1024 * 1024) {
                showToast("Image size cannot exceed 5 MB.", "error");
                this.value = "";
                return;
            }

            // Client-side preview
            const reader = new FileReader();
            reader.onload = function (e) {
                let img = avatarContainer.querySelector("img");
                const defaultAvatar = avatarContainer.querySelector(".doctor-default-avatar");
                if (defaultAvatar) {
                    defaultAvatar.style.display = "none";
                }
                if (!img) {
                    img = document.createElement("img");
                    img.className = "doctor-photo-img";
                    img.alt = "Doctor Profile Photo";
                    avatarContainer.insertBefore(img, avatarContainer.firstChild);
                }
                img.src = e.target.result;
                img.style.display = "block";
            };
            reader.readAsDataURL(file);

            // Upload via API
            const formData = new FormData();
            formData.append("photo", file);

            fetch("/doctor/profile/api/photo", {
                method: "POST",
                body: formData,
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast(data.message || "Profile photograph updated successfully.");
                        if (btnRemovePhoto) {
                            btnRemovePhoto.style.display = "inline-block";
                        }
                    } else {
                        showToast(data.error || "Failed to upload photo.", "error");
                    }
                })
                .catch((err) => {
                    console.error("Photo upload error:", err);
                    showToast("Network error uploading photo.", "error");
                });
        });
    }

    if (btnRemovePhoto) {
        btnRemovePhoto.addEventListener("click", function () {
            if (!confirm("Are you sure you want to remove your custom profile photograph?")) {
                return;
            }

            fetch("/doctor/profile/api/photo", {
                method: "DELETE",
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showToast(data.message || "Profile photograph removed.");
                        // Restore default avatar
                        const img = avatarContainer.querySelector("img");
                        if (img) img.style.display = "none";

                        let def = avatarContainer.querySelector(".doctor-default-avatar");
                        if (def) {
                            def.style.display = "flex";
                        }
                        btnRemovePhoto.style.display = "none";
                    } else {
                        showToast(data.error || "Failed to remove photo.", "error");
                    }
                })
                .catch((err) => {
                    console.error("Photo delete error:", err);
                    showToast("Network error removing photo.", "error");
                });
        });
    }


    // ============================================================
    // EDIT PROFILE MODAL (PERSONAL & HOSPITAL DETAILS)
    // ============================================================
    const btnOpenEditProfile = document.getElementById("btnOpenEditProfileModal");
    const formEditProfile = document.getElementById("formEditProfile");

    if (btnOpenEditProfile) {
        btnOpenEditProfile.addEventListener("click", () => {
            openModal("editProfileModal");
        });
    }

    if (formEditProfile) {
        formEditProfile.addEventListener("submit", function (e) {
            e.preventDefault();

            const fullName = document.getElementById("inputFullName").value.trim();
            const phone = document.getElementById("inputPhone").value.trim();
            const hospitalName = document.getElementById("inputHospitalName").value.trim();
            const hospitalAddress = document.getElementById("inputHospitalAddress").value.trim();

            if (!fullName) {
                showToast("Full Name is required.", "error");
                return;
            }

            const payload = {
                full_name: fullName,
                phone: phone,
                hospital_name: hospitalName,
                hospital_address: hospitalAddress,
            };

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";

            fetch("/doctor/profile/api/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;

                    if (data.success) {
                        showToast("Profile details updated successfully.");
                        closeModal("editProfileModal");

                        // Update DOM elements
                        const p = data.profile;
                        if (document.getElementById("dispDoctorName")) {
                            document.getElementById("dispDoctorName").textContent = `Dr. ${p.full_name}`;
                        }
                        if (document.getElementById("dispFullNameDetail")) {
                            document.getElementById("dispFullNameDetail").textContent = `Dr. ${p.full_name}`;
                        }
                        if (document.getElementById("dispPhone")) {
                            document.getElementById("dispPhone").textContent = p.phone || "Not provided";
                        }
                        if (document.getElementById("dispHospital")) {
                            document.getElementById("dispHospital").textContent = p.hospital_name || "OmniCare Partner Hospital";
                        }
                        if (document.getElementById("dispHospitalDetail")) {
                            document.getElementById("dispHospitalDetail").textContent = p.hospital_name || "OmniCare Partner Hospital";
                        }
                        if (document.getElementById("dispAddress")) {
                            document.getElementById("dispAddress").textContent = p.hospital_address || "Medical Center";
                        }
                        if (document.getElementById("dispAddressDetail")) {
                            document.getElementById("dispAddressDetail").textContent = p.hospital_address || "Medical Center";
                        }
                    } else {
                        showToast(data.error || "Failed to update profile.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    console.error("Update profile error:", err);
                    showToast("Network error updating profile.", "error");
                });
        });
    }


    // ============================================================
    // EDIT PROFESSIONAL INFORMATION MODAL
    // ============================================================
    const btnOpenProfessional = document.getElementById("btnOpenProfessionalModal");
    const formEditProfessional = document.getElementById("formEditProfessional");

    if (btnOpenProfessional) {
        btnOpenProfessional.addEventListener("click", () => {
            openModal("editProfessionalModal");
        });
    }

    if (formEditProfessional) {
        formEditProfessional.addEventListener("submit", function (e) {
            e.preventDefault();

            const qualification = document.getElementById("inputQualification").value.trim();
            const specialization = document.getElementById("inputSpecialization").value.trim();
            const department = document.getElementById("inputDepartment").value.trim();
            const experienceYears = parseInt(document.getElementById("inputExperience").value, 10) || 0;
            const hospitalAddress = document.getElementById("inputProfAddress").value.trim();

            const payload = {
                qualification: qualification,
                specialization: specialization,
                department: department,
                experience_years: experienceYears,
                hospital_address: hospitalAddress,
            };

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";

            fetch("/doctor/profile/api/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;

                    if (data.success) {
                        showToast("Professional information updated successfully.");
                        closeModal("editProfessionalModal");

                        const p = data.profile;
                        if (document.getElementById("dispSpecializationBadge")) {
                            document.getElementById("dispSpecializationBadge").textContent = p.specialization;
                        }
                        if (document.getElementById("dispQualification")) {
                            document.getElementById("dispQualification").textContent = p.qualification;
                        }
                        if (document.getElementById("dispSpecializationDetail")) {
                            document.getElementById("dispSpecializationDetail").textContent = p.specialization;
                        }
                        if (document.getElementById("dispDepartment")) {
                            document.getElementById("dispDepartment").textContent = p.department;
                        }
                        if (document.getElementById("dispExperience")) {
                            document.getElementById("dispExperience").textContent = `${p.experience_years} Years`;
                        }
                        if (document.getElementById("dispAddressDetail")) {
                            document.getElementById("dispAddressDetail").textContent = p.hospital_address;
                        }
                        if (document.getElementById("dispAddress")) {
                            document.getElementById("dispAddress").textContent = p.hospital_address;
                        }
                    } else {
                        showToast(data.error || "Failed to update professional details.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    console.error("Update professional error:", err);
                    showToast("Network error updating professional details.", "error");
                });
        });
    }


    // ============================================================
    // EDIT BIOGRAPHY (ABOUT ME) MODAL
    // ============================================================
    const btnOpenBio = document.getElementById("btnOpenBioModal");
    const formEditBio = document.getElementById("formEditBio");
    const inputBio = document.getElementById("inputBioText");
    const bioCharCounter = document.getElementById("bioCharCounter");

    if (btnOpenBio) {
        btnOpenBio.addEventListener("click", () => {
            if (inputBio && bioCharCounter) {
                bioCharCounter.textContent = `${inputBio.value.length} / 1000`;
            }
            openModal("editBioModal");
        });
    }

    if (inputBio && bioCharCounter) {
        inputBio.addEventListener("input", function () {
            bioCharCounter.textContent = `${this.value.length} / 1000`;
        });
    }

    if (formEditBio) {
        formEditBio.addEventListener("submit", function (e) {
            e.preventDefault();

            const bioText = inputBio.value.trim();
            if (bioText.length > 1000) {
                showToast("Biography cannot exceed 1000 characters.", "error");
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";

            fetch("/doctor/profile/api/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ professional_bio: bioText }),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;

                    if (data.success) {
                        showToast("Biography updated successfully.");
                        closeModal("editBioModal");

                        if (document.getElementById("dispBio")) {
                            document.getElementById("dispBio").textContent = data.profile.professional_bio;
                        }
                    } else {
                        showToast(data.error || "Failed to update biography.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    console.error("Bio update error:", err);
                    showToast("Network error updating biography.", "error");
                });
        });
    }


    // ============================================================
    // EDIT WORKING PREFERENCES MODAL
    // ============================================================
    const btnOpenPrefs = document.getElementById("btnOpenPrefsModal");
    const formEditPrefs = document.getElementById("formEditPreferences");

    if (btnOpenPrefs) {
        btnOpenPrefs.addEventListener("click", () => {
            openModal("editPrefsModal");
        });
    }

    if (formEditPrefs) {
        formEditPrefs.addEventListener("submit", function (e) {
            e.preventDefault();

            const selectedDays = [];
            formEditPrefs.querySelectorAll('input[name="consultation_days"]:checked').forEach((chk) => {
                selectedDays.push(chk.value);
            });

            if (selectedDays.length === 0) {
                showToast("Please select at least one consultation day.", "error");
                return;
            }

            const startTime = document.getElementById("inputStartTime").value.trim();
            const endTime = document.getElementById("inputEndTime").value.trim();
            const mode = document.getElementById("inputConsultationMode").value;

            const payload = {
                consultation_days: selectedDays,
                consultation_start_time: startTime,
                consultation_end_time: endTime,
                consultation_mode: mode,
            };

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";

            fetch("/doctor/profile/api/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;

                    if (data.success) {
                        showToast("Working preferences saved successfully.");
                        closeModal("editPrefsModal");

                        // Update active day pills
                        const daysWrap = document.getElementById("dispDaysWrap");
                        if (daysWrap) {
                            daysWrap.querySelectorAll(".day-badge").forEach((badge) => {
                                const dayName = badge.getAttribute("data-day");
                                if (selectedDays.includes(dayName)) {
                                    badge.classList.add("active");
                                } else {
                                    badge.classList.remove("active");
                                }
                            });
                        }

                        // Update hours
                        if (document.getElementById("dispHours")) {
                            document.getElementById("dispHours").textContent = `${startTime} – ${endTime}`;
                        }

                        // Update mode
                        if (document.getElementById("dispModeBadge")) {
                            const modeLabels = {
                                in_person: "In-Person Clinic",
                                teleconsultation: "Teleconsultation Only",
                                both: "In-Person & Teleconsultation",
                            };
                            document.getElementById("dispModeBadge").textContent = modeLabels[mode] || mode;
                        }
                    } else {
                        showToast(data.error || "Failed to save preferences.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    console.error("Preferences error:", err);
                    showToast("Network error saving working preferences.", "error");
                });
        });
    }


    // ============================================================
    // PROFESSIONAL DOCUMENTS UPLOAD & MANAGEMENT
    // ============================================================
    const btnOpenUploadDoc = document.getElementById("btnOpenUploadDocModal");
    const formUploadDoc = document.getElementById("formUploadDocument");
    const docDropzone = document.getElementById("docDropzone");
    const docFileInput = document.getElementById("docFileInput");
    const docFilePreview = document.getElementById("docFilePreview");
    const docFileNameDisp = document.getElementById("docFileNameDisp");
    const docFileSizeDisp = document.getElementById("docFileSizeDisp");
    const btnClearDocFile = document.getElementById("btnClearDocFile");
    const docsTableBody = document.getElementById("docsTableBody");
    const emptyDocsState = document.getElementById("emptyDocsState");

    if (btnOpenUploadDoc) {
        btnOpenUploadDoc.addEventListener("click", () => {
            openModal("uploadDocModal");
        });
    }

    if (docDropzone && docFileInput) {
        docDropzone.addEventListener("click", () => docFileInput.click());

        docDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            docDropzone.classList.add("dragover");
        });

        docDropzone.addEventListener("dragleave", () => {
            docDropzone.classList.remove("dragover");
        });

        docDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            docDropzone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                docFileInput.files = e.dataTransfer.files;
                handleDocFileSelect(e.dataTransfer.files[0]);
            }
        });

        docFileInput.addEventListener("change", function () {
            if (this.files && this.files[0]) {
                handleDocFileSelect(this.files[0]);
            }
        });
    }

    function handleDocFileSelect(file) {
        const allowedExts = ["pdf", "jpg", "jpeg", "png", "webp"];
        const ext = file.name.split(".").pop().toLowerCase();
        if (!allowedExts.includes(ext)) {
            showToast("Supported formats: PDF, JPG, PNG, WEBP.", "error");
            docFileInput.value = "";
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            showToast("Document size cannot exceed 10 MB.", "error");
            docFileInput.value = "";
            return;
        }

        if (docFilePreview && docFileNameDisp && docFileSizeDisp) {
            docFileNameDisp.textContent = file.name;
            const sizeStr = file.size < 1024 * 1024
                ? `${(file.size / 1024).toFixed(1)} KB`
                : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
            docFileSizeDisp.textContent = sizeStr;
            docFilePreview.style.display = "flex";
        }
    }

    if (btnClearDocFile) {
        btnClearDocFile.addEventListener("click", (e) => {
            e.stopPropagation();
            if (docFileInput) docFileInput.value = "";
            if (docFilePreview) docFilePreview.style.display = "none";
        });
    }

    if (formUploadDoc) {
        formUploadDoc.addEventListener("submit", function (e) {
            e.preventDefault();

            const file = docFileInput ? docFileInput.files[0] : null;
            if (!file) {
                showToast("Please choose a file to upload.", "error");
                return;
            }

            const docName = document.getElementById("inputDocName").value.trim();
            const docType = document.getElementById("inputDocType").value;

            const formData = new FormData();
            formData.append("document_file", file);
            formData.append("document_name", docName);
            formData.append("document_type", docType);

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "Uploading & Verifying...";

            fetch("/doctor/profile/api/documents/upload", {
                method: "POST",
                body: formData,
            })
                .then((res) => res.json())
                .then((data) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;

                    if (data.success) {
                        showToast(data.message || "Document uploaded successfully.");
                        closeModal("uploadDocModal");
                        formUploadDoc.reset();
                        if (docFilePreview) docFilePreview.style.display = "none";

                        // Append to table
                        appendDocumentRow(data.document);
                    } else {
                        showToast(data.error || "Failed to upload document.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    console.error("Document upload error:", err);
                    showToast("Network error uploading document.", "error");
                });
        });
    }

    function appendDocumentRow(doc) {
        if (emptyDocsState) {
            emptyDocsState.style.display = "none";
        }
        if (docsTableBody) {
            const tableWrap = docsTableBody.closest(".table-responsive");
            if (tableWrap) tableWrap.style.display = "block";

            const row = document.createElement("tr");
            row.id = `doc-row-${doc.id}`;

            const isPdf = (doc.mime_type || "").includes("pdf") || (doc.file_name || "").endsWith(".pdf");
            const iconClass = isPdf ? "pdf" : "image";
            const iconSvg = isPdf
                ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>'
                : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>';

            row.innerHTML = `
                <td>
                    <div class="doc-name-cell">
                        <div class="doc-icon-pill ${iconClass}">
                            ${iconSvg}
                        </div>
                        <div>
                            <strong>${doc.document_name}</strong>
                            <div style="font-size: 11px; color: var(--text-muted);">${doc.file_name}</div>
                        </div>
                    </div>
                </td>
                <td>${doc.document_type_label || "Document"}</td>
                <td>Just now</td>
                <td>${doc.file_size_formatted || "—"}</td>
                <td>
                    <span class="status-badge verified">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        Verified
                    </span>
                </td>
                <td>
                    <div class="action-buttons-group">
                        <a href="/doctor/profile/api/documents/${doc.id}/view" target="_blank" class="btn-icon-action" title="View Document">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        </a>
                        <a href="/doctor/profile/api/documents/${doc.id}/download" class="btn-icon-action" title="Download Document">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        </a>
                        <button type="button" class="btn-icon-action danger btn-delete-doc" data-doc-id="${doc.id}" data-doc-name="${doc.document_name}" title="Delete Document">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                    </div>
                </td>
            `;

            docsTableBody.insertBefore(row, docsTableBody.firstChild);
            attachDeleteHandler(row.querySelector(".btn-delete-doc"));
        }
    }

    // Delete Document Handlers
    let targetDocIdToDelete = null;

    function attachDeleteHandler(btn) {
        if (!btn) return;
        btn.addEventListener("click", function () {
            targetDocIdToDelete = this.getAttribute("data-doc-id");
            const docName = this.getAttribute("data-doc-name") || "this document";
            const nameEl = document.getElementById("deleteDocNameDisp");
            if (nameEl) nameEl.textContent = docName;
            openModal("deleteDocModal");
        });
    }

    document.querySelectorAll(".btn-delete-doc").forEach(attachDeleteHandler);

    const btnConfirmDeleteDoc = document.getElementById("btnConfirmDeleteDoc");
    if (btnConfirmDeleteDoc) {
        btnConfirmDeleteDoc.addEventListener("click", function () {
            if (!targetDocIdToDelete) return;

            const btn = this;
            btn.disabled = true;
            btn.textContent = "Deleting...";

            fetch(`/doctor/profile/api/documents/${targetDocIdToDelete}`, {
                method: "DELETE",
            })
                .then((res) => res.json())
                .then((data) => {
                    btn.disabled = false;
                    btn.textContent = "Delete Document";

                    if (data.success) {
                        showToast("Document deleted successfully.");
                        closeModal("deleteDocModal");

                        const row = document.getElementById(`doc-row-${targetDocIdToDelete}`);
                        if (row) row.remove();

                        // Check if table empty
                        if (docsTableBody && docsTableBody.children.length === 0) {
                            const tableWrap = docsTableBody.closest(".table-responsive");
                            if (tableWrap) tableWrap.style.display = "none";
                            if (emptyDocsState) emptyDocsState.style.display = "block";
                        }
                    } else {
                        showToast(data.error || "Failed to delete document.", "error");
                    }
                    targetDocIdToDelete = null;
                })
                .catch((err) => {
                    btn.disabled = false;
                    btn.textContent = "Delete Document";
                    console.error("Delete doc error:", err);
                    showToast("Network error deleting document.", "error");
                });
        });
    }


    // ============================================================
    // ACCOUNT & SECURITY: CHANGE PASSWORD
    // ============================================================
    const formChangePassword = document.getElementById("formChangePassword");
    const inputNewPass = document.getElementById("inputNewPassword");
    const inputConfirmPass = document.getElementById("inputConfirmPassword");
    const checkLength = document.getElementById("ruleLength");
    const checkAlphanumeric = document.getElementById("ruleAlphanumeric");

    if (inputNewPass) {
        inputNewPass.addEventListener("input", function () {
            const val = this.value;
            // Check length >= 8
            if (val.length >= 8) {
                if (checkLength) checkLength.classList.add("valid");
            } else {
                if (checkLength) checkLength.classList.remove("valid");
            }

            // Check letters and numbers
            const hasLetter = /[A-Za-z]/.test(val);
            const hasNumber = /[0-9]/.test(val);
            if (hasLetter && hasNumber) {
                if (checkAlphanumeric) checkAlphanumeric.classList.add("valid");
            } else {
                if (checkAlphanumeric) checkAlphanumeric.classList.remove("valid");
            }
        });
    }

    if (formChangePassword) {
        formChangePassword.addEventListener("submit", function (e) {
            e.preventDefault();

            const curPass = document.getElementById("inputCurrentPassword").value;
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
                showToast("New password must contain both letters and numbers.", "error");
                return;
            }

            if (newPass !== confPass) {
                showToast("New password and confirmation do not match.", "error");
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "Updating...";

            fetch("/doctor/profile/api/change-password", {
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
                    submitBtn.textContent = originalText;

                    if (data.success) {
                        showToast(data.message || "Password changed successfully.");
                        formChangePassword.reset();
                        if (checkLength) checkLength.classList.remove("valid");
                        if (checkAlphanumeric) checkAlphanumeric.classList.remove("valid");
                    } else {
                        showToast(data.error || "Failed to update password.", "error");
                    }
                })
                .catch((err) => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    console.error("Change password error:", err);
                    showToast("Network error changing password.", "error");
                });
        });
    }
});
