// Client-side JavaScript for Patient Workspace Medical Records & Templates

let currentPreviewBlob = null;
let currentPreviewFileName = "medical_document.pdf";
const patientId = "{{ patient.get('id') }}";

// Set default dates to today
document.addEventListener("DOMContentLoaded", function () {
    const today = new Date().toISOString().split("T")[0];
    const dateInputs = ["uploadDate", "consDate", "rxDate", "otherDocDate"];
    dateInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el && !el.value) el.value = today;
    });

    // Initialize prescription with 1 default medicine row
    const container = document.getElementById("medicineRowsContainer");
    if (container && container.children.length === 0) {
        addMedicineRow({
            name: "Paracetamol",
            dosage: "650 mg",
            timing: { morning: true, afternoon: false, evening: true, night: false },
            frequency: "Twice daily",
            food_relation: "After Food",
            duration: "5 days",
            instructions: "Take with water"
        });
    }
});

function openRecordTypeModal() {
    const modal = document.getElementById("recordTypeModal");
    if (modal) {
        modal.style.display = "flex";
        document.body.style.overflow = "hidden";
    }
}

function openOptionModal(modalId) {
    closeWorkspaceModal("recordTypeModal");
    const target = document.getElementById(modalId);
    if (target) {
        target.style.display = "flex";
        document.body.style.overflow = "hidden";
    }
}

function closeWorkspaceModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = "none";
        // Check if any other modal is still visible
        const anyOpen = document.querySelectorAll(".workspace-modal-overlay[style*='display: flex']");
        if (anyOpen.length === 0) {
            document.body.style.overflow = "";
        }
    }
}

// Close on Escape or click outside
document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") {
        document.querySelectorAll(".workspace-modal-overlay").forEach(m => {
            if (m.style.display === "flex") {
                m.style.display = "none";
            }
        });
        document.body.style.overflow = "";
    }
});

// Dropzone handling
function handleFileSelected(input) {
    const file = input.files && input.files[0];
    if (!file) return;

    document.getElementById("dropzonePrompt").style.display = "none";
    const info = document.getElementById("dropzoneFileInfo");
    info.style.display = "flex";
    document.getElementById("selectedFileName").textContent = file.name;

    const sizeKb = Math.round(file.size / 1024);
    document.getElementById("selectedFileSize").textContent = sizeKb > 1024 ? (sizeKb / 1024).toFixed(1) + " MB" : sizeKb + " KB";

    // Auto-fill title if empty
    const titleField = document.getElementById("uploadTitle");
    if (titleField && !titleField.value) {
        const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
        titleField.value = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
    }
}

function clearSelectedFile(e) {
    if (e) e.stopPropagation();
    const input = document.getElementById("fileInputOptionA");
    if (input) input.value = "";
    document.getElementById("dropzonePrompt").style.display = "flex";
    document.getElementById("dropzoneFileInfo").style.display = "none";
}

// BMI Calculation
function calculateBMI() {
    const w = parseFloat(document.getElementById("vitalsWeight").value);
    const h = parseFloat(document.getElementById("vitalsHeight").value);
    const bmiField = document.getElementById("vitalsBmi");
    if (w > 0 && h > 0) {
        const hm = h / 100;
        const bmi = (w / (hm * hm)).toFixed(1);
        bmiField.value = bmi;
    } else {
        bmiField.value = "";
    }
}

// Prescription Medicine Row Management
let medicineRowCounter = 0;

