#!/usr/bin/env python3
"""Validate repository-relative Markdown references without network access."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
errors = []
files = list(root.glob("*.md")) + list((root / "docs").rglob("*.md"))
for path in files:
    content = path.read_text(encoding="utf-8")
    if "\ufffd" in content:
        errors.append(f"{path.relative_to(root)}: replacement character")
    for link in re.findall(r"\]\(([^)]+)\)", content):
        target = link.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (path.parent / unquote(target)).exists():
            errors.append(f"{path.relative_to(root)}: missing {target}")
for name in ["README.md", "docs/README.md", "docs/product.md", "docs/architecture.md",
             "docs/tablet-ux.md", "docs/development.md", "docs/decisions.md", "ROADMAP.md"]:
    if not (root / name).is_file():
        errors.append(f"Missing required reading: {name}")
if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"Validated UTF-8 and relative links in {len(files)} documents")
