#!/usr/bin/env python3
"""Validate the offline TRoW developer-reference site."""

from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_root", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    root = args.site_root.resolve()

    html_files = sorted(root.rglob("*.html"))
    href_re = re.compile(r'href="([^"]+)"')
    broken: list[dict] = []
    titles: list[str] = []
    external_runtime: list[dict] = []

    for path in html_files:
        text = path.read_text(encoding="utf-8")
        title_match = re.search(r"<title>(.*?)</title>", text, flags=re.S)
        titles.append(clean_text(title_match.group(1)) if title_match else "")

        for href in href_re.findall(text):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            local = href.split("#", 1)[0].split("?", 1)[0]
            if not local:
                continue
            target = (path.parent / local).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                broken.append({"page": str(path.relative_to(root)), "href": href, "reason": "outside root"})
                continue
            if not target.exists():
                broken.append({"page": str(path.relative_to(root)), "href": href, "reason": "missing"})

        for tag in re.findall(r"<(?:script|link)\b[^>]+>", text, flags=re.I):
            match = re.search(r'(?:src|href)="(https?://[^"]+)"', tag)
            if match:
                external_runtime.append({
                    "page": str(path.relative_to(root)),
                    "url": match.group(1),
                })

    duplicate_titles = sorted(
        {title for title in titles if title and titles.count(title) > 1}
    )

    search_index = root / "assets/search-index.js"
    search_entries = None
    if search_index.exists():
        raw = search_index.read_text(encoding="utf-8").strip()
        prefix = "window.TROW_SEARCH_INDEX="
        if raw.startswith(prefix):
            search_entries = len(json.loads(raw[len(prefix):].rstrip(";\n")))

    required = [
        "assets/audit-report.json",
        "assets/campaign-metadata.json",
        "assets/state-lifecycle.json",
        "assets/unit-core-closure.json",
        "assets/inherited-unit-audio.json",
        "assets/source-snapshot.json",
        "tools/trow_unit_dependency_audit.py",
        "tools/validate_reference.py",
    ]
    missing_required = [item for item in required if not (root / item).exists()]

    report = {
        "html_pages": len(html_files),
        "search_entries": search_entries,
        "broken_links": broken,
        "duplicate_titles": duplicate_titles,
        "external_runtime_dependencies": external_runtime,
        "missing_required_files": missing_required,
    }
    report["ok"] = (
        not broken
        and not duplicate_titles
        and not external_runtime
        and not missing_required
        and search_entries == len(html_files)
    )

    print(json.dumps(report, indent=2))
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