function addMedicineRow(data = {}) {
    medicineRowCounter++;
    const container = document.getElementById("medicineRowsContainer");
    if (!container) return;

    const rowId = `medRow_${medicineRowCounter}`;
    const row = document.createElement("div");
    row.className = "medicine-item-card";
    row.id = rowId;

    const timing = data.timing || { morning: false, afternoon: false, evening: false, night: false };

    row.innerHTML = `
        <div class="med-item-top">
            <span class="med-num-badge">#${container.children.length + 1}</span>
            <div class="med-field-name">
                <input type="text" class="field-control med-input-name" placeholder="Medicine / Generic / Brand Name *" value="${escapeHtml(data.name || '')}" required>
            </div>
            <div class="med-field-dosage">
                <input type="text" class="field-control med-input-dosage" placeholder="Dosage (e.g. 500 mg, 1 Tab)" value="${escapeHtml(data.dosage || '')}">
            </div>
            <button type="button" class="btn-remove-med-row" onclick="removeMedicineRow('${rowId}')" title="Remove medication">✕</button>
        </div>

        <div class="med-item-bottom">
            <div class="timing-chips-group">
                <span class="timing-label">Timing:</span>
                <label class="timing-pill ${timing.morning ? 'active' : ''}">
                    <input type="checkbox" class="timing-cb timing-m" ${timing.morning ? 'checked' : ''} onchange="toggleTimingPill(this)">
                    <span>M (Morning)</span>
                </label>
                <label class="timing-pill ${timing.afternoon ? 'active' : ''}">
                    <input type="checkbox" class="timing-cb timing-a" ${timing.afternoon ? 'checked' : ''} onchange="toggleTimingPill(this)">
                    <span>A (Noon)</span>
                </label>
                <label class="timing-pill ${timing.evening ? 'active' : ''}">
                    <input type="checkbox" class="timing-cb timing-e" ${timing.evening ? 'checked' : ''} onchange="toggleTimingPill(this)">
                    <span>E (Evening)</span>
                </label>
                <label class="timing-pill ${timing.night ? 'active' : ''}">
                    <input type="checkbox" class="timing-cb timing-n" ${timing.night ? 'checked' : ''} onchange="toggleTimingPill(this)">
                    <span>N (Night)</span>
                </label>
            </div>

            <div class="med-meta-fields">
                <select class="field-control med-input-freq">
                    <option value="Once daily" ${data.frequency === 'Once daily' ? 'selected' : ''}>Once daily</option>
                    <option value="Twice daily" ${(!data.frequency || data.frequency === 'Twice daily') ? 'selected' : ''}>Twice daily</option>
                    <option value="Thrice daily" ${data.frequency === 'Thrice daily' ? 'selected' : ''}>Thrice daily</option>
                    <option value="Four times daily" ${data.frequency === 'Four times daily' ? 'selected' : ''}>Four times daily</option>
                    <option value="As needed (SOS)" ${data.frequency === 'As needed (SOS)' ? 'selected' : ''}>As needed (SOS)</option>
                </select>

                <select class="field-control med-input-food">
                    <option value="After Food" ${(!data.food_relation || data.food_relation === 'After Food') ? 'selected' : ''}>After Food</option>
                    <option value="Before Food" ${data.food_relation === 'Before Food' ? 'selected' : ''}>Before Food</option>
                    <option value="With Food" ${data.food_relation === 'With Food' ? 'selected' : ''}>With Food</option>
                    <option value="On Empty Stomach" ${data.food_relation === 'On Empty Stomach' ? 'selected' : ''}>On Empty Stomach</option>
                    <option value="At Bedtime" ${data.food_relation === 'At Bedtime' ? 'selected' : ''}>At Bedtime</option>
                </select>

                <input type="text" class="field-control med-input-duration" placeholder="Duration (e.g. 5 days)" value="${escapeHtml(data.duration || '5 days')}">
                <input type="text" class="field-control med-input-instructions" placeholder="Instructions (e.g. with water)" value="${escapeHtml(data.instructions || '')}">
            </div>
        </div>
    `;

    container.appendChild(row);
    reindexMedicineRows();
}

function removeMedicineRow(rowId) {
    const container = document.getElementById("medicineRowsContainer");
    if (!container) return;
    if (container.children.length <= 1) {
        alert("At least one medicine is required in the prescription.");
        return;
    }
    const row = document.getElementById(rowId);
    if (row) row.remove();
    reindexMedicineRows();
}

function reindexMedicineRows() {
    const container = document.getElementById("medicineRowsContainer");
    if (!container) return;
    Array.from(container.children).forEach((child, idx) => {
        const badge = child.querySelector(".med-num-badge");
        if (badge) badge.textContent = `#${idx + 1}`;
    });
}

function toggleTimingPill(cb) {
    const label = cb.closest(".timing-pill");
    if (label) {
        if (cb.checked) label.classList.add("active");
        else label.classList.remove("active");
    }
}

