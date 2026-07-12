#!/usr/bin/env python3
"""Generate the TRoW campaign-unit dependency and audio closure.

This is a bounded WML source analyser, not a complete Wesnoth preprocessor.
It scans:
  * data/campaigns/The_Rise_Of_Wesnoth/units
  * campaign utilities for macro definitions
  * data/core/macros
  * core unit files reached through [base_unit]

It resolves macro calls transitively and expands numeric sound ranges such as
human-hit-[1~5].ogg.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

MACRO_CALL_RE = re.compile(r"\{([A-Z][A-Z0-9_:.-]+)")
AUDIO_RE = re.compile(r"[A-Za-z0-9_./~-]+(?:\[[^\]]+\])?\.(?:ogg|wav)")
DEFINE_RE = re.compile(
    r"(?ms)^#define[ \t]+([^\s]+)([^\n]*)\n(.*?)^#enddef[ \t]*$"
)
UNIT_BLOCK_RE = re.compile(r"(?ms)\[unit_type\](.*?)\[/unit_type\]")


def macro_calls(text: str) -> set[str]:
    return set(MACRO_CALL_RE.findall(text))


def expand_numeric_pattern(value: str) -> list[str]:
    parts: list[str] = []
    current = ""
    depth = 0
    for char in value:
        if char == "[":
            depth += 1
        elif char == "]":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            if current.strip():
                parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())

    expanded: list[str] = []
    for part in parts:
        match = re.search(r"\[(\d+)~(\d+)\]", part)
        if not match:
            expanded.append(part)
            continue
        start, end = map(int, match.groups())
        step = 1 if end >= start else -1
        for number in range(start, end + step, step):
            expanded.append(part[: match.start()] + str(number) + part[match.end() :])
    return expanded


def parse_macro_definitions(files: Iterable[Path], root: Path) -> dict[str, dict]:
    definitions: dict[str, dict] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in DEFINE_RE.finditer(text):
            name, header, body = match.groups()
            definitions[name] = {
                "header": header.strip(),
                "body": body.strip(),
                "source": path.relative_to(root).as_posix(),
            }
    return definitions


def build_core_unit_index(core_units: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in core_units.rglob("*.cfg"):
        text = path.read_text(encoding="utf-8")
        for block in UNIT_BLOCK_RE.findall(text):
            match = re.search(r"(?m)^\s*id\s*=\s*(.+?)\s*$", block)
            if match:
                index[match.group(1).strip()] = path
    return index


def git_commit(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wesnoth-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.wesnoth_root.resolve()
    campaign = root / "data/campaigns/The_Rise_Of_Wesnoth"
    campaign_units = campaign / "units"
    campaign_utils = campaign / "utils"
    core_units = root / "data/core/units"
    core_macros = root / "data/core/macros"

    required = [campaign_units, campaign_utils, core_units, core_macros]
    missing = [str(path) for path in required if not path.is_dir()]
    if missing:
        parser.error("Missing directories: " + ", ".join(missing))

    macro_files = list(core_macros.glob("*.cfg")) + list(campaign_utils.glob("*.cfg"))
    definitions = parse_macro_definitions(macro_files, root)
    core_index = build_core_unit_index(core_units)

    sound_lists: dict[str, list[str]] = {}
    for name, definition in definitions.items():
        if name.startswith("SOUND_LIST:"):
            values: set[str] = set()
            for token in AUDIO_RE.findall(definition["body"]):
                values.update(expand_numeric_pattern(token))
            sound_lists[name] = sorted(values)

    report = {
        "repository_root": str(root),
        "commit": git_commit(root),
        "scope": (
            "Campaign-defined unit files plus recursively reached core base units "
            "and macro definitions."
        ),
        "units": {},
    }

    for path in sorted(campaign_units.glob("*.cfg")):
        text = path.read_text(encoding="utf-8")
        id_match = re.search(r"(?m)^\s*id\s*=\s*(.+?)\s*$", text)
        unit_id = id_match.group(1).strip() if id_match else path.stem

        bases = [
            value.strip()
            for value in re.findall(
                r"(?ms)\[base_unit\].*?^\s*id\s*=\s*(.+?)\s*$.*?\[/base_unit\]",
                text,
            )
        ]
        sources = [path]
        missing_bases: list[str] = []
        for base in bases:
            core_path = core_index.get(base)
            if core_path:
                sources.append(core_path)
            else:
                missing_bases.append(base)

        roots: set[str] = set()
        literal_patterns: set[str] = set()
        for source in sources:
            source_text = source.read_text(encoding="utf-8")
            roots.update(macro_calls(source_text))
            literal_patterns.update(AUDIO_RE.findall(source_text))

        seen: set[str] = set()
        unresolved: set[str] = set()
        edges: set[tuple[str, str]] = set()
        stack = list(roots)
        while stack:
            symbol = stack.pop()
            if symbol in seen:
                continue
            seen.add(symbol)
            definition = definitions.get(symbol)
            if not definition:
                unresolved.add(symbol)
                continue
            parameter_names = set(
                re.findall(r"[A-Z][A-Z0-9_]*", definition["header"])
            )
            children = macro_calls(definition["body"]) - parameter_names
            for child in children:
                edges.add((symbol, child))
                if child not in seen:
                    stack.append(child)

        direct_audio: set[str] = set()
        for pattern in literal_patterns:
            direct_audio.update(expand_numeric_pattern(pattern))
        expanded_audio = set(direct_audio)
        used_sound_lists = sorted(symbol for symbol in seen if symbol in sound_lists)
        for symbol in used_sound_lists:
            expanded_audio.update(sound_lists[symbol])

        report["units"][unit_id] = {
            "campaign_source": path.relative_to(root).as_posix(),
            "source_files": [source.relative_to(root).as_posix() for source in sources],
            "base_units": bases,
            "missing_base_units": missing_bases,
            "root_symbols": sorted(roots),
            "resolved_symbols": sorted(symbol for symbol in seen if symbol in definitions),
            "unresolved_symbols": sorted(unresolved),
            "macro_edges": [list(edge) for edge in sorted(edges)],
            "direct_audio_patterns": sorted(literal_patterns),
            "sound_list_macros": used_sound_lists,
            "expanded_audio": sorted(expanded_audio),
        }

    all_unresolved = sorted(
        {
            symbol
            for unit in report["units"].values()
            for symbol in unit["unresolved_symbols"]
        }
    )
    all_audio = sorted(
        {
            filename
            for unit in report["units"].values()
            for filename in unit["expanded_audio"]
        }
    )
    all_symbols = sorted(
        {
            symbol
            for unit in report["units"].values()
            for symbol in unit["resolved_symbols"]
        }
    )
    report["global"] = {
        "campaign_unit_files": len(report["units"]),
        "resolved_symbols": len(all_symbols),
        "resolved_symbol_names": all_symbols,
        "unresolved_symbols": all_unresolved,
        "unique_expanded_audio": len(all_audio),
        "expanded_audio": all_audio,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["global"], indent=2))

    if args.strict and (
        all_unresolved
        or any(unit["missing_base_units"] for unit in report["units"].values())
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
