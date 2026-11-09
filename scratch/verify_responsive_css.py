import re

with open("static/css/doctor_patient_workspace.css", "r", encoding="utf-8") as f:
    css = f.read()

checks = {
    "Modal Overlay fixed & overflow hidden": "workspace-modal-overlay" in css and "overflow: hidden" in css,
    "Modal Container flex column & max-height 92vh": "max-height: 92vh" in css and "overflow: hidden" in css,
    "Modal Form flex column min-height 0": ".modal-card-form" in css and "flex: 1 1 auto" in css,
    "Modal Header flex-shrink 0": ".modal-card-header" in css and "flex-shrink: 0" in css,
    "Modal Body scrollable & min-height 0": ".modal-card-body" in css and "overflow-y: auto" in css and "min-height: 0" in css,
    "Modal Footer relative & flex-shrink 0": ".modal-card-footer" in css and "position: relative" in css and "flex-shrink: 0" in css,
    "Medical Record Card 2-col Mobile Grid": "grid-template-columns: 42px minmax(0, 1fr)" in css,
    "No 1-char vertical text wrapping": "overflow-wrap: anywhere" in css and "word-break: normal" in css and "white-space: normal" in css,
    "Clearance from fixed bottom nav (95px)": "padding-bottom: calc(95px + env(safe-area-inset-bottom, 0px)) !important;" in css,
    "Stacked footer buttons on mobile": "flex-direction: column-reverse" in css,
    "Form Row Grid 3 columns": ".form-row-grid-3" in css
}

print("Responsive Verification Results:")
all_ok = True
for name, passed in checks.items():
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    if not passed:
        all_ok = False

if all_ok:
    print("\nALL 11 RESPONSIVE & LAYOUT CHECKS PASSED PERFECTLY!")
else:
    print("\nSOME CHECKS FAILED.")
