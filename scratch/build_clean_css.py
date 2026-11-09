import re

css_path = "static/css/doctor_patient_workspace.css"

with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# 1. Fix line 524-560: .record-information h3 & .record-description
css = re.sub(
    r'\.record-information h3 \{[\s\S]*?word-break:\s*break-word;\s*\}',
    '''.record-information h3 {
    margin: 0 0 4px;
    color: #214e6d;
    font-size: 15px;
    font-weight: 800;
    line-height: 1.4;
    white-space: normal;
    word-break: normal;
    overflow-wrap: anywhere;
    min-width: 0;
}''',
    css
)

css = re.sub(
    r'\.record-description \{[\s\S]*?word-break:\s*break-word;\s*\}',
    '''.record-description {
    margin: 0 0 5px;
    color: #778e9e;
    font-size: 12px;
    line-height: 1.5;
    white-space: normal;
    word-break: normal;
    overflow-wrap: anywhere;
    min-width: 0;
}''',
    css
)

# 2. Fix lines 860-880: replace old broken mobile flex layout with responsive 2-column grid
old_mobile_card_pattern = r'\.medical-record-card \{\s*flex-wrap:\s*wrap;\s*align-items:\s*flex-start;\s*padding:\s*15px;\s*\}\s*\.record-information \{\s*width:\s*calc\(100% - 61px\);\s*\}\s*\.view-record-btn \{\s*width:\s*100%;\s*margin-top:\s*4px;\s*\}'
new_mobile_card_css = '''.medical-record-card {
        display: grid;
        grid-template-columns: 42px minmax(0, 1fr);
        column-gap: 12px;
        row-gap: 10px;
        padding: 14px;
        align-items: start;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
    }

    .record-icon {
        grid-column: 1;
        grid-row: 1;
        width: 42px;
        height: 42px;
        font-size: 20px;
        border-radius: 10px;
        align-self: start;
    }

    .record-information {
        grid-column: 2;
        grid-row: 1;
        min-width: 0;
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .record-actions {
        grid-column: 2;
        grid-row: 2;
        width: 100%;
        min-width: 0;
    }

    .view-record-btn {
        width: 100%;
        min-height: 38px;
        padding: 8px 12px;
        font-size: 12.5px;
        box-sizing: border-box;
        text-align: center;
        justify-content: center;
        margin-top: 0;
    }'''

css = re.sub(old_mobile_card_pattern, new_mobile_card_css, css)

# 3. Fix lines 915-927: small mobile
old_small_mobile_pattern = r'\.medical-record-card \{\s*gap:\s*11px;\s*\}\s*\.record-icon \{\s*width:\s*42px;\s*height:\s*42px;\s*font-size:\s*20px;\s*\}'
new_small_mobile_css = '''.medical-record-card {
        grid-template-columns: 38px minmax(0, 1fr);
        column-gap: 10px;
        row-gap: 8px;
        padding: 11px;
    }

    .record-icon {
        width: 38px;
        height: 38px;
        font-size: 18px;
    }'''

css = re.sub(old_small_mobile_pattern, new_small_mobile_css, css)

# 4. In @media (max-width: 850px) ensure patient-workspace-page has padding-bottom
pattern_850_page = r'(@media \(max-width: 850px\) \{\s*\.patient-workspace-page \{)'
css = re.sub(pattern_850_page, r'\1\n        padding-bottom: calc(95px + env(safe-area-inset-bottom, 0px)) !important;', css)

