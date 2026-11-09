import re

css_path = "static/css/doctor_patient_workspace.css"

with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# 1. Update lines around 524-560: .record-information h3, .record-description
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

# 2. Update lines around 860-880: replace old broken mobile .medical-record-card flex layout with 2-column Grid
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

# 3. Update @media (max-width: 400px) block around lines 915-927
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

# 4. In @media (max-width: 850px) ensure patient-workspace-page has padding-bottom: 95px !important
if ".patient-workspace-page {" in css:
    # Check if patient-workspace-page inside media query already has padding-bottom
    pattern_850_page = r'(@media \(max-width: 850px\) \{\s*\.patient-workspace-page \{)'
    css = re.sub(pattern_850_page, r'\1\n        padding-bottom: calc(95px + env(safe-area-inset-bottom, 0px)) !important;', css)

# 5. Update .record-title-row and .meta-chip (around lines 5134-5197)
pattern_title_row = r'\.record-title-row \{[\s\S]*?margin-bottom:\s*4px;\s*\}'
new_title_row = '''.record-title-row {
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
}'''
css = re.sub(pattern_title_row, new_title_row, css)

pattern_meta_chip = r'\.meta-chip \{[\s\S]*?border-radius:\s*4px;\s*\}'
new_meta_chip = '''.meta-chip {
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
}'''
css = re.sub(pattern_meta_chip, new_meta_chip, css)

# 6. Update Modal Overlay, Card, Form, Header, Body, Footer (around lines 5208-5312)
pattern_modal_base = r'/\* Modal Overlay & Base Card \*/[\s\S]*?/\* Buttons \*/'
new_modal_base = """/* Modal Overlay & Base Card */
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

/* Buttons */"""
css = re.sub(pattern_modal_base, new_modal_base, css)

# 7. Add .form-row-grid-3 and style .med-field-type, .med-field-strength
pattern_form_grid = r'\.form-row-grid \{\s*display:\s*grid;\s*grid-template-columns:\s*1fr 1fr;\s*gap:\s*14px;\s*margin-bottom:\s*12px;\s*\}'
new_form_grid = '''.form-row-grid {
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
}'''
css = re.sub(pattern_form_grid, new_form_grid, css)

pattern_med_fields = r'(\.med-field-dosage \{\s*flex:\s*1;\s*\})'
new_med_fields = '''\\1

.med-field-type {
    flex: 1.1;
    min-width: 105px;
}

.med-field-strength {
    flex: 1;
    min-width: 100px;
}'''
css = re.sub(pattern_med_fields, new_med_fields, css)

# 8. Update mobile media query @media (max-width: 768px) and @media (max-width: 480px)
pattern_mobile = r'@media \(max-width: 768px\) \{[\s\S]*?@media \(max-width: 480px\) \{[\s\S]*?\}\s*\}'
new_mobile = """@media (max-width: 768px) {
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
}"""
css = re.sub(pattern_mobile, new_mobile, css)

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)

print("Successfully updated static/css/doctor_patient_workspace.css")
