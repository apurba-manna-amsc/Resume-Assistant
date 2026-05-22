from pathlib import Path

root = Path(__file__).resolve().parents[1]
lines = (root / "streamlit_app.py").read_text(encoding="utf-8").splitlines()

def find(name):
    return next(i for i, l in enumerate(lines) if f"def {name}" in l)

ns = find("normalize_certification_entry")
ne = find("render_resume_form_editor")
rs = find("render_resume_form_editor")
re = find("_is_placeholder_resume")

header = '''"""Streamlit form editor for resume JSON sections."""

from typing import Any, Dict

import streamlit as st


'''
norm = [l[4:] if l.startswith("    ") else l for l in lines[ns + 1 : ne]]
body = []
for l in lines[rs:re]:
    if l.strip().startswith("def render_resume_form_editor"):
        body.append("def render_resume_form_editor(resume_data: Dict[str, Any]) -> Dict[str, Any]:")
        continue
    line = l[4:] if l.startswith("    ") else l
    line = line.replace("self.normalize_certification_entry", "normalize_certification_entry")
    body.append(line)

out = root / "resume_assistant/ui/components/resume_editor.py"
out.write_text(header + "\n".join(norm) + "\n\n" + "\n".join(body) + "\n", encoding="utf-8")
print("Wrote", out)
