/**
 * OMNICARE AI — DOCTOR CONSULTATIONS & PRESCRIPTIONS CONTROLLER
 * Page-specific JavaScript for /doctor/consultations-prescriptions
 */

(function () {
    "use strict";

    // Application state
    let authorizedPatients = window.AUTHORIZED_PATIENTS || [];
    let currentPatient = window.SELECTED_PATIENT || null;
    let medicineRowCount = 0;
    let previewDebounceTimer = null;

    function lockModalScroll() {
        document.body.classList.add("modal-open-lock");
        document.documentElement.classList.add("modal-open-lock");
    }

    function unlockModalScroll() {
        const anyActive = document.querySelectorAll(".consultations-modal-overlay.active");
        if (anyActive.length === 0) {
            document.body.classList.remove("modal-open-lock");
            document.documentElement.classList.remove("modal-open-lock");
        }
    }

    function initModalDismissal() {
        // Close active modal on Escape key
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                const activeModals = document.querySelectorAll(".consultations-modal-overlay.active");
                if (activeModals.length > 0) {
                    activeModals.forEach(m => m.classList.remove("active"));
                    const pdfIframe = document.getElementById("pdfViewerIframe");
                    if (pdfIframe) pdfIframe.src = "about:blank";
                    unlockModalScroll();
                }
            }
        });

        // Close on backdrop click outside the modal card
        document.querySelectorAll(".consultations-modal-overlay").forEach(overlay => {
            overlay.addEventListener("click", function (e) {
                if (e.target === overlay) {
                    overlay.classList.remove("active");
                    if (overlay.id === "pdfViewerModal") {
                        const pdfIframe = document.getElementById("pdfViewerIframe");
                        if (pdfIframe) pdfIframe.src = "about:blank";
                    }
                    unlockModalScroll();
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initPatientSearch();
        initTableFilters();
        initTimingChips();
        initDropzones();
        initModalDismissal();
    });

    /* ==========================================================================
       1. PATIENT SEARCH & AUTOCOMPLETE
       ========================================================================== */
    function initPatientSearch() {
        const input = document.getElementById("patientSearchInput");
        const dropdown = document.getElementById("patientAutocompleteDropdown");

        if (!input || !dropdown) return;

        input.addEventListener("input", function () {
            const query = (this.value || "").trim().toLowerCase();
            if (!query) {
                dropdown.style.display = "none";
                return;
            }

            const matches = authorizedPatients.filter(p => {
                const name = (p.name || p.full_name || "").toLowerCase();
                const hid = (p.health_id || "").toLowerCase();
                const id = (p.id || p.patient_id || "").toLowerCase();
                return name.includes(query) || hid.includes(query) || id.includes(query);
            });

            if (matches.length === 0) {
                dropdown.innerHTML = `
                    <div style="padding: 14px; text-align: center; color: #64748b; font-size: 13px;">
                        No authorized patients found matching "<strong>${escapeHtml(query)}</strong>"
                    </div>
                `;
                dropdown.style.display = "block";
                return;
            }

            let html = "";
            matches.forEach(p => {
                const name = p.name || p.full_name || "Patient";
                const hid = p.health_id || "N/A";
                const age = p.age ? `${p.age} yrs` : "";
                const gender = p.gender || "";
                const meta = [age, gender, p.blood_group].filter(Boolean).join(" • ");
                const permBadge = p.is_permanent ? "Permanent Access" : (p.access_type || "Authorized");

                html += `
                    <div class="autocomplete-item" data-patient-id="${p.id || p.patient_id}">
                        <div class="autocomplete-patient-details">
                            <h5>${escapeHtml(name)}</h5>
                            <span>${escapeHtml(hid)} ${meta ? `• ${escapeHtml(meta)}` : ""}</span>
                        </div>
                        <span class="autocomplete-access-badge">✓ ${escapeHtml(permBadge)}</span>
                    </div>
                `;
            });

            dropdown.innerHTML = html;
            dropdown.style.display = "block";

            // Bind click handlers to autocomplete items
            dropdown.querySelectorAll(".autocomplete-item").forEach(item => {
                item.addEventListener("click", function () {
                    const pid = this.getAttribute("data-patient-id");
                    selectPatient(pid);
                });
            });
        });

        // Hide dropdown on click outside
        document.addEventListener("click", function (e) {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });
    }

    function selectPatient(patientId) {
        if (!patientId) return;
        // Navigate with selected patient query param
        window.location.href = `/doctor/consultations-prescriptions?patient_id=${encodeURIComponent(patientId)}`;
    }

    /* ==========================================================================
       2. DOCUMENT HISTORY TABLE SEARCH & FILTERS
       ========================================================================== */
    function initTableFilters() {
        const filterBtns = document.querySelectorAll(".cat-filter-btn");
        const statCards = document.querySelectorAll(".summary-stat-card");
        const searchInput = document.getElementById("tableSearchInput");
        const rows = document.querySelectorAll(".clinical-documents-table tbody tr.doc-row");
        const emptyState = document.getElementById("tableEmptyFilterState");

        function applyFilter(category) {
            let visibleCount = 0;
            const searchVal = (searchInput ? searchInput.value : "").trim().toLowerCase();

            rows.forEach(row => {
                const rowCat = (row.getAttribute("data-category") || "").toLowerCase();
                const text = row.textContent.toLowerCase();

                const catMatch = (category === "all") || (rowCat === category) ||
                    (category === "lab" && (rowCat === "lab_report" || rowCat === "lab")) ||
                    (category === "imaging" && (rowCat === "scan_imaging" || rowCat === "imaging"));
                const searchMatch = !searchVal || text.includes(searchVal);

                if (catMatch && searchMatch) {
                    row.style.display = "";
                    visibleCount++;
                } else {
                    row.style.display = "none";
                }
            });

            if (emptyState) {
                emptyState.style.display = (visibleCount === 0 && rows.length > 0) ? "block" : "none";
            }

            // Sync pill buttons active state
            filterBtns.forEach(btn => {
                if (btn.getAttribute("data-category") === category) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });

            // Sync stat cards active state
            statCards.forEach(card => {
                if (card.getAttribute("data-category") === category) {
                    card.classList.add("active-filter");
                } else {
                    card.classList.remove("active-filter");
                }
            });
        }

        filterBtns.forEach(btn => {
            btn.addEventListener("click", function () {
                const cat = this.getAttribute("data-category") || "all";
                applyFilter(cat);
            });
        });

        statCards.forEach(card => {
            card.addEventListener("click", function () {
                const cat = this.getAttribute("data-category") || "all";
                applyFilter(cat);
            });
        });

        if (searchInput) {
            searchInput.addEventListener("input", function () {
                const activeBtn = document.querySelector(".cat-filter-btn.active");
                const currentCat = activeBtn ? activeBtn.getAttribute("data-category") : "all";
                applyFilter(currentCat);
            });
        }
    }

    /* ==========================================================================
       3. CONSULTATION TEMPLATE MODAL
       ========================================================================== */
    window.openConsultationModal = function () {
        if (!ensurePatientSelected()) return;
        const modal = document.getElementById("consultationModal");
        if (modal) {
            modal.classList.add("active");
            lockModalScroll();
        }
    };

    window.closeConsultationModal = function () {
        const modal = document.getElementById("consultationModal");
        if (modal) {
            modal.classList.remove("active");
            unlockModalScroll();
        }
    };

    window.saveConsultationForm = async function (isDraft = false) {
        if (!currentPatient) return;
        const form = document.getElementById("consultationForm");
        if (!form) return;

        const submitBtn = document.getElementById("btnSaveConsultation");
        const origText = submitBtn ? submitBtn.innerHTML : "";
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span>⏳ Saving...</span>`;
        }

        const formData = new FormData(form);
        const payload = {
            consultation_type: formData.get("consultation_type") || "General Consultation",
            document_date: formData.get("consultation_date") || new Date().toISOString().split("T")[0],
            consultation_time: formData.get("consultation_time") || "",
            chief_complaint: formData.get("chief_complaint") || "",
            hpi: formData.get("hpi") || "",
            medical_history: formData.get("medical_history") || "",
            findings: formData.get("findings") || "",
            diagnosis_primary: formData.get("diagnosis_primary") || "",
            diagnosis_secondary: formData.get("diagnosis_secondary") || "",
            investigations_recommended: formData.get("investigations_recommended") || "",
            treatment_plan: formData.get("treatment_plan") || "",
            recommendations: formData.get("recommendations") || "",
            follow_up: formData.get("follow_up") || "",
            clinical_notes: formData.get("clinical_notes") || "",
            is_draft: isDraft,
            vitals: {
                bp: formData.get("vital_bp") || "",
                pulse: formData.get("vital_pulse") || "",
                temperature: formData.get("vital_temp") || "",
                respiratory_rate: formData.get("vital_rr") || "",
                oxygen_saturation: formData.get("vital_spo2") || "",
                weight: formData.get("vital_weight") || "",
                height: formData.get("vital_height") || "",
                bmi: formData.get("vital_bmi") || ""
            }
        };

        try {
            const res = await fetch(`/doctor/consultations/${currentPatient.id}/create-consultation`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (data.success) {
                closeConsultationModal();
                form.reset();
                showToast(isDraft ? "Consultation note saved as draft!" : "Consultation note created successfully!", "success");
                addRecordToTableDOM(data.record);
                updateRecentConsultationsDOM(data.record);
                incrementCategoryCount("consultation");
            } else {
                alert(data.error || "Failed to create consultation.");
            }
        } catch (err) {
            console.error("Save consultation error:", err);
            alert("Network error occurred while saving consultation.");
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origText;
            }
        }
    };

    /* ==========================================================================
       4. PRESCRIPTION TEMPLATE MODAL & TWO-PANEL PREVIEW
       ========================================================================== */
    window.openPrescriptionModal = function () {
        if (!ensurePatientSelected()) return;
        const modal = document.getElementById("prescriptionModal");
        if (modal) {
            modal.classList.add("active");
            lockModalScroll();

            // Add first empty medicine row if empty
            const container = document.getElementById("medicineRowsContainer");
            if (container && container.children.length === 0) {
                addMedicineRow();
            }

            // Trigger initial preview
            updatePrescriptionLivePreview();
        }
    };

    window.closePrescriptionModal = function () {
        const modal = document.getElementById("prescriptionModal");
        if (modal) {
            modal.classList.remove("active");
            unlockModalScroll();
        }
    };

    window.addMedicineRow = function (prefill = null) {
        medicineRowCount++;
        const container = document.getElementById("medicineRowsContainer");
        if (!container) return;

        const row = document.createElement("div");
        row.className = "medicine-item-card";
        row.setAttribute("data-row-id", medicineRowCount);

        const medName = prefill ? (prefill.name || "") : "";
        const medType = prefill ? (prefill.type || "Tablet") : "Tablet";
        const medStrength = prefill ? (prefill.strength || "") : "";
        const medDosage = prefill ? (prefill.dosage || "1 Tablet") : "1 Tablet";
        const medFreq = prefill ? (prefill.frequency || "Once Daily") : "Once Daily";
        const medDur = prefill ? (prefill.duration || "5 Days") : "5 Days";
        const medFood = prefill ? (prefill.food || "After Food") : "After Food";
        const medInstr = prefill ? (prefill.instructions || "") : "";

        row.innerHTML = `
            <div class="medicine-item-top">
                <span class="med-num-badge">${medicineRowCount}</span>
                <input type="text" class="form-input med-name-input" placeholder="Medicine / Brand / Generic Name (e.g. Paracetamol)" value="${escapeHtml(medName)}" oninput="schedulePrescriptionPreview()">
                <button type="button" class="btn-remove-med" title="Remove Medicine" onclick="removeMedicineRow(this)">🗑️</button>
            </div>
            <div class="form-grid-3" style="margin-bottom: 8px;">
                <div class="form-field">
                    <label>Type</label>
                    <select class="form-select med-type-select" onchange="schedulePrescriptionPreview()">
                        <option value="Tablet" ${medType === 'Tablet' ? 'selected' : ''}>Tablet</option>
                        <option value="Capsule" ${medType === 'Capsule' ? 'selected' : ''}>Capsule</option>
                        <option value="Syrup" ${medType === 'Syrup' ? 'selected' : ''}>Syrup</option>
                        <option value="Injection" ${medType === 'Injection' ? 'selected' : ''}>Injection</option>
                        <option value="Syringe" ${medType === 'Syringe' ? 'selected' : ''}>Syringe</option>
                        <option value="Sachet" ${medType === 'Sachet' ? 'selected' : ''}>Sachet</option>
                        <option value="Drops" ${medType === 'Drops' ? 'selected' : ''}>Drops</option>
                        <option value="Ointment" ${medType === 'Ointment' ? 'selected' : ''}>Ointment</option>
                        <option value="Cream" ${medType === 'Cream' ? 'selected' : ''}>Cream</option>
                        <option value="Inhaler" ${medType === 'Inhaler' ? 'selected' : ''}>Inhaler</option>
                        <option value="Other" ${medType === 'Other' ? 'selected' : ''}>Other</option>
                    </select>
                </div>
                <div class="form-field">
                    <label>Strength</label>
                    <input type="text" class="form-input med-strength-input" placeholder="e.g. 500 mg, 10 ml" value="${escapeHtml(medStrength)}" oninput="schedulePrescriptionPreview()">
                </div>
                <div class="form-field">
                    <label>Dosage</label>
                    <input type="text" class="form-input med-dosage-input" placeholder="e.g. 1 Tablet, 5 ml" value="${escapeHtml(medDosage)}" oninput="schedulePrescriptionPreview()">
                </div>
            </div>
            <div class="form-grid-3" style="margin-bottom: 8px;">
                <div class="form-field">
                    <label>Frequency</label>
                    <select class="form-select med-freq-select" onchange="schedulePrescriptionPreview()">
                        <option value="Once Daily" ${medFreq === 'Once Daily' ? 'selected' : ''}>Once Daily</option>
                        <option value="Twice Daily" ${medFreq === 'Twice Daily' ? 'selected' : ''}>Twice Daily</option>
                        <option value="Three Times Daily" ${medFreq === 'Three Times Daily' ? 'selected' : ''}>Three Times Daily</option>
                        <option value="Four Times Daily" ${medFreq === 'Four Times Daily' ? 'selected' : ''}>Four Times Daily</option>
                        <option value="As Required (SOS)" ${medFreq === 'As Required (SOS)' ? 'selected' : ''}>As Required (SOS)</option>
                        <option value="Other" ${medFreq === 'Other' ? 'selected' : ''}>Other</option>
                    </select>
                </div>
                <div class="form-field">
                    <label>Duration</label>
                    <input type="text" class="form-input med-duration-input" placeholder="e.g. 3 Days, 5 Days" value="${escapeHtml(medDur)}" oninput="schedulePrescriptionPreview()">
                </div>
                <div class="form-field">
                    <label>Food Instructions</label>
                    <select class="form-select med-food-select" onchange="schedulePrescriptionPreview()">
                        <option value="After Food" ${medFood === 'After Food' ? 'selected' : ''}>After Food</option>
                        <option value="Before Food" ${medFood === 'Before Food' ? 'selected' : ''}>Before Food</option>
                        <option value="With Food" ${medFood === 'With Food' ? 'selected' : ''}>With Food</option>
                        <option value="Empty Stomach" ${medFood === 'Empty Stomach' ? 'selected' : ''}>Empty Stomach</option>
                        <option value="Not Applicable" ${medFood === 'Not Applicable' ? 'selected' : ''}>Not Applicable</option>
                    </select>
                </div>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
                <div class="timing-horizontal-group">
                    <span class="timing-label-text">Timing:</span>
                    <label class="timing-chip" onclick="toggleTimingChip(this)">
                        <input type="checkbox" name="med_timing_m" value="1"> M (Morning)
                    </label>
                    <label class="timing-chip" onclick="toggleTimingChip(this)">
                        <input type="checkbox" name="med_timing_a" value="1"> A (Afternoon)
                    </label>
                    <label class="timing-chip" onclick="toggleTimingChip(this)">
                        <input type="checkbox" name="med_timing_e" value="1"> E (Evening)
                    </label>
                    <label class="timing-chip" onclick="toggleTimingChip(this)">
                        <input type="checkbox" name="med_timing_n" value="1"> N (Night)
                    </label>
                </div>
                <div style="flex: 1 1 200px;">
                    <input type="text" class="form-input med-instr-input" placeholder="Specific notes / warnings..." value="${escapeHtml(medInstr)}" oninput="schedulePrescriptionPreview()">
                </div>
            </div>
        `;

        container.appendChild(row);
        schedulePrescriptionPreview();
    };

    window.removeMedicineRow = function (btn) {
        const row = btn.closest(".medicine-item-card");
        if (row) {
            row.remove();
            renumberMedicineRows();
            schedulePrescriptionPreview();
        }
    };

    function renumberMedicineRows() {
        const rows = document.querySelectorAll("#medicineRowsContainer .medicine-item-card");
        rows.forEach((r, idx) => {
            const badge = r.querySelector(".med-num-badge");
            if (badge) badge.textContent = idx + 1;
        });
        medicineRowCount = rows.length;
    }

    window.toggleTimingChip = function (chip) {
        setTimeout(() => {
            const cb = chip.querySelector("input[type='checkbox']");
            if (cb && cb.checked) {
                chip.classList.add("active");
            } else {
                chip.classList.remove("active");
            }
            schedulePrescriptionPreview();
        }, 10);
    };

    function initTimingChips() {
        document.querySelectorAll(".timing-chip input[type='checkbox']").forEach(cb => {
            if (cb.checked) {
                cb.closest(".timing-chip").classList.add("active");
            }
        });
    }

    window.schedulePrescriptionPreview = function () {
        clearTimeout(previewDebounceTimer);
        previewDebounceTimer = setTimeout(updatePrescriptionLivePreview, 600);
    };

    async function updatePrescriptionLivePreview() {
        if (!currentPatient) return;
        const iframe = document.getElementById("prescriptionLiveIframe");
        if (!iframe) return;

        const payload = buildPrescriptionPayload(false);
        payload.template_type = "prescription";

        try {
            const res = await fetch(`/doctor/consultations/${currentPatient.id}/preview-pdf`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const blob = await res.blob();
                const blobUrl = URL.createObjectURL(blob);
                iframe.src = blobUrl;
            }
        } catch (e) {
            console.warn("Live prescription preview error:", e);
        }
    }

    function buildPrescriptionPayload(isDraft) {
        const form = document.getElementById("prescriptionForm");
        const formData = form ? new FormData(form) : new FormData();

        const medicines = [];
        const rows = document.querySelectorAll("#medicineRowsContainer .medicine-item-card");

        rows.forEach(r => {
            const name = (r.querySelector(".med-name-input")?.value || "").trim();
            if (!name) return;

            const mType = r.querySelector(".med-type-select")?.value || "Tablet";
            const strength = r.querySelector(".med-strength-input")?.value || "";
            const dosage = r.querySelector(".med-dosage-input")?.value || "1 Tablet";
            const freq = r.querySelector(".med-freq-select")?.value || "Once Daily";
            const dur = r.querySelector(".med-duration-input")?.value || "5 Days";
            const food = r.querySelector(".med-food-select")?.value || "After Food";
            const instr = r.querySelector(".med-instr-input")?.value || "";

            const timingM = r.querySelector("input[name='med_timing_m']")?.checked || false;
            const timingA = r.querySelector("input[name='med_timing_a']")?.checked || false;
            const timingE = r.querySelector("input[name='med_timing_e']")?.checked || false;
            const timingN = r.querySelector("input[name='med_timing_n']")?.checked || false;

            medicines.push({
                name: name,
                type: mType,
                strength: strength,
                dosage: dosage,
                frequency: freq,
                duration: dur,
                food: food,
                instructions: instr,
                timing: { m: timingM, a: timingA, e: timingE, n: timingN }
            });
        });

        return {
            diagnosis: formData.get("rx_diagnosis") || "",
            clinical_notes: formData.get("rx_clinical_notes") || "",
            general_advice: formData.get("rx_general_advice") || "",
            follow_up: formData.get("rx_follow_up") || "",
            document_date: formData.get("rx_date") || new Date().toISOString().split("T")[0],
            prescription_time: formData.get("rx_time") || "",
            review_after_tests: formData.get("rx_review_after_tests") ? true : false,
            medicines: medicines,
            is_draft: isDraft
        };
    }

    window.savePrescriptionForm = async function (isDraft = false) {
        if (!currentPatient) return;
        const submitBtn = document.getElementById("btnSavePrescription");
        const origText = submitBtn ? submitBtn.innerHTML : "";
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span>⏳ Saving...</span>`;
        }

        const payload = buildPrescriptionPayload(isDraft);

        try {
            const res = await fetch(`/doctor/consultations/${currentPatient.id}/create-prescription`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (data.success) {
                closePrescriptionModal();
                showToast(isDraft ? "Prescription saved as draft!" : "Prescription generated successfully!", "success");
                addRecordToTableDOM(data.record);
                updateRecentPrescriptionsDOM(data.record);
                incrementCategoryCount("prescription");
            } else {
                alert(data.error || "Failed to create prescription.");
            }
        } catch (err) {
            console.error("Save prescription error:", err);
            alert("Network error occurred while saving prescription.");
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origText;
            }
        }
    };

    /* ==========================================================================
       5. UPLOAD DOCUMENT MODAL (CONSULTATION, PRESCRIPTION, OTHER)
       ========================================================================== */
    window.openUploadDocumentModal = function (preselectedType = "other") {
        if (!ensurePatientSelected()) return;
        const modal = document.getElementById("uploadDocumentModal");
        if (modal) {
            const typeSelect = document.getElementById("uploadDocCategory");
            if (typeSelect && preselectedType) {
                typeSelect.value = preselectedType;
            }
            modal.classList.add("active");
            lockModalScroll();
        }
    };

    window.closeUploadDocumentModal = function () {
        const modal = document.getElementById("uploadDocumentModal");
        if (modal) {
            modal.classList.remove("active");
            unlockModalScroll();
        }
    };

    function initDropzones() {
        const dropzone = document.getElementById("docUploadDropzone");
        const fileInput = document.getElementById("docUploadFileInput");
        const pill = document.getElementById("selectedFilePill");

        if (!dropzone || !fileInput) return;

        dropzone.addEventListener("click", () => fileInput.click());

        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("drag-over");
        });

        dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));

        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("drag-over");
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateSelectedFileDisplay();
            }
        });

        fileInput.addEventListener("change", updateSelectedFileDisplay);

        function updateSelectedFileDisplay() {
            if (fileInput.files && fileInput.files[0] && pill) {
                const f = fileInput.files[0];
                pill.textContent = `📎 ${f.name} (${(f.size / (1024 * 1024)).toFixed(2)} MB)`;
                pill.style.display = "inline-flex";
            }
        }
    }

    window.submitUploadDocumentForm = async function () {
        if (!currentPatient) return;
        const form = document.getElementById("uploadDocumentForm");
        const fileInput = document.getElementById("docUploadFileInput");

        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            alert("Please select a medical document to upload.");
            return;
        }

        const file = fileInput.files[0];
        if (file.size > 25 * 1024 * 1024) {
            alert("File size exceeds 25 MB limit.");
            return;
        }

        const submitBtn = document.getElementById("btnSubmitDocUpload");
        const origText = submitBtn ? submitBtn.innerHTML : "";
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span>⏳ Uploading...</span>`;
        }

        const formData = new FormData(form);

        try {
            const res = await fetch(`/doctor/consultations/${currentPatient.id}/upload-document`, {
                method: "POST",
                body: formData
            });

            const data = await res.json();
            if (data.success) {
                closeUploadDocumentModal();
                form.reset();
                const pill = document.getElementById("selectedFilePill");
                if (pill) pill.style.display = "none";
                showToast("Medical document uploaded successfully!", "success");
                addRecordToTableDOM(data.record);
                incrementCategoryCount(data.record.record_type);
            } else {
                alert(data.error || "Failed to upload document.");
            }
        } catch (err) {
            console.error("Document upload error:", err);
            alert("Network error occurred during document upload.");
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origText;
            }
        }
    };

    /* ==========================================================================
       6. VIEW PDF PREVIEW MODAL
       ========================================================================== */
    window.viewDocumentPdf = function (fileUrl, title = "Medical Document") {
        const modal = document.getElementById("pdfViewerModal");
        const iframe = document.getElementById("pdfViewerIframe");
        const titleEl = document.getElementById("pdfViewerTitle");
        const downloadBtn = document.getElementById("pdfViewerDownloadBtn");

        if (!modal || !iframe) return;

        titleEl.textContent = title;
        iframe.src = fileUrl;
        if (downloadBtn) {
            downloadBtn.href = fileUrl;
            downloadBtn.setAttribute("download", `${title.replace(/[^a-zA-Z0-9_-]/g, "_")}.pdf`);
        }

        modal.classList.add("active");
        lockModalScroll();
    };

    window.closePdfViewerModal = function () {
        const modal = document.getElementById("pdfViewerModal");
        const iframe = document.getElementById("pdfViewerIframe");
        if (modal) {
            modal.classList.remove("active");
            unlockModalScroll();
            if (iframe) iframe.src = "about:blank";
        }
    };

    /* ==========================================================================
       7. DYNAMIC DOM HELPERS & TOAST NOTIFICATIONS
       ========================================================================== */
    function ensurePatientSelected() {
        if (!currentPatient) {
            alert("Please select an authorized patient first.");
            const input = document.getElementById("patientSearchInput");
            if (input) input.focus();
            return false;
        }
        return true;
    }

    function addRecordToTableDOM(record) {
        if (!record) return;

        const tbody = document.querySelector(".clinical-documents-table tbody");
        if (!tbody) return;

        // Hide empty table message if visible
        const emptyTr = document.getElementById("emptyTableTr");
        if (emptyTr) emptyTr.style.display = "none";

        const recType = (record.record_type || "other").toLowerCase();
        const typeIcons = {
            consultation: "🩺",
            prescription: "💊",
            lab_report: "🔬",
            lab: "🔬",
            scan_imaging: "🔬",
            imaging: "🔬",
            other: "📄"
        };
        const icon = typeIcons[recType] || "📄";
        const typeLabel = (record.record_type || "Document").replace(/_/g, " ");
        const dateStr = record.document_date || record.uploaded_at || "Just now";
        const viewUrl = record.file_url || `/doctor/patient-record/${currentPatient.id}/${record.id}`;
        const uploader = record.uploader_label || record.doctor_name || "Doctor";

        const tr = document.createElement("tr");
        tr.className = "doc-row";
        tr.setAttribute("data-category", recType);
        tr.style.animation = "modalSlideIn 0.3s ease";

        tr.innerHTML = `
            <td>
                <div class="doc-title-cell">
                    <span class="doc-type-icon">${icon}</span>
                    <div class="doc-title-text">
                        <h4>${escapeHtml(record.title || 'Medical Record')}</h4>
                        <p>${escapeHtml(record.description || '')}</p>
                    </div>
                </div>
            </td>
            <td>
                <span class="doc-badge ${escapeHtml(recType)}">${escapeHtml(typeLabel)}</span>
            </td>
            <td>
                <span style="font-weight: 600; color: #1e293b;">${escapeHtml(uploader)}</span>
            </td>
            <td>
                <span style="color: #64748b;">${escapeHtml(dateStr)}</span>
            </td>
            <td>
                <div class="table-action-btns">
                    <button type="button" class="btn-tbl-view" onclick="viewDocumentPdf('${viewUrl}', '${escapeHtml(record.title)}')">
                        <span>👁️ View</span>
                    </button>
                    <a href="${viewUrl}" download class="btn-tbl-download" target="_blank" rel="noopener noreferrer">
                        <span>⬇️ Download</span>
                    </a>
                </div>
            </td>
        `;

        tbody.insertBefore(tr, tbody.firstChild);
    }

    function updateRecentPrescriptionsDOM(record) {
        const list = document.getElementById("recentPrescriptionsList");
        if (!list) return;

        const empty = list.querySelector(".side-widget-empty");
        if (empty) empty.style.display = "none";

        const item = document.createElement("div");
        item.className = "side-record-item";
        const viewUrl = record.file_url || `/doctor/patient-record/${currentPatient.id}/${record.id}`;
        const dateStr = record.document_date || "Just now";
        const docName = record.doctor_name || "Attending Doctor";

        item.innerHTML = `
            <div class="side-record-top">
                <span class="side-record-title">${escapeHtml(record.title)}</span>
                <span class="side-record-date">${escapeHtml(dateStr)}</span>
            </div>
            <div class="side-record-doctor">Prescribed by Dr. ${escapeHtml(docName)}</div>
            <div class="side-record-actions">
                <button type="button" class="side-btn-view" onclick="viewDocumentPdf('${viewUrl}', '${escapeHtml(record.title)}')">View</button>
                <a href="${viewUrl}" download class="side-btn-download" target="_blank">Download PDF</a>
            </div>
        `;

        list.insertBefore(item, list.firstChild);
    }

    function updateRecentConsultationsDOM(record) {
        const list = document.getElementById("recentConsultationsList");
        if (!list) return;

        const empty = list.querySelector(".side-widget-empty");
        if (empty) empty.style.display = "none";

        const item = document.createElement("div");
        item.className = "side-record-item";
        const viewUrl = record.file_url || `/doctor/patient-record/${currentPatient.id}/${record.id}`;
        const dateStr = record.document_date || "Just now";
        const docName = record.doctor_name || "Attending Doctor";

        item.innerHTML = `
            <div class="side-record-top">
                <span class="side-record-title">${escapeHtml(record.title)}</span>
                <span class="side-record-date">${escapeHtml(dateStr)}</span>
            </div>
            <div class="side-record-doctor">Consultation by Dr. ${escapeHtml(docName)}</div>
            <div class="side-record-actions">
                <button type="button" class="side-btn-view" onclick="viewDocumentPdf('${viewUrl}', '${escapeHtml(record.title)}')">View</button>
                <a href="${viewUrl}" download class="side-btn-download" target="_blank">Download PDF</a>
            </div>
        `;

        list.insertBefore(item, list.firstChild);
    }

    function incrementCategoryCount(cat) {
        cat = (cat || "").toLowerCase();
        let targetId = null;

        if (cat === "consultation") targetId = "countConsultations";
        else if (cat === "prescription") targetId = "countPrescriptions";
        else if (cat === "lab_report" || cat === "lab") targetId = "countLab";
        else if (cat === "scan_imaging" || cat === "imaging") targetId = "countImaging";
        else targetId = "countOther";

        const el = document.getElementById(targetId);
        if (el) {
            const current = parseInt(el.textContent, 10) || 0;
            el.textContent = current + 1;
        }

        const totalEl = document.getElementById("countTotalDocs");
        if (totalEl) {
            const currentTotal = parseInt(totalEl.textContent, 10) || 0;
            totalEl.textContent = currentTotal + 1;
        }

        const pill = document.getElementById("tableCountBadge");
        if (pill) {
            const currentTotal = parseInt(pill.textContent, 10) || 0;
            pill.textContent = currentTotal + 1;
        }
    }

    function showToast(msg, type = "success") {
        let toast = document.getElementById("consultationsToast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "consultationsToast";
            toast.className = "consultations-toast";
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.className = `consultations-toast toast-${type} toast-visible`;
        setTimeout(() => {
            toast.className = "consultations-toast";
        }, 4000);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

})();