function collectMedicinesData() {
    const container = document.getElementById("medicineRowsContainer");
    if (!container) return [];
    const list = [];
    Array.from(container.children).forEach(row => {
        const name = (row.querySelector(".med-input-name")?.value || "").trim();
        if (!name) return;
        const dosage = (row.querySelector(".med-input-dosage")?.value || "").trim();
        const m = row.querySelector(".timing-m")?.checked || false;
        const a = row.querySelector(".timing-a")?.checked || false;
        const e = row.querySelector(".timing-e")?.checked || false;
        const n = row.querySelector(".timing-n")?.checked || false;
        const frequency = row.querySelector(".med-input-freq")?.value || "";
        const food = row.querySelector(".med-input-food")?.value || "";
        const duration = (row.querySelector(".med-input-duration")?.value || "").trim();
        const instructions = (row.querySelector(".med-input-instructions")?.value || "").trim();

        list.push({
            name: name,
            dosage: dosage,
            timing: { morning: m, afternoon: a, evening: e, night: n },
            frequency: frequency,
            food_relation: food,
            duration: duration,
            instructions: instructions
        });
    });
    return list;
}

// Other Doc Template Type Change
function handleOtherDocTypeChange(val) {
    const titleField = document.getElementById("otherDocTitle");
    const secCert = document.getElementById("sectionMedicalCert");
    const secRef = document.getElementById("sectionReferral");

    if (secCert) secCert.style.display = (val === "medical_certificate") ? "block" : "none";
    if (secRef) secRef.style.display = (val === "referral_letter") ? "block" : "none";

    const titles = {
        "medical_certificate": "Medical Fitness Certificate",
        "referral_letter": "Clinical Referral Letter",
        "discharge_summary": "Inpatient Discharge Summary",
        "lab_report": "Laboratory Investigation Summary",
        "scan_imaging": "Diagnostic Imaging & Radiology Report",
        "other": "Clinical Medical Report"
    };
    if (titleField) {
        titleField.value = titles[val] || "Medical Document";
    }
}

// Live PDF Preview
async function previewPDF(templateType) {
    const previewBtn = event?.currentTarget;
    const origHTML = previewBtn ? previewBtn.innerHTML : "";
    if (previewBtn) {
        previewBtn.disabled = true;
        previewBtn.innerHTML = `<span>⏳</span><span>Generating Preview...</span>`;
    }

    try {
        let payload = { template_type: templateType };

        if (templateType === "consultation") {
            payload.consultation_type = document.getElementById("consType").value;
            payload.document_date = document.getElementById("consDate").value;
            payload.chief_complaint = document.getElementById("consChiefComplaint").value;
            payload.hpi = document.getElementById("consHpi").value;
            payload.vitals = {
                bp: document.getElementById("vitalsBp").value,
                pulse: document.getElementById("vitalsPulse").value,
                temperature: document.getElementById("vitalsTemp").value,
                respiratory_rate: document.getElementById("vitalsRr").value,
                oxygen_saturation: document.getElementById("vitalsSpo2").value,
                weight: document.getElementById("vitalsWeight").value,
                height: document.getElementById("vitalsHeight").value,
                bmi: document.getElementById("vitalsBmi").value
            };
            payload.diagnosis_primary = document.getElementById("consPrimaryDiag").value;
            payload.diagnosis_secondary = document.getElementById("consSecondaryDiag").value;
            payload.treatment_plan = document.getElementById("consTreatmentPlan").value;
            payload.clinical_notes = document.getElementById("consClinicalNotes").value;
            currentPreviewFileName = `consultation_note_${payload.document_date}.pdf`;

        } else if (templateType === "prescription") {
            payload.document_date = document.getElementById("rxDate").value;
            payload.diagnosis = document.getElementById("rxDiagnosis").value;
            payload.medicines = collectMedicinesData();
            payload.clinical_notes = document.getElementById("rxClinicalNotes").value;
            payload.general_advice = document.getElementById("rxAdvice").value;
            payload.follow_up = document.getElementById("rxFollowUp").value;
            currentPreviewFileName = `prescription_${payload.document_date}.pdf`;

        } else {
            payload.doc_type = document.getElementById("otherDocType").value;
            payload.title = document.getElementById("otherDocTitle").value;
            payload.document_date = document.getElementById("otherDocDate").value;
            payload.certificate_reason = document.getElementById("certDiagnosis")?.value || "";
            payload.valid_from = document.getElementById("certFromDate")?.value || "";
            payload.valid_to = document.getElementById("certToDate")?.value || "";
            payload.recipient = document.getElementById("refDoctor")?.value || "";
            payload.clinical_summary = document.getElementById("otherSummary").value;
            payload.findings = document.getElementById("otherFindings").value;
            payload.recommendations = document.getElementById("otherRecs").value;
            currentPreviewFileName = `${payload.doc_type}_${payload.document_date}.pdf`;
        }

        const previewUrl = `/doctor/patient-workspace/${patientId}/preview-document-pdf`;
        const res = await fetch(previewUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || `Server returned ${res.status}`);
        }

        const blob = await res.blob();
        currentPreviewBlob = blob;
        const blobUrl = URL.createObjectURL(blob);
        const iframe = document.getElementById("pdfPreviewIframe");
        if (iframe) {
            iframe.src = blobUrl;
        }

        const previewModal = document.getElementById("modalPdfPreview");
        if (previewModal) {
            previewModal.style.display = "flex";
            document.body.style.overflow = "hidden";
        }

    } catch (err) {
        console.error("Preview error:", err);
        alert(`Failed to generate PDF preview: ${err.message}`);
    } finally {
        if (previewBtn) {
            previewBtn.disabled = false;
            previewBtn.innerHTML = origHTML;
        }
    }
}

