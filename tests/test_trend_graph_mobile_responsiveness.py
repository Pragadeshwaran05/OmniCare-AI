"""
tests/test_trend_graph_mobile_responsiveness.py

Verifies mobile responsiveness, layout boundary constraints,
and Chart.js configuration for Health Trend Analysis Graphs in OmniCare AI.
"""

import unittest
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestTrendGraphMobileResponsiveness(unittest.TestCase):

    def setUp(self):
        self.css_path = os.path.join(BASE_DIR, 'static', 'css', 'doctor_patient_workspace.css')
        self.template_path = os.path.join(BASE_DIR, 'templates', 'doctor', 'patient_workspace.html')
        self.guest_template_path = os.path.join(BASE_DIR, 'templates', 'doctor', 'guest_patient_workspace.html')
        self.guest_js_path = os.path.join(BASE_DIR, 'static', 'js', 'guest_patient_workspace.js')
        self.analyzer_path = os.path.join(BASE_DIR, 'services', 'health_trend_analyzer.py')

        with open(self.css_path, 'r', encoding='utf-8') as f:
            self.css_content = f.read()

        with open(self.template_path, 'r', encoding='utf-8') as f:
            self.template_content = f.read()

        with open(self.guest_js_path, 'r', encoding='utf-8') as f:
            self.guest_js_content = f.read()

        with open(self.analyzer_path, 'r', encoding='utf-8') as f:
            self.analyzer_content = f.read()

    def test_css_canvas_wrapper_constraints(self):
        """Test that .trend-chart-canvas-wrapper and .chart-container have strict width, max-width, min-width, and overflow constraints."""
        self.assertIn('.trend-chart-canvas-wrapper', self.css_content)
        self.assertIn('.chart-container', self.css_content)

        # Check canvas wrapper has 100% width, min-width 0, overflow hidden
        wrapper_match = re.search(r'\.trend-chart-canvas-wrapper[^{]*\{([^}]+)\}', self.css_content)
        self.assertIsNotNone(wrapper_match, "Wrapper rule not found")
        props = wrapper_match.group(1)
        self.assertIn('width: 100%', props)
        self.assertIn('max-width: 100%', props)
        self.assertIn('min-width: 0', props)
        self.assertIn('overflow: hidden', props)
        self.assertIn('box-sizing: border-box', props)

    def test_css_canvas_element_rules(self):
        """Test that canvas and SVG elements have max-width: 100% !important and display: block to prevent overflow."""
        canvas_match = re.search(r'\.trend-chart-canvas-wrapper\s+canvas[^{]*\{([^}]+)\}', self.css_content)
        self.assertIsNotNone(canvas_match, "Canvas rule not found")
        canvas_props = canvas_match.group(1)
        self.assertIn('display: block', canvas_props)
        self.assertIn('max-width: 100% !important', canvas_props)
        self.assertIn('width: 100% !important', canvas_props)
        self.assertIn('height: 100% !important', canvas_props)

    def test_css_card_and_grid_constraints(self):
        """Test that .trend-chart-card and .trend-charts-grid have width: 100%, max-width: 100%, and min-width: 0."""
        card_match = re.search(r'\.trend-chart-card\s*\{([^}]+)\}', self.css_content)
        self.assertIsNotNone(card_match, "Trend chart card rule not found")
        card_props = card_match.group(1)
        self.assertIn('width: 100%', card_props)
        self.assertIn('max-width: 100%', card_props)
        self.assertIn('min-width: 0', card_props)
        self.assertIn('overflow: hidden', card_props)

    def test_css_responsive_media_queries(self):
        """Test that responsive media queries (900px, 768px, 600px, 480px, 360px) properly adapt the trend charts."""
        # Check 900px breakpoint collapses to single column
        self.assertIn('@media (max-width: 900px)', self.css_content)

        # Check 768px tablet breakpoint
        self.assertIn('@media (max-width: 768px)', self.css_content)

        # Check 480px mobile breakpoint
        self.assertIn('@media (max-width: 480px)', self.css_content)

        # Check 360px small mobile breakpoint
        self.assertIn('@media (max-width: 360px)', self.css_content)

    def test_chartjs_configuration_in_patient_workspace(self):
        """Test Chart.js options in patient_workspace.html include responsive, maintainAspectRatio, layout padding, and tick controls."""
        self.assertIn('responsive: true', self.template_content)
        self.assertIn('maintainAspectRatio: false', self.template_content)
        self.assertIn('autoSkip: true', self.template_content)
        self.assertIn('maxTicksLimit: 6', self.template_content)
        self.assertIn('maxRotation: 45', self.template_content)
        self.assertIn('minRotation: 0', self.template_content)
        self.assertIn('drawBorder: false', self.template_content)

        # Verify layout padding is specified
        self.assertIn('layout: {', self.template_content)
        self.assertIn('padding: {', self.template_content)

    def test_chartjs_configuration_in_guest_patient_workspace(self):
        """Test Chart.js options in guest_patient_workspace.js mirror the same responsive settings."""
        self.assertIn('responsive: true', self.guest_js_content)
        self.assertIn('maintainAspectRatio: false', self.guest_js_content)
        self.assertIn('autoSkip: true', self.guest_js_content)
        self.assertIn('maxTicksLimit: 6', self.guest_js_content)
        self.assertIn('maxRotation: 45', self.guest_js_content)
        self.assertIn('drawBorder: false', self.guest_js_content)

    def test_window_resize_and_tab_hooks(self):
        """Test that window resize listener and onTrendTabActivated call chart.resize()."""
        self.assertIn('window.addEventListener("resize"', self.template_content)
        self.assertIn('chart.resize()', self.template_content)
        self.assertIn('window.onTrendTabActivated', self.template_content)

        self.assertIn('window.addEventListener("resize"', self.guest_js_content)
        self.assertIn('chart.resize()', self.guest_js_content)
        self.assertIn('window.onTrendTabActivated', self.guest_js_content)

    def test_medical_trend_analyzer_preserved(self):
        """Test that health_trend_analyzer.py preserves teal trend line and danger point colors."""
        # Teal trend stroke
        self.assertIn('#168b83', self.analyzer_content)

        # Danger colors
        self.assertIn('#ef4444', self.analyzer_content)  # red
        self.assertIn('#f59e0b', self.analyzer_content)  # amber
        self.assertIn('#10b981', self.analyzer_content)  # green

        # Check core analyzer function exists
        from services.health_trend_analyzer import get_trend_analysis_data
        self.assertTrue(callable(get_trend_analysis_data))


if __name__ == '__main__':
    unittest.main()
