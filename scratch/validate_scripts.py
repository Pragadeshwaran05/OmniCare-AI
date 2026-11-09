import re, subprocess

def check_html(filename):
    print(f"\n--- Checking {filename} ---")
    with open(filename, "r", encoding="utf-8") as f:
        html = f.read()

    # Find inline scripts
    scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
    print(f"Found {len(scripts)} inline script blocks.")

    for i, s in enumerate(scripts):
        s_file = f"scratch/test_script_{i}.js"
        with open(s_file, "w", encoding="utf-8") as sf:
            sf.write(s)
        res = subprocess.run(["node", "--check", s_file], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[ERROR] Script {i} has syntax errors:")
            print(res.stderr)
        else:
            print(f"[OK] Script {i} is valid JavaScript.")

check_html("scratch/rendered_public.html")
check_html("scratch/rendered_doc_access.html")