function downloadCurrentPreviewPDF() {
    if (!currentPreviewBlob) {
        alert("No preview PDF available to download.");
        return;
    }
    const url = URL.createObjectURL(currentPreviewBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = currentPreviewFileName || "medical_document.pdf";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Submissions
async function submitOptionA(e) {
    e.preventDefault();
    const btn = document.getElementById("btnSubmitOptionA");
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span><span>Uploading & Processing...</span>`;

    const form = document.getElementById("formOptionA");
    const formData = new FormData(form);

    try {
        const res = await fetch(`/doctor/patient-workspace/${patientId}/upload-medical-record`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            closeWorkspaceModal("modalOptionA");
            insertRecordCardIntoDOM(data.record);
            showNotificationToast("Medical record uploaded and saved successfully!", "success");
            form.reset();
            clearSelectedFile();
        } else {
            alert(data.error || "Failed to upload document.");
        }
    } catch (err) {
        console.error("Upload error:", err);
        alert("Network error while uploading medical record.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHTML;
    }
}

async function submitOptionB(e) {
    e.preventDefault();
    const btn = document.getElementById("btnSubmitOptionB");
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span><span>Generating Official PDF...</span>`;

    const payload = {
        consultation_type: document.getElementById("consType").value,
        document_date: document.getElementById("consDate").value,
        chief_complaint: document.getElementById("consChiefComplaint").value,
        hpi: document.getElementById("consHpi").value,
        vitals: {
            bp: document.getElementById("vitalsBp").value,
            pulse: document.getElementById("vitalsPulse").value,
            temperature: document.getElementById("vitalsTemp").value,
            respiratory_rate: document.getElementById("vitalsRr").value,
            oxygen_saturation: document.getElementById("vitalsSpo2").value,
            weight: document.getElementById("vitalsWeight").value,
            height: document.getElementById("vitalsHeight").value,
            bmi: document.getElementById("vitalsBmi").value
        },
        diagnosis_primary: document.getElementById("consPrimaryDiag").value,
        diagnosis_secondary: document.getElementById("consSecondaryDiag").value,
        treatment_plan: document.getElementById("consTreatmentPlan").value,
        clinical_notes: document.getElementById("consClinicalNotes").value
    };

    try {
        const res = await fetch(`/doctor/patient-workspace/${patientId}/create-consultation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeWorkspaceModal("modalOptionB");
            insertRecordCardIntoDOM(data.record);
            showNotificationToast("Consultation Note created and PDF generated!", "success");
            document.getElementById("formOptionB").reset();
        } else {
            alert(data.error || "Failed to create consultation note.");
        }
    } catch (err) {
        console.error("Consultation submit error:", err);
        alert("Network error while saving consultation note.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHTML;
    }
}

async function submitOptionC(e) {
    e.preventDefault();
    const btn = document.getElementById("btnSubmitOptionC");
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span><span>Generating Prescription PDF...</span>`;

    const medicines = collectMedicinesData();
    if (medicines.length === 0) {
        alert("Please add at least one medication to the prescription.");
        btn.disabled = false;
        btn.innerHTML = origHTML;
        return;
    }

    const payload = {
        document_date: document.getElementById("rxDate").value,
        diagnosis: document.getElementById("rxDiagnosis").value,
        medicines: medicines,
        clinical_notes: document.getElementById("rxClinicalNotes").value,
        general_advice: document.getElementById("rxAdvice").value,
        follow_up: document.getElementById("rxFollowUp").value
    };

    try {
        const res = await fetch(`/doctor/patient-workspace/${patientId}/create-prescription`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeWorkspaceModal("modalOptionC");
            insertRecordCardIntoDOM(data.record);
            showNotificationToast("Digital Prescription created and PDF generated!", "success");
            document.getElementById("formOptionC").reset();
        } else {
            alert(data.error || "Failed to create prescription.");
        }
    } catch (err) {
        console.error("Prescription submit error:", err);
        alert("Network error while saving prescription.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHTML;
    }
}

async function submitOptionD(e) {
    e.preventDefault();
    const btn = document.getElementById("btnSubmitOptionD");
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span><span>Generating Document...</span>`;

    const payload = {
        doc_type: document.getElementById("otherDocType").value,
        title: document.getElementById("otherDocTitle").value,
        document_date: document.getElementById("otherDocDate").value,
        certificate_reason: document.getElementById("certDiagnosis")?.value || "",
        valid_from: document.getElementById("certFromDate")?.value || "",
        valid_to: document.getElementById("certToDate")?.value || "",
        recipient: document.getElementById("refDoctor")?.value || "",
        clinical_summary: document.getElementById("otherSummary").value,
        findings: document.getElementById("otherFindings").value,
        recommendations: document.getElementById("otherRecs").value
    };

    try {
        const res = await fetch(`/doctor/patient-workspace/${patientId}/create-other-document`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeWorkspaceModal("modalOptionD");
            insertRecordCardIntoDOM(data.record);
            showNotificationToast(`${payload.title} created successfully!`, "success");
            document.getElementById("formOptionD").reset();
        } else {
            alert(data.error || "Failed to create document.");
        }
    } catch (err) {
        console.error("Other doc submit error:", err);
        alert("Network error while saving document.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHTML;
    }
}

// Dynamic DOM update helper
function insertRecordCardIntoDOM(record) {
    if (!record) return;

    const noRecs = document.querySelector(".no-records");
    if (noRecs) noRecs.style.display = "none";

    let list = document.querySelector(".medical-records-list");
    if (!list) {
        const section = document.querySelector("#medical-records-tab .workspace-section");
        if (section) {
            list = document.createElement("div");
            list.className = "medical-records-list";
            section.appendChild(list);
        }
    }
    if (!list) return;

    // Determine icon and badges
    const typeIcons = {
        prescription: "💊",
        consultation: "🩺",
        lab_report: "🔬",
        scan_imaging: "🔬",
        discharge_summary: "📋",
        medical_certificate: "📜",
        referral_letter: "📤"
    };
    const icon = typeIcons[record.record_type] || "📄";
    const typeLabel = (record.record_type || "Document").replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
    const viewUrl = record.file_url || `/doctor/patient-record/${patientId}/${record.id}`;

    const card = document.createElement("div");
    card.className = "medical-record-card new-record-highlight";
    card.setAttribute("data-record-id", record.id || "");

    card.innerHTML = `
        <div class="record-icon">${icon}</div>
        <div class="record-information">
            <div class="record-title-row">
                <h3>${escapeHtml(record.title || 'Medical Record')}</h3>
                <span class="record-type-badge ${escapeHtml(record.record_type || 'other')}">${escapeHtml(typeLabel)}</span>
            </div>
            ${record.description ? `<p class="record-description">${escapeHtml(record.description)}</p>` : ''}
            <div class="record-meta-chips">
                <span class="meta-chip">📅 Just now</span>
                ${record.hospital_name ? `<span class="meta-chip">🏥 ${escapeHtml(record.hospital_name)}</span>` : ''}
                ${record.doctor_name ? `<span class="meta-chip">👨‍⚕️ ${escapeHtml(record.doctor_name)}</span>` : ''}
            </div>
        </div>
        <div class="record-actions">
            <a href="${viewUrl}" target="_blank" rel="noopener noreferrer" class="view-record-btn">
                View Record <span>→</span>
            </a>
        </div>
    `;

    list.insertBefore(card, list.firstChild);

    // Update count badge
    const countBadge = document.getElementById("record-count-badge") || document.querySelector(".record-count");
    if (countBadge) {
        const currentCount = list.querySelectorAll(".medical-record-card").length;
        countBadge.textContent = currentCount;
    }
}

function showNotificationToast(msg, type = "success") {
    let toast = document.getElementById("workspaceNotificationToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "workspaceNotificationToast";
        toast.className = "workspace-toast";
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.className = `workspace-toast toast-${type} toast-visible`;
    setTimeout(() => {
        toast.className = "workspace-toast";
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
