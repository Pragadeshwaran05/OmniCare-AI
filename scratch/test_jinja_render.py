import jinja2

env = jinja2.Environment()
s = """const qrIdentifier = {{ qr_identifier|tojson if qr_identifier else (patient.get('id')|tojson) }};
const patientId = {{ patient.get('id')|tojson }};
const msg91WidgetId = {{ msg91_widget_id|tojson if msg91_widget_id else '""' }};
const msg91TokenAuth = {{ msg91_token_auth|tojson if msg91_token_auth else '""' }};
"""

try:
    t = env.from_string(s)
    out = t.render(qr_identifier="OMC-QR-1234", patient={"id": "uuid-5678"}, msg91_widget_id=None, msg91_token_auth=None)
    print("Rendered with None:")
    print(out)
    out2 = t.render(qr_identifier="", patient={"id": "uuid-5678"}, msg91_widget_id="", msg91_token_auth="")
    print("Rendered with empty:")
    print(out2)
except Exception as e:
    print("Error:", repr(e))