# 5. Build the modal & upload template styles block
modal_styles_block = """

/* ============================================================
   OMNICARE AI — MEDICAL RECORD UPLOAD & TEMPLATES CSS
   ============================================================ */

/* Section Header Actions */
.workspace-section-actions {
    display: flex;
    align-items: center;
    gap: 12px;
}

.btn-primary-action {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
    color: #ffffff;
    font-size: 13.5px;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(15, 118, 110, 0.2);
    transition: all 0.2s ease;
}

.btn-primary-action:hover {
    background: linear-gradient(135deg, #115e59 0%, #0f766e 100%);
    box-shadow: 0 4px 8px rgba(15, 118, 110, 0.3);
    transform: translateY(-1px);
}

.readonly-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #fef3c7;
    color: #92400e;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 20px;
    border: 1px solid #fcd34d;
}

/* Enhanced Record Card Badges */
.record-title-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 6px 10px;
    margin-bottom: 4px;
    min-width: 0;
    width: 100%;
}

.record-title-row h3 {
    margin: 0;
    color: #214e6d;
    font-size: 14.5px;
    font-weight: 700;
    line-height: 1.4;
    white-space: normal;
    word-break: normal;
    overflow-wrap: anywhere;
    min-width: 0;
    flex: 1 1 auto;
}

.record-type-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 6px;
    background: #e2e8f0;
    color: #475569;
    flex-shrink: 0;
    white-space: nowrap;
}

.record-type-badge.prescription {
    background: #dcfce7;
    color: #166534;
}

.record-type-badge.consultation {
    background: #ccfbf1;
    color: #0f766e;
}

.record-type-badge.lab_report,
.record-type-badge.scan_imaging {
    background: #e0e7ff;
    color: #3730a3;
}

.record-type-badge.medical_certificate {
    background: #fef9c3;
    color: #854d0e;
}

.record-type-badge.referral_letter {
    background: #fae8ff;
    color: #86198f;
}

.record-meta-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
    min-width: 0;
    width: 100%;
}

.meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: #475569;
    background: #f1f5f9;
    padding: 3px 8px;
    border-radius: 5px;
    max-width: 100%;
    box-sizing: border-box;
    white-space: normal;
    word-break: normal;
    overflow-wrap: anywhere;
    min-width: 0;
    line-height: 1.35;
}

.new-record-highlight {
    animation: newRecordGlow 2s ease-out;
}

@keyframes newRecordGlow {
    0% { background-color: #f0fdfa; border-color: #0d9488; }
    100% { background-color: #ffffff; }
}

/* Modal Overlay & Base Card */
.workspace-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    background: rgba(15, 23, 42, 0.65);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    z-index: 1050;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    box-sizing: border-box;
    overflow: hidden;
}

.workspace-modal-card {
    background: #ffffff;
    border-radius: 14px;
    width: 100%;
    max-height: 92vh;
    max-height: 92dvh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    animation: modalScaleUp 0.2s ease-out;
    border: 1px solid #e2e8f0;
    overflow: hidden;
    box-sizing: border-box;
    position: relative;
}

.workspace-modal-card > form,
.workspace-modal-card .modal-card-form {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
    width: 100%;
    margin: 0;
    padding: 0;
}

@keyframes modalScaleUp {
    from { opacity: 0; transform: scale(0.96); }
    to { opacity: 1; transform: scale(1); }
}

.modal-card-chooser { max-width: 680px; }
.modal-card-lg { max-width: 760px; }
.modal-card-xl { max-width: 920px; }
.modal-card-preview { max-width: 980px; height: 90vh; }

.modal-card-header {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 22px;
    border-bottom: 1px solid #e2e8f0;
    position: relative;
    background: #fafaf9;
    border-radius: 14px 14px 0 0;
    flex-shrink: 0;
}

.modal-header-icon {
    font-size: 24px;
    line-height: 1;
}

.modal-title {
    font-size: 17px;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 4px 0;
}

.modal-subtitle {
    font-size: 13px;
    color: #64748b;
    margin: 0;
    line-height: 1.4;
}

.modal-close-btn {
    position: absolute;
    top: 16px;
    right: 18px;
    background: transparent;
    border: none;
    font-size: 18px;
    color: #94a3b8;
    cursor: pointer;
    line-height: 1;
    padding: 6px;
    border-radius: 6px;
    transition: background 0.15s, color 0.15s;
}

.modal-close-btn:hover {
    background: #f1f5f9;
    color: #0f172a;
}

.modal-card-body {
    padding: 20px 24px;
    overflow-y: auto;
    overflow-x: hidden;
    flex: 1 1 auto;
    min-height: 0;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
}

.modal-card-body::-webkit-scrollbar {
    width: 6px;
}
.modal-card-body::-webkit-scrollbar-track {
    background: #f1f5f9;
}
.modal-card-body::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 3px;
}
.modal-card-body::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

.modal-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 24px;
    border-top: 1px solid #e2e8f0;
    background: #fafaf9;
    border-radius: 0 0 14px 14px;
    gap: 12px;
    flex-shrink: 0;
    position: relative;
    box-sizing: border-box;
    z-index: 5;
}

.footer-action-buttons {
    display: flex;
    align-items: center;
    gap: 10px;
}

/* Buttons */
.btn-workspace-secondary {
    padding: 8px 16px;
    font-size: 13.5px;
    font-weight: 600;
    color: #475569;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
}

.btn-workspace-secondary:hover {
    background: #e2e8f0;
    color: #1e293b;
}

.btn-workspace-primary {
    padding: 8px 18px;
    font-size: 13.5px;
    font-weight: 600;
    color: #ffffff;
    background: #0f766e;
    border: 1px solid #0f766e;
    border-radius: 8px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    transition: all 0.15s;
}

.btn-workspace-primary:hover {
    background: #0d9488;
}

.btn-workspace-preview {
    padding: 8px 16px;
    font-size: 13.5px;
    font-weight: 600;
    color: #0f766e;
    background: #f0fdfa;
    border: 1.5px solid #0f766e;
    border-radius: 8px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s;
}

.btn-workspace-preview:hover {
    background: #ccfbf1;
}

/* Option Chooser Grid */
.document-action-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
}

.action-choice-card {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px;
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
}

.action-choice-card:hover {
    border-color: #0d9488;
    background: #f0fdfa;
    box-shadow: 0 4px 12px rgba(13, 148, 136, 0.08);
    transform: translateY(-2px);
}

.choice-icon-bubble {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
}

.choice-icon-blue { background: #eff6ff; }
.choice-icon-teal { background: #f0fdfa; }
.choice-icon-emerald { background: #ecfdf5; }
.choice-icon-purple { background: #faf5ff; }

.choice-content {
    flex: 1;
}

.choice-content h4 {
    font-size: 14px;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 4px 0;
}

.choice-content p {
    font-size: 12px;
    color: #64748b;
    margin: 0 0 8px 0;
    line-height: 1.4;
}

.choice-tag {
    display: inline-block;
    font-size: 10.5px;
    font-weight: 600;
    color: #0f766e;
    background: #f0fdfa;
    border: 1px solid #ccfbf1;
    padding: 2px 6px;
    border-radius: 4px;
}

.choice-arrow {
    font-size: 16px;
    color: #94a3b8;
    align-self: center;
    transition: transform 0.15s;
}

.action-choice-card:hover .choice-arrow {
    color: #0d9488;
    transform: translateX(3px);
}

/* Template Context Banner */
.template-context-banner {
    display: flex;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 16px;
    gap: 16px;
}

.banner-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.banner-divider {
    width: 1px;
    background: #e2e8f0;
}

.context-label {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #0f766e;
}

.context-sub {
    font-size: 11.5px;
    color: #64748b;
}

/* Form Styles */
.form-row-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 12px;
}

.form-row-grid-3 {
    display: grid;
    grid-template-columns: 1.2fr 1fr 1fr;
    gap: 14px;
    margin-bottom: 12px;
}

.form-group {
    margin-bottom: 12px;
}

.field-label {
    display: block;
    font-size: 12.5px;
    font-weight: 600;
    color: #334155;
    margin-bottom: 5px;
}

.required-star {
    color: #dc2626;
}

.field-control {
    width: 100%;
    padding: 8px 12px;
    font-size: 13px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    background: #ffffff;
    color: #0f172a;
    box-sizing: border-box;
    transition: border-color 0.15s, box-shadow 0.15s;
    font-family: inherit;
}

.field-control:focus {
    outline: none;
    border-color: #0d9488;
    box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.15);
}

textarea.field-control {
    resize: vertical;
}

/* File Dropzone */
.file-dropzone {
    border: 2px dashed #0d9488;
    background: #f0fdfa;
    border-radius: 10px;
    padding: 24px 16px;
    text-align: center;
    cursor: pointer;
    margin-bottom: 16px;
    transition: background 0.15s;
}

.file-dropzone:hover {
    background: #e6fffa;
}

.dropzone-icon {
    font-size: 32px;
    margin-bottom: 6px;
}

.dropzone-title {
    font-size: 14px;
    font-weight: 600;
    color: #0f766e;
    margin: 0 0 4px 0;
}

.dropzone-hint {
    font-size: 12px;
    color: #64748b;
    margin: 0;
}

.dropzone-file-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    background: #ffffff;
    padding: 10px 16px;
    border-radius: 8px;
    border: 1px solid #cbd5e1;
    max-width: 400px;
    margin: 0 auto;
}

.file-details {
    display: flex;
    flex-direction: column;
    text-align: left;
}

.file-details strong {
    font-size: 13px;
    color: #0f172a;
}

.file-details span {
    font-size: 11px;
    color: #64748b;
}

.btn-remove-file {
    background: #f1f5f9;
    border: none;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    cursor: pointer;
    font-size: 12px;
    color: #64748b;
}

.btn-remove-file:hover {
    background: #fee2e2;
    color: #ef4444;
}

/* Vitals Grid */
.section-subheading {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin: 14px 0 8px 0;
    font-size: 13.5px;
    font-weight: 700;
    color: #0f766e;
}

.subheading-hint {
    font-size: 11.5px;
    font-weight: 400;
    color: #64748b;
}

.vitals-input-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    background: #f8fafc;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
}

.vitals-cell {
    display: flex;
    flex-direction: column;
}

.vital-label {
    font-size: 11px;
    font-weight: 600;
    color: #475569;
    margin-bottom: 3px;
}

.vital-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
}

.vital-field {
    padding-right: 36px !important;
    font-size: 12.5px;
}

.vital-unit {
    position: absolute;
    right: 8px;
    font-size: 10.5px;
    color: #94a3b8;
    pointer-events: none;
}

/* Prescription Medicine Builder */
.medicine-builder-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 16px 0 10px 0;
    padding-bottom: 8px;
    border-bottom: 1.5px solid #e2e8f0;
}

.medicine-builder-title {
    font-size: 14px;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
}

.medicine-builder-subtitle {
    font-size: 12px;
    color: #64748b;
    margin: 2px 0 0 0;
}

.btn-add-medicine {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #f0fdfa;
    color: #0f766e;
    border: 1.5px solid #0d9488;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
}

.btn-add-medicine:hover {
    background: #ccfbf1;
}

.medicine-rows-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.medicine-item-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: border-color 0.15s;
}

.medicine-item-card:hover {
    border-color: #cbd5e1;
}

.med-item-top {
    display: flex;
    align-items: center;
    gap: 10px;
}

.med-num-badge {
    font-size: 11px;
    font-weight: 700;
    color: #0f766e;
    background: #ccfbf1;
    padding: 4px 8px;
    border-radius: 6px;
}

.med-field-name {
    flex: 2;
}

.med-field-type {
    flex: 1.1;
    min-width: 105px;
}

.med-field-strength {
    flex: 1;
    min-width: 100px;
}

.med-field-dosage {
    flex: 1;
    min-width: 95px;
}

.btn-remove-med-row {
    background: #fee2e2;
    color: #ef4444;
    border: none;
    border-radius: 6px;
    width: 32px;
    height: 32px;
    font-size: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
}

.btn-remove-med-row:hover {
    background: #fecaca;
}

.med-item-bottom {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

/* Horizontal Timing Chips */
.timing-chips-group {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}

.timing-label {
    font-size: 11.5px;
    font-weight: 600;
    color: #475569;
}

.timing-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 600;
    color: #475569;
    cursor: pointer;
    user-select: none;
    transition: all 0.15s;
}

.timing-pill.active {
    background: #0f766e;
    border-color: #0f766e;
    color: #ffffff;
}

.timing-pill input[type="checkbox"] {
    accent-color: #0f766e;
    margin: 0;
    cursor: pointer;
}

.timing-pill.active input[type="checkbox"] {
    accent-color: #ffffff;
}

.med-meta-fields {
    display: grid;
    grid-template-columns: 1.2fr 1.2fr 1fr 1.6fr;
    gap: 8px;
}

/* PDF Preview Modal Frame */
.modal-card-preview .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.preview-title-block {
    display: flex;
    align-items: center;
    gap: 10px;
}

.preview-badge-pill {
    font-size: 10px;
    font-weight: 800;
    color: #0f766e;
    background: #ccfbf1;
    padding: 3px 6px;
    border-radius: 4px;
}

.preview-header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
}

.btn-preview-download {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    font-size: 12.5px;
    font-weight: 600;
    background: #0f766e;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.btn-preview-download:hover {
    background: #0d9488;
}

.iframe-container {
    width: 100%;
    height: 100%;
    min-height: 520px;
    background: #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
}

.pdf-viewer-frame {
    width: 100%;
    height: 100%;
    min-height: 520px;
    border: none;
}

.preview-disclaimer {
    font-size: 11.5px;
    color: #64748b;
}

/* Toast */
.workspace-toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 1200;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    opacity: 0;
    transform: translateY(12px);
    transition: opacity 0.2s, transform 0.2s;
    pointer-events: none;
}

.workspace-toast.toast-visible {
    opacity: 1;
    transform: translateY(0);
}

.toast-success { background: #0f766e; }
.toast-error { background: #dc2626; }

/* Responsive Media Queries */
@media (max-width: 768px) {
    .patient-workspace-page {
        padding-bottom: calc(95px + env(safe-area-inset-bottom, 0px)) !important;
    }

    .workspace-section-header {
        flex-direction: column;
        align-items: stretch;
        gap: 12px;
    }

    .workspace-section-actions {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
    }

    .btn-primary-action {
        width: 100%;
        justify-content: center;
        box-sizing: border-box;
    }

    .document-action-grid {
        grid-template-columns: 1fr;
    }

    .form-row-grid,
    .form-row-grid-3 {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .vitals-input-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .workspace-modal-overlay {
        padding: 10px;
        align-items: center;
    }

    .workspace-modal-card {
        width: 100%;
        max-width: calc(100vw - 20px);
        max-height: 95vh;
        max-height: 95dvh;
        border-radius: 12px;
    }

    .modal-card-header {
        padding: 14px 16px;
        border-radius: 12px 12px 0 0;
    }

    .modal-header-icon {
        font-size: 20px;
    }

    .modal-title {
        font-size: 15.5px;
    }

    .modal-subtitle {
        font-size: 11.5px;
    }

    .modal-card-body {
        padding: 14px 16px;
    }

    .med-item-top {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
    }

    .med-num-badge {
        flex: 0 0 auto;
    }

    .med-field-name {
        flex: 1 1 calc(100% - 85px);
        min-width: 130px;
    }

    .btn-remove-med-row {
        flex: 0 0 32px;
        margin-left: auto;
    }

    .med-field-type {
        flex: 1 1 calc(50% - 6px);
        min-width: 110px;
    }

    .med-field-strength {
        flex: 1 1 calc(50% - 6px);
        min-width: 110px;
    }

    .med-field-dosage {
        flex: 1 1 100%;
    }

    .med-meta-fields {
        grid-template-columns: 1fr 1fr;
    }

    .template-context-banner {
        flex-direction: column;
        gap: 10px;
    }

    .banner-divider {
        width: 100%;
        height: 1px;
    }

    .modal-card-footer {
        flex-direction: column-reverse;
        align-items: stretch;
        padding: 12px 16px;
        border-radius: 0 0 12px 12px;
        gap: 8px;
    }

    .footer-action-buttons {
        flex-direction: column;
        width: 100%;
        gap: 8px;
    }

    .btn-workspace-secondary,
    .btn-workspace-preview,
    .btn-workspace-primary {
        width: 100%;
        justify-content: center;
        min-height: 40px;
        box-sizing: border-box;
    }
}

@media (max-width: 480px) {
    .vitals-input-grid {
        grid-template-columns: 1fr;
    }

    .med-meta-fields {
        grid-template-columns: 1fr;
    }

    .med-field-type,
    .med-field-strength {
        flex: 1 1 100%;
    }
}
"""

final_css = css.rstrip() + "\n" + modal_styles_block.lstrip()

with open(css_path, "w", encoding="utf-8") as f:
    f.write(final_css)

print("Successfully wrote updated CSS! Total chars:", len(final_css))
