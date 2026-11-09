import jinja2

env = jinja2.Environment(autoescape=True)
tmpl = env.from_string("""
case 1: {{ msg91_widget_id|tojson if msg91_widget_id else '""' }}
case 2: {{ (msg91_widget_id or "")|tojson|safe }}
""")

print(tmpl.render(msg91_widget_id=""))
print(tmpl.render(msg91_widget_id=None))
print(tmpl.render(msg91_widget_id="widget_123"))
