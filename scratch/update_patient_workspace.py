import re

template_path = "templates/doctor/patient_workspace.html"

with open(template_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update modalOptionA form class
content = content.replace(
    '<form id="formOptionA" enctype="multipart/form-data" onsubmit="submitOptionA(event)">',
    '<form id="formOptionA" class="modal-card-form" enctype="multipart/form-data" onsubmit="submitOptionA(event)">'
)

# 2. Update modalOptionD form class
content = content.replace(
    '<form id="formOptionD" onsubmit="submitOptionD(event)">',
    '<form id="formOptionD" class="modal-card-form" onsubmit="submitOptionD(event)">'
)

# 3. Update modalOptionB completely
# Find from <!-- MODAL 3: OPTION B to <!-- MODAL 4: OPTION C
pattern_b = r'(<!-- MODAL 3: OPTION B — CREATE CONSULTATION NOTE -->[\s\S]*?)(<!-- MODAL 4: OPTION C — CREATE PRESCRIPTION -->)'
replacement_b = """<!-- MODAL 3: OPTION B — CREATE CONSULTATION NOTE -->
<div id="modalOptionB" class="workspace-modal-overlay" style="display: none;" role="dialog" aria-modal="true" aria-labelledby="modalOptionBTitle">
    <div class="workspace-modal-card modal-card-xl">
        <div class="modal-card-header">
            <div class="modal-header-icon">🩺</div>
            <div>
                <h3 id="modalOptionBTitle" class="modal-title">Clinical Consultation Note</h3>
                <p class="modal-subtitle">Document clinical consultation, vital signs, diagnosis, findings, and treatment for {{ patient.get('name') or patient.get('full_name') }}.</p>
            </div>
            <button type="button" class="modal-close-btn" onclick="closeWorkspaceModal('modalOptionB')" aria-label="Close modal">✕</button>
        </div>
        <form id="formOptionB" class="modal-card-form" onsubmit="submitOptionB(event)">
            <div class="modal-card-body">
                <!-- Pre-populated Header Banner -->
                <div class="template-context-banner">
                    <div class="banner-col">
                        <span class="context-label">ATTENDING CLINICIAN</span>
                        <strong>{{ doctor_profile.get('full_name') or 'Dr. Attending Physician' }}</strong>
                        <span class="context-sub">{{ doctor_profile.get('specialization') or 'General Medicine' }} | Reg: {{ doctor_profile.get('registration_number') or 'Registered' }}</span>
                        <span class="context-sub">{{ doctor_profile.get('hospital_name') or 'OmniCare Clinical Center' }}</span>
                    </div>
                    <div class="banner-divider"></div>
                    <div class="banner-col">
                        <span class="context-label">PATIENT DETAILS</span>
                        <strong>{{ patient.get('name') or patient.get('full_name') or 'Patient' }}</strong>
                        <span class="context-sub">ID: {{ patient.get('id')[:12] if patient.get('id') else 'PT-ID' }} | Age: {{ patient.get('age') or 'N/A' }} yrs | Gender: {{ (patient.get('gender') or 'N/A')|title }}</span>
                        <span class="context-sub">Blood Group: {{ patient.get('blood_group') or 'Unknown' }}</span>
                    </div>
                </div>

                <div class="form-row-grid-3">
                    <div class="form-group">
                        <label for="consType" class="field-label">Consultation Type <span class="required-star">*</span></label>
                        <select id="consType" name="consultation_type" class="field-control" required>
                            <option value="General Consultation" selected>General Consultation</option>
                            <option value="Follow-up Visit">Follow-up Visit</option>
                            <option value="Specialist Consultation">Specialist Consultation</option>
                            <option value="Routine Checkup">Routine Checkup</option>
                            <option value="Emergency Consultation">Emergency Consultation</option>
                            <option value="Teleconsultation">Teleconsultation</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="consDate" class="field-label">Consultation Date <span class="required-star">*</span></label>
                        <input type="date" id="consDate" name="document_date" class="field-control" required>
                    </div>

                    <div class="form-group">
                        <label for="consTime" class="field-label">Consultation Time</label>
                        <input type="time" id="consTime" name="consultation_time" class="field-control">
                    </div>
                </div>

                <!-- Chief Complaint & HPI -->
                <div class="form-group">
                    <label for="consChiefComplaint" class="field-label">Chief Complaint <span class="required-star">*</span></label>
                    <textarea id="consChiefComplaint" name="chief_complaint" class="field-control" rows="2" placeholder="e.g., High-grade fever for 3 days, productive cough, shortness of breath on exertion" required></textarea>
                </div>

                <div class="form-group">
                    <label for="consHpi" class="field-label">History of Present Illness (HPI)</label>
                    <textarea id="consHpi" name="hpi" class="field-control" rows="2" placeholder="Onset, duration, severity, progression, relieving/aggravating factors, previous treatments..."></textarea>
                </div>

                <!-- Vitals Table / Responsive Grid -->
                <div class="section-subheading">
                    <span>Vital Signs</span>
                    <span class="subheading-hint">Record vital measurements during this consultation</span>
                </div>
                <div class="vitals-input-grid">
                    <div class="vitals-cell">
                        <label for="vitalsBp" class="vital-label">Blood Pressure</label>
                        <div class="vital-input-wrapper">
                            <input type="text" id="vitalsBp" name="vitals_bp" class="field-control vital-field" placeholder="120/80">
                            <span class="vital-unit">mmHg</span>
                        </div>
                    </div>
                    <div class="vitals-cell">
                        <label for="vitalsPulse" class="vital-label">Pulse / HR</label>
                        <div class="vital-input-wrapper">
                            <input type="number" id="vitalsPulse" name="vitals_pulse" class="field-control vital-field" placeholder="72">
                            <span class="vital-unit">bpm</span>
                        </div>
                    </div>
                    <div class="vitals-cell">
                        <label for="vitalsTemp" class="vital-label">Temperature</label>
                        <div class="vital-input-wrapper">
                            <input type="text" id="vitalsTemp" name="vitals_temp" class="field-control vital-field" placeholder="98.6">
                            <span class="vital-unit">°F</span>
                        </div>
                    </div>
                    <div class="vitals-cell">
                        <label for="vitalsRr" class="vital-label">Resp. Rate</label>
                        <div class="vital-input-wrapper">
                            <input type="number" id="vitalsRr" name="vitals_rr" class="field-control vital-field" placeholder="16">
                            <span class="vital-unit">/min</span>
                        </div>
                    </div>
                    <div class="vitals-cell">
                        <label for="vitalsSpo2" class="vital-label">SpO2</label>
                        <div class="vital-input-wrapper">
                            <input type="number" id="vitalsSpo2" name="vitals_spo2" class="field-control vital-field" placeholder="98">
                            <span class="vital-unit">%</span>
                        </div>
                    </div>
                    <div class="vitals-cell">
                        <label for="vitalsWeight" class="vital-label">Weight</label>
                        <div class="vital-input-wrapper">
                            <input type="number" step="0.1" id="vitalsWeight" name="vitals_weight" class="field-control vital-field" placeholder="70" oninput="calculateBMI()">
                            <span class="vital-unit">kg</span>
                        </div>
                    </div>
                    <div class="vitals-cell">
                        <label for="vitalsHeight" class="vital-label">Height</label>
                        <div class="vital-input-wrapper">
                            <input type="number" step="0.5" id="vitalsHeight" name="vitals_height" class="field-control vital-field" placeholder="170" oninput="calculateBMI()">
                            <span class="vital-unit">cm</span>
                        </div>
                    </div>
                    <div class="vitals-cell">
                        <label for="vitalsBmi" class="vital-label">BMI (Calculated)</label>
                        <div class="vital-input-wrapper">
                            <input type="text" id="vitalsBmi" name="vitals_bmi" class="field-control vital-field" placeholder="24.2" readonly>
                            <span class="vital-unit">kg/m²</span>
                        </div>
                    </div>
                </div>

                <!-- Diagnosis -->
                <div class="form-row-grid" style="margin-top: 14px;">
                    <div class="form-group">
                        <label for="consPrimaryDiag" class="field-label">Primary Diagnosis <span class="required-star">*</span></label>
                        <input type="text" id="consPrimaryDiag" name="diagnosis_primary" class="field-control" placeholder="e.g., Acute Bronchitis / Type 2 Diabetes Mellitus" required>
                    </div>

                    <div class="form-group">
                        <label for="consSecondaryDiag" class="field-label">Secondary / Differential Diagnosis</label>
                        <input type="text" id="consSecondaryDiag" name="diagnosis_secondary" class="field-control" placeholder="e.g., Essential Hypertension, Mild Allergic Rhinitis">
                    </div>
                </div>

                <!-- Findings & Test Results -->
                <div class="form-group">
                    <label for="consFindings" class="field-label">Findings & Test Results / Clinical Examination</label>
                    <textarea id="consFindings" name="findings" class="field-control" rows="2" placeholder="Clinical examination findings, systemic exam observations, diagnostic/imaging/lab test results..."></textarea>
                </div>

                <!-- Treatment Plan & Notes -->
                <div class="form-group">
                    <label for="consTreatmentPlan" class="field-label">Treatment Plan & Clinical Management</label>
                    <textarea id="consTreatmentPlan" name="treatment_plan" class="field-control" rows="2" placeholder="Prescribed medications summary, lab orders, diagnostic imaging requests, physical therapy, lifestyle changes..."></textarea>
                </div>

                <!-- Recommendations & Advice -->
                <div class="form-group">
                    <label for="consRecommendations" class="field-label">Recommendations & Patient Advice</label>
                    <textarea id="consRecommendations" name="recommendations" class="field-control" rows="2" placeholder="Dietary restrictions, lifestyle advice, precautions, activities to avoid, hydration..."></textarea>
                </div>

                <!-- Follow-up -->
                <div class="form-group">
                    <label for="consFollowUp" class="field-label">Follow-up Date / Timeline</label>
                    <input type="text" id="consFollowUp" name="follow_up" class="field-control" placeholder="e.g., Review after 5 days or sooner if fever persists or difficulty breathing occurs">
                </div>

                <div class="form-group">
                    <label for="consClinicalNotes" class="field-label">Additional Clinical Notes</label>
                    <textarea id="consClinicalNotes" name="clinical_notes" class="field-control" rows="2" placeholder="Additional observations, confidential doctor notes, allergy warnings..."></textarea>
                </div>
            </div>
            <div class="modal-card-footer">
                <button type="button" class="btn-workspace-secondary" onclick="closeWorkspaceModal('modalOptionB')">Cancel</button>
                <div class="footer-action-buttons">
                    <button type="button" class="btn-workspace-preview" onclick="previewPDF('consultation')">
                        <span>👁️ Live PDF Preview</span>
                    </button>
                    <button type="submit" class="btn-workspace-primary" id="btnSubmitOptionB">
                        <span>💾 Save & Generate PDF</span>
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>\n\n\\2"""

content = re.sub(pattern_b, replacement_b, content)

# 4. Update modalOptionC completely
# Find from <!-- MODAL 4: OPTION C to <!-- MODAL 5: OPTION D
pattern_c = r'(<!-- MODAL 4: OPTION C — CREATE PRESCRIPTION -->[\s\S]*?)(<!-- MODAL 5: OPTION D — OTHER MEDICAL DOCUMENT TEMPLATE -->)'
replacement_c = """<!-- MODAL 4: OPTION C — CREATE PRESCRIPTION -->
<div id="modalOptionC" class="workspace-modal-overlay" style="display: none;" role="dialog" aria-modal="true" aria-labelledby="modalOptionCTitle">
    <div class="workspace-modal-card modal-card-xl">
        <div class="modal-card-header">
            <div class="modal-header-icon">💊</div>
            <div>
                <h3 id="modalOptionCTitle" class="modal-title">Hospital Digital Prescription</h3>
                <p class="modal-subtitle">Generate an official digital prescription with structured medication dosing for {{ patient.get('name') or patient.get('full_name') }}.</p>
            </div>
            <button type="button" class="modal-close-btn" onclick="closeWorkspaceModal('modalOptionC')" aria-label="Close modal">✕</button>
        </div>
        <form id="formOptionC" class="modal-card-form" onsubmit="submitOptionC(event)">
            <div class="modal-card-body">
                <!-- Header Banner -->
                <div class="template-context-banner">
                    <div class="banner-col">
                        <span class="context-label">PRESCRIBING CLINICIAN</span>
                        <strong>{{ doctor_profile.get('full_name') or 'Dr. Attending Physician' }}</strong>
                        <span class="context-sub">{{ doctor_profile.get('specialization') or 'General Medicine' }} | Reg: {{ doctor_profile.get('registration_number') or 'Registered' }}</span>
                        <span class="context-sub">{{ doctor_profile.get('hospital_name') or 'OmniCare Clinical Center' }}</span>
                    </div>
                    <div class="banner-divider"></div>
                    <div class="banner-col">
                        <span class="context-label">PATIENT DETAILS</span>
                        <strong>{{ patient.get('name') or patient.get('full_name') or 'Patient' }}</strong>
                        <span class="context-sub">ID: {{ patient.get('id')[:12] if patient.get('id') else 'PT-ID' }} | Age: {{ patient.get('age') or 'N/A' }} yrs | Gender: {{ (patient.get('gender') or 'N/A')|title }}</span>
                        <span class="context-sub">Weight: {{ patient.get('weight') or 'N/A' }} | Allergies: {{ patient.get('allergies') or 'None reported' }}</span>
                    </div>
                </div>

                <div class="form-row-grid-3">
                    <div class="form-group">
                        <label for="rxDiagnosis" class="field-label">Diagnosis / Indication <span class="required-star">*</span></label>
                        <input type="text" id="rxDiagnosis" name="diagnosis" class="field-control" placeholder="e.g., Acute Pharyngitis / Upper Respiratory Tract Infection" required>
                    </div>

                    <div class="form-group">
                        <label for="rxDate" class="field-label">Prescription Date <span class="required-star">*</span></label>
                        <input type="date" id="rxDate" name="document_date" class="field-control" required>
                    </div>

                    <div class="form-group">
                        <label for="rxTime" class="field-label">Prescription Time</label>
                        <input type="time" id="rxTime" name="prescription_time" class="field-control">
                    </div>
                </div>

                <!-- Medicine Builder Section -->
                <div class="medicine-builder-header">
                    <div>
                        <h4 class="medicine-builder-title">Prescribed Medications</h4>
                        <p class="medicine-builder-subtitle">Specify medicine details and mark horizontal timing checkboxes for Morning, Afternoon, Evening, and Night.</p>
                    </div>
                    <button type="button" class="btn-add-medicine" onclick="addMedicineRow()">
                        <span>➕ Add Medicine</span>
                    </button>
                </div>

                <!-- Medicines List Container -->
                <div id="medicineRowsContainer" class="medicine-rows-list">
                    <!-- Populated dynamically by JavaScript -->
                </div>

                <!-- General Advice & Follow-up -->
                <div class="form-row-grid" style="margin-top: 16px;">
                    <div class="form-group">
                        <label for="rxAdvice" class="field-label">General Advice & Dietary Instructions</label>
                        <textarea id="rxAdvice" name="general_advice" class="field-control" rows="2" placeholder="e.g., Drink warm fluids, salt water gargles 3 times a day, avoid cold drinks and smoking..."></textarea>
                    </div>

                    <div class="form-group">
                        <label for="rxFollowUp" class="field-label">Follow-up Instructions / Date</label>
                        <textarea id="rxFollowUp" name="follow_up" class="field-control" rows="2" placeholder="e.g., Review after 5 days if fever persists or sooner in case of difficulty breathing."></textarea>
                    </div>
                </div>

                <div class="form-group">
                    <label for="rxClinicalNotes" class="field-label">Additional Clinical Notes / Warnings</label>
                    <input type="text" id="rxClinicalNotes" name="clinical_notes" class="field-control" placeholder="e.g., Take antibiotics at exact 12-hour intervals. Complete full course.">
                </div>
            </div>
            <div class="modal-card-footer">
                <button type="button" class="btn-workspace-secondary" onclick="closeWorkspaceModal('modalOptionC')">Cancel</button>
                <div class="footer-action-buttons">
                    <button type="button" class="btn-workspace-preview" onclick="previewPDF('prescription')">
                        <span>👁️ Live PDF Preview</span>
                    </button>
                    <button type="submit" class="btn-workspace-primary" id="btnSubmitOptionC">
                        <span>💾 Save & Generate Prescription PDF</span>
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>\n\n\\2"""

content = re.sub(pattern_c, replacement_c, content)

# 5. Update addMedicineRow & collectMedicinesData
new_add_med = """function addMedicineRow(data = {}) {
    medicineRowCounter++;
    const container = document.getElementById("medicineRowsContainer");
    if (!container) return;

    const rowId = `medRow_${medicineRowCounter}`;
    const row = document.createElement("div");
    row.className = "medicine-item-card";
    row.id = rowId;

    const timing = data.timing || { morning: false, afternoon: false, evening: false, night: false };
    const curType = data.type || "Tablet";

    row.innerHTML = `
        <div class="med-item-top">
            <span class="med-num-badge">#${container.children.length + 1}</span>
            <div class="med-field-name">
                <input type="text" class="field-control med-input-name" placeholder="Medicine / Generic / Brand Name *" value="${escapeHtml(data.name || '')}" required>
            </div>
            <div class="med-field-type">
                <select class="field-control med-input-type">
                    <option value="Tablet" ${curType === 'Tablet' ? 'selected' : ''}>Tablet</option>
                    <option value="Capsule" ${curType === 'Capsule' ? 'selected' : ''}>Capsule</option>
                    <option value="Syrup" ${curType === 'Syrup' ? 'selected' : ''}>Syrup</option>
                    <option value="Injection" ${curType === 'Injection' ? 'selected' : ''}>Injection</option>
                    <option value="Drops" ${curType === 'Drops' ? 'selected' : ''}>Drops</option>
                    <option value="Inhaler" ${curType === 'Inhaler' ? 'selected' : ''}>Inhaler</option>
                    <option value="Ointment" ${curType === 'Ointment' ? 'selected' : ''}>Ointment</option>
                    <option value="Gel" ${curType === 'Gel' ? 'selected' : ''}>Gel</option>
                    <option value="Suspension" ${curType === 'Suspension' ? 'selected' : ''}>Suspension</option>
                    <option value="Solution" ${curType === 'Solution' ? 'selected' : ''}>Solution</option>
                    <option value="Cream" ${curType === 'Cream' ? 'selected' : ''}>Cream</option>
                    <option value="Powder" ${curType === 'Powder' ? 'selected' : ''}>Powder</option>
                    <option value="Spray" ${curType === 'Spray' ? 'selected' : ''}>Spray</option>
                    <option value="Other" ${curType === 'Other' ? 'selected' : ''}>Other</option>
                </select>
            </div>
            <div class="med-field-strength">
                <input type="text" class="field-control med-input-strength" placeholder="Strength (e.g. 500mg, 10mg)" value="${escapeHtml(data.strength || '')}">
            </div>
            <div class="med-field-dosage">
                <input type="text" class="field-control med-input-dosage" placeholder="Dose (e.g. 1 tab, 5ml)" value="${escapeHtml(data.dosage || '')}">
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
                    <option value="Once daily" ${data.frequency === 'Once daily' ? 'selected' : ''}>Once daily (OD)</option>
                    <option value="Twice daily" ${(!data.frequency || data.frequency === 'Twice daily') ? 'selected' : ''}>Twice daily (BD)</option>
                    <option value="Thrice daily" ${data.frequency === 'Thrice daily' ? 'selected' : ''}>Thrice daily (TDS)</option>
                    <option value="Four times daily" ${data.frequency === 'Four times daily' ? 'selected' : ''}>Four times daily (QID)</option>
                    <option value="Every 4 hours" ${data.frequency === 'Every 4 hours' ? 'selected' : ''}>Every 4 hours</option>
                    <option value="Every 6 hours" ${data.frequency === 'Every 6 hours' ? 'selected' : ''}>Every 6 hours</option>
                    <option value="Every 8 hours" ${data.frequency === 'Every 8 hours' ? 'selected' : ''}>Every 8 hours</option>
                    <option value="Every 12 hours" ${data.frequency === 'Every 12 hours' ? 'selected' : ''}>Every 12 hours</option>
                    <option value="As needed (SOS)" ${data.frequency === 'As needed (SOS)' ? 'selected' : ''}>As needed (SOS)</option>
                    <option value="At bedtime" ${data.frequency === 'At bedtime' ? 'selected' : ''}>At bedtime (HS)</option>
                </select>

                <select class="field-control med-input-food">
                    <option value="After Food" ${(!data.food_relation || data.food_relation === 'After Food') ? 'selected' : ''}>After Food (PC)</option>
                    <option value="Before Food" ${data.food_relation === 'Before Food' ? 'selected' : ''}>Before Food (AC)</option>
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
}"""

pattern_add_med = r'function addMedicineRow\(data = \{\}\) \{[\s\S]*?container\.appendChild\(row\);\s*reindexMedicineRows\(\);\s*\}'
content = re.sub(pattern_add_med, new_add_med, content)

new_collect_med = """function collectMedicinesData() {
    const container = document.getElementById("medicineRowsContainer");
    if (!container) return [];
    const list = [];
    Array.from(container.children).forEach(row => {
        const name = (row.querySelector(".med-input-name")?.value || "").trim();
        if (!name) return;
        const type = row.querySelector(".med-input-type")?.value || "Tablet";
        const strength = (row.querySelector(".med-input-strength")?.value || "").trim();
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
            type: type,
            strength: strength,
            dosage: dosage,
            timing: { morning: m, afternoon: a, evening: e, night: n },
            frequency: frequency,
            food_relation: food,
            duration: duration,
            instructions: instructions
        });
    });
    return list;
}"""

pattern_collect_med = r'function collectMedicinesData\(\) \{[\s\S]*?return list;\s*\}'
content = re.sub(pattern_collect_med, new_collect_med, content)

# 6. Update submitOptionB
new_submit_b = """async function submitOptionB(e) {
    e.preventDefault();
    const btn = document.getElementById("btnSubmitOptionB");
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span><span>Generating Official PDF...</span>`;

    const payload = {
        consultation_type: document.getElementById("consType").value,
        document_date: document.getElementById("consDate").value,
        consultation_time: document.getElementById("consTime")?.value || "",
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
        findings: document.getElementById("consFindings")?.value || "",
        treatment_plan: document.getElementById("consTreatmentPlan").value,
        recommendations: document.getElementById("consRecommendations")?.value || "",
        follow_up: document.getElementById("consFollowUp")?.value || "",
        clinical_notes: document.getElementById("consClinicalNotes").value
    };"""

pattern_submit_b = r'async function submitOptionB\(e\) \{[\s\S]*?clinical_notes:\s*document\.getElementById\("consClinicalNotes"\)\.value\s*\};'
content = re.sub(pattern_submit_b, new_submit_b, content)

# 7. Update submitOptionC
new_submit_c = """async function submitOptionC(e) {
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
        prescription_time: document.getElementById("rxTime")?.value || "",
        diagnosis: document.getElementById("rxDiagnosis").value,
        medicines: medicines,
        clinical_notes: document.getElementById("rxClinicalNotes").value,
        general_advice: document.getElementById("rxAdvice").value,
        follow_up: document.getElementById("rxFollowUp").value
    };"""

pattern_submit_c = r'async function submitOptionC\(e\) \{[\s\S]*?follow_up:\s*document\.getElementById\("rxFollowUp"\)\.value\s*\};'
content = re.sub(pattern_submit_c, new_submit_c, content)

# 8. Update previewPDF
new_preview_payload = """        if (templateType === "consultation") {
            payload.consultation_type = document.getElementById("consType").value;
            payload.document_date = document.getElementById("consDate").value;
            payload.consultation_time = document.getElementById("consTime")?.value || "";
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
            payload.findings = document.getElementById("consFindings")?.value || "";
            payload.treatment_plan = document.getElementById("consTreatmentPlan").value;
            payload.recommendations = document.getElementById("consRecommendations")?.value || "";
            payload.follow_up = document.getElementById("consFollowUp")?.value || "";
            payload.clinical_notes = document.getElementById("consClinicalNotes").value;
            currentPreviewFileName = `consultation_note_${payload.document_date}.pdf`;

        } else if (templateType === "prescription") {
            payload.document_date = document.getElementById("rxDate").value;
            payload.prescription_time = document.getElementById("rxTime")?.value || "";
            payload.diagnosis = document.getElementById("rxDiagnosis").value;
            payload.medicines = collectMedicinesData();
            payload.clinical_notes = document.getElementById("rxClinicalNotes").value;
            payload.general_advice = document.getElementById("rxAdvice").value;
            payload.follow_up = document.getElementById("rxFollowUp").value;
            currentPreviewFileName = `prescription_${payload.document_date}.pdf`;"""

pattern_preview = r'if \(templateType === "consultation"\) \{[\s\S]*?currentPreviewFileName = `prescription_\$\{payload\.document_date\}\.pdf`;'
content = re.sub(pattern_preview, new_preview_payload, content)

with open(template_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated templates/doctor/patient_workspace.html")
