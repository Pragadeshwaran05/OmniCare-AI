import os
import re
import unittest

class TestPrescriptionBuilderLayeringAndLayout(unittest.TestCase):
    """
    Automated test suite verifying the Prescription Builder modal layout fixes:
    - Layering & z-index above the fixed doctor sidebar (sidebar z-index 1250 vs overlay 99999 vs card 100000)
    - Viewport centering & margin: auto
    - Modal body independent scrolling with min-height: 0
    - Sticky accessible modal header and footer
    - Desktop two-column layout (form + live PDF preview)
    - Mobile stacked layout (1fr)
    - Background scroll locking (modal-open-lock)
    - Backdrop click & Escape key dismissal
    - Doctor patient workspace modal layering
    """

    def setUp(self):
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.sidebar_css_path = os.path.join(self.base_dir, "static", "css", "doctor_sidebar.css")
        self.consultations_css_path = os.path.join(self.base_dir, "static", "css", "doctor_consultations.css")
        self.workspace_css_path = os.path.join(self.base_dir, "static", "css", "doctor_patient_workspace.css")
        self.consultations_js_path = os.path.join(self.base_dir, "static", "js", "doctor_consultations.js")
        self.consultations_html_path = os.path.join(self.base_dir, "templates", "doctor", "doctor_consultations.html")
        self.workspace_html_path = os.path.join(self.base_dir, "templates", "doctor", "patient_workspace.html")

    def test_01_sidebar_z_index_documented(self):
        """Verify the doctor sidebar z-index values in doctor_sidebar.css."""
        with open(self.sidebar_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Sidebar has z-index: 1250
        self.assertIn("1250", content)
        self.assertIn(".doctor-sidebar", content)

    def test_02_consultations_modal_overlay_z_index_and_layering(self):
        """Verify .consultations-modal-overlay is position: fixed and z-index >= 99999 above sidebar."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        overlay_match = re.search(r"\.consultations-modal-overlay\s*\{([^}]+)\}", content)
        self.assertIsNotNone(overlay_match, ".consultations-modal-overlay rule must exist in doctor_consultations.css")
        rules = overlay_match.group(1)

        self.assertIn("position: fixed", rules)
        self.assertIn("99999", rules, "Modal overlay must have z-index >= 99999 to render above sidebar (1250)")
        self.assertIn("backdrop-filter", rules)
        self.assertIn("align-items: center", rules)
        self.assertIn("justify-content: center", rules)

    def test_03_consultations_modal_card_layering_and_centering(self):
        """Verify .consultations-modal-card has z-index: 100000, margin: auto, and max-height constraints."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        card_match = re.search(r"\.consultations-modal-card\s*\{([^}]+)\}", content)
        self.assertIsNotNone(card_match, ".consultations-modal-card rule must exist")
        rules = card_match.group(1)

        self.assertIn("100000", rules, "Modal card container must have z-index: 100000")
        self.assertIn("margin: auto", rules, "Modal card container must have margin: auto for viewport centering")
        self.assertIn("max-height", rules)
        self.assertIn("flex-direction: column", rules)
        self.assertIn("overflow: hidden", rules)

    def test_04_wide_prescription_modal_dimensions(self):
        """Verify .consultations-modal-card.modal-wide-prescription width accommodates two panels."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(".consultations-modal-card.modal-wide-prescription", content)
        self.assertIn("1240px", content, "Wide prescription modal should have max-width: 1240px")

    def test_05_sticky_modal_header_and_footer(self):
        """Verify .modal-header and .modal-footer are sticky with flex-shrink: 0."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        header_match = re.search(r"\.modal-header\s*\{([^}]+)\}", content)
        self.assertIsNotNone(header_match)
        header_rules = header_match.group(1)
        self.assertIn("position: sticky", header_rules)
        self.assertIn("top: 0", header_rules)
        self.assertIn("flex-shrink: 0", header_rules)

        footer_match = re.search(r"\.modal-footer\s*\{([^}]+)\}", content)
        self.assertIsNotNone(footer_match)
        footer_rules = footer_match.group(1)
        self.assertIn("position: sticky", footer_rules)
        self.assertIn("bottom: 0", footer_rules)
        self.assertIn("flex-shrink: 0", footer_rules)

    def test_06_scrollable_modal_body(self):
        """Verify .modal-body is independently scrollable with overflow-y: auto and min-height: 0."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        body_match = re.search(r"\.modal-body\s*\{([^}]+)\}", content)
        self.assertIsNotNone(body_match)
        body_rules = body_match.group(1)
        self.assertIn("overflow-y: auto", body_rules)
        self.assertIn("min-height: 0", body_rules)
        self.assertIn("flex: 1 1 auto", body_rules)

    def test_07_desktop_two_column_prescription_grid(self):
        """Verify .prescription-two-panel-grid defines two-column grid on desktop."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        grid_match = re.search(r"\.prescription-two-panel-grid\s*\{([^}]+)\}", content)
        self.assertIsNotNone(grid_match)
        grid_rules = grid_match.group(1)
        self.assertIn("display: grid", grid_rules)
        self.assertIn("1.15fr", grid_rules)
        self.assertIn("0.85fr", grid_rules)
        self.assertIn("min-width: 0", grid_rules)

    def test_08_mobile_stacked_prescription_grid(self):
        """Verify responsive media queries stack prescription-two-panel-grid to 1 column on mobile/tablet."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        # At max-width: 992px, grid becomes 1 column
        self.assertIn("@media (max-width: 992px)", content)
        mobile_section = content[content.find("@media (max-width: 992px)"):]
        self.assertIn(".prescription-two-panel-grid", mobile_section)
        self.assertIn("grid-template-columns: 1fr", mobile_section)

    def test_09_background_scroll_lock_css(self):
        """Verify body.modal-open-lock and html.modal-open-lock prevent background scrolling."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("body.modal-open-lock", content)
        self.assertIn("html.modal-open-lock", content)
        self.assertIn("overflow: hidden !important;", content)

    def test_10_js_modal_open_and_close_lock_handling(self):
        """Verify doctor_consultations.js adds and removes modal-open-lock class."""
        with open(self.consultations_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("lockModalScroll", content)
        self.assertIn("unlockModalScroll", content)
        self.assertIn("modal-open-lock", content)
        self.assertIn("openPrescriptionModal", content)
        self.assertIn("closePrescriptionModal", content)

    def test_11_js_escape_key_and_backdrop_dismissal(self):
        """Verify doctor_consultations.js has Escape key and backdrop click dismissal."""
        with open(self.consultations_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('e.key === "Escape"', content)
        self.assertIn("consultations-modal-overlay", content)
        self.assertIn("e.target === overlay", content)

    def test_12_toast_z_index_above_modal(self):
        """Verify .consultations-toast has z-index: 100001 to appear above modal card (100000)."""
        with open(self.consultations_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        toast_match = re.search(r"\.consultations-toast\s*\{([^}]+)\}", content)
        self.assertIsNotNone(toast_match)
        toast_rules = toast_match.group(1)
        self.assertIn("100001", toast_rules)

    def test_13_workspace_modal_layering_and_centering(self):
        """Verify doctor_patient_workspace.css modal overlay has z-index: 99999 and card has z-index: 100000."""
        with open(self.workspace_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(".workspace-modal-overlay", content)
        self.assertIn("99999", content)
        self.assertIn(".workspace-modal-card", content)
        self.assertIn("100000", content)
        self.assertIn("margin: auto", content)

    def test_14_patient_workspace_html_scroll_lock_and_backdrop(self):
        """Verify templates/doctor/patient_workspace.html toggles modal-open-lock and backdrop click."""
        with open(self.workspace_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("modal-open-lock", content)
        self.assertIn("openOptionModal", content)
        self.assertIn("closeWorkspaceModal", content)
        self.assertIn("workspace-modal-overlay", content)

    def test_15_prescription_html_modal_structure(self):
        """Verify prescriptionModal exists with correct classes in doctor_consultations.html."""
        with open(self.consultations_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('id="prescriptionModal"', content)
        self.assertIn('class="consultations-modal-overlay"', content)
        self.assertIn('class="consultations-modal-card modal-wide-prescription"', content)
        self.assertIn('class="prescription-two-panel-grid"', content)
        self.assertIn('class="prescription-form-panel"', content)
        self.assertIn('class="prescription-preview-panel"', content)
        self.assertIn('id="prescriptionLiveIframe"', content)
        self.assertIn('onclick="closePrescriptionModal()"', content)

if __name__ == "__main__":
    unittest.main()
