#!/usr/bin/env python3
"""Static validation for the World Painted Blood Wesnoth 1.18 test build.

This catches packaging, chain, basic WML structure, map, coordinate, sound,
and placeholder-audio problems. It does not replace loading the campaign in
Wesnoth or running wmllint/wmlscope from a Wesnoth source checkout.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STEMS = [
    "01_When_the_Stillness_Comes", "02_Cast_the_First_Stone",
    "03_Here_Comes_the_Pain", "04_Show_No_Mercy", "05_At_Dawn_They_Sleep",
    "06_Die_by_the_Sword", "07_You_Against_You", "08_Raining_Blood",
    "09_Unguarded_Instinct", "10_Born_of_Fire", "11_Fictional_Reality",
    "12_Read_Between_the_Lies", "13_Aggressive_Perfector", "14_Ghosts_of_War",
    "15_Tormentor", "16_War_Ensemble", "17_Repentless",
    "18_Eyes_of_the_Insane", "19_Spirit_in_Black", "20_The_Final_Command",
]
REQUIRED_SCENARIOS = [f"{s}.cfg" for s in STEMS]
REQUIRED_MAPS = [f"{s}.map" for s in STEMS]
REQUIRED_MUSIC = [f"{i:02}_Scenario.ogg" for i in range(1, 21)]
REQUIRED_ROOT = ["_main.cfg", "README.md", "CHANGELOG.md", "LICENSE"]

ALLOWED_TERRAINS = {
    "Cer", "Cfr", "Ch", "Chr", "Cud", "Isa", "Isa^Ebn", "Isa^Ii", "Isc",
    "Isr", "Iwc", "Iwo", "Iwo^Vhcr", "Iwr", "Ker", "Kfr", "Kh", "Khr",
    "Kud", "Ql", "Ql^Bp/", "Ql^Bp\\", "Ql^Bp|", "Qlf", "Qxe", "Qxu",
    "Qxu^Bs/", "Qxu^Bs\\", "Qxu^Bs|", "Qxua", "Rb", "Rr", "Rrc", "Sm",
    "Sm^Bsb/", "Sm^Bsb\\", "Sm^Bsb|", "Tb", "Uh", "Uhe", "Ur", "Ur^Br/",
    "Ur^Br\\", "Ur^Br|", "Urb", "Urb^Br|", "Urb^Ebn", "Urb^Edb",
    "Urb^Vhc", "Urb^Vhcr", "Urb^Vu", "Urc", "Uu", "Uu^Edb", "Uu^Ii",
    "Uu^Tf", "Uu^Tfi", "Uu^Vu", "Uu^Vud", "Uue", "Uue^Tf", "Ww",
    "Wwg", "Xoa", "Xoc", "Xoi", "Xom", "Xor", "Xos", "Xot", "Xu",
    "Xuc", "Xue", "Xur", "Xv",
}
VERIFIED_CORE_SOUNDS = {
    "axe.ogg", "bat-flapping.wav", "cave-in.ogg", "claws.ogg",
    "dagger-swish.wav", "explosion.ogg", "fanfare-short.wav", "fire.wav",
    "fuse.ogg", "gold.ogg", "groan.wav", "heal.wav", "hiss-big.wav",
    "hiss.wav", "human-die-1.ogg",
}
IMPASSABLE_PREFIXES = ("X", "Qx", "Ql")
errors: list[str] = []
warnings: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def check_exact_files(folder: str, required: list[str]) -> None:
    directory = ROOT / folder
    if not directory.is_dir():
        fail(f"missing directory: {folder}/")
        return
    found = {p.name for p in directory.iterdir() if p.is_file()}
    missing = [name for name in required if name not in found]
    if missing:
        fail(f"{folder}/ missing: {', '.join(missing)}")


def check_tag_balance(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    stack: list[str] = []
    for match in re.finditer(r"(?m)^\s*\[(/?)([A-Za-z0-9_]+)\]\s*$", text):
        closing, tag = match.groups()
        if not closing:
            stack.append(tag)
        elif not stack:
            fail(f"{path.relative_to(ROOT)}: unexpected closing [/{tag}]")
        else:
            opened = stack.pop()
            if opened != tag:
                fail(
                    f"{path.relative_to(ROOT)}: [/{tag}] closes [{opened}]"
                )
    if stack:
        fail(f"{path.relative_to(ROOT)}: unclosed tags {stack[-8:]}")


def read_map(path: Path) -> list[list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [
        [cell.strip() for cell in line.split(",")]
        for line in lines
        if line.strip() and "=" not in line
    ]
    if not rows:
        fail(f"{path.relative_to(ROOT)}: no map rows")
        return []
    widths = {len(row) for row in rows}
    if len(widths) != 1:
        fail(f"{path.relative_to(ROOT)}: inconsistent row widths {sorted(widths)}")
    for y, row in enumerate(rows, 1):
        for x, cell in enumerate(row, 1):
            terrain = re.sub(r"^\d+\s+", "", cell)
            if terrain not in ALLOWED_TERRAINS:
                fail(f"{path.relative_to(ROOT)}: unknown terrain {terrain} at {x},{y}")
    return rows


def reachable_cells(grid: list[list[str]], start: tuple[int, int]) -> set[tuple[int, int]]:
    if not grid:
        return set()
    height, width = len(grid), len(grid[0])

    def passable(x: int, y: int) -> bool:
        return (
            1 <= x <= width
            and 1 <= y <= height
            and not grid[y - 1][x - 1].startswith(IMPASSABLE_PREFIXES)
        )

    if not passable(*start):
        return set()
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        neighbors += [(1, 1), (-1, 1)] if x % 2 else [(1, -1), (-1, -1)]
        for dx, dy in neighbors:
            nxt = (x + dx, y + dy)
            if nxt not in seen and passable(*nxt):
                seen.add(nxt)
                queue.append(nxt)
    return seen


for filename in REQUIRED_ROOT:
    if not (ROOT / filename).is_file():
        fail(f"missing root file: {filename}")
check_exact_files("scenarios", REQUIRED_SCENARIOS)
check_exact_files("maps", REQUIRED_MAPS)
check_exact_files("music", REQUIRED_MUSIC)

for path in [ROOT / "_main.cfg", ROOT / "utils" / "macros.cfg", ROOT / "units" / "Hunter.cfg"]:
    if path.exists():
        check_tag_balance(path)

hunter_path = ROOT / "units" / "Hunter.cfg"
if hunter_path.exists():
    hunter_text = hunter_path.read_text(encoding="utf-8")
    if "id=WPB Hunter" not in hunter_text or "[base_unit]" not in hunter_text or "id=Ranger" not in hunter_text:
        fail("units/Hunter.cfg must define WPB Hunter by inheriting core Ranger assets")

all_used_sounds: set[str] = set()
map_cache: dict[str, list[list[str]]] = {}

for index, filename in enumerate(REQUIRED_SCENARIOS, 1):
    path = ROOT / "scenarios" / filename
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    check_tag_balance(path)
    stem = filename[:-4]
    expected_next = STEMS[index] if index < 20 else "null"
    expected_map = f"{stem}.map"
    expected_music = f"{index:02}_Scenario.ogg"

    if not re.search(rf"(?m)^\s*id={re.escape(stem)}\s*$", text):
        fail(f"{filename}: scenario id must be {stem}")
    if not re.search(rf"(?m)^\s*next_scenario={re.escape(expected_next)}\s*$", text):
        fail(f"{filename}: next_scenario must be {expected_next}")
    if not re.search(rf"(?m)^\s*map_file={re.escape(expected_map)}\s*$", text):
        fail(f"{filename}: map_file must be {expected_map}")
    if not re.search(rf"\{{SCENARIO_MUSIC\s+{re.escape(expected_music)}\}}", text):
        fail(f"{filename}: music must be {expected_music}")
    if "victory_when_enemies_defeated=no" not in text:
        fail(f"{filename}: custom objectives require victory_when_enemies_defeated=no")

    # Side 1 needs a leader, coordinates, and recruitment in the initial scenario.
    side1 = re.search(r"\[side\](?:(?!\[/side\]).)*?side=1(?:(?!\[/side\]).)*?\[/side\]", text, re.S)
    if not side1:
        fail(f"{filename}: no Side 1 definition")
        continue
    side1_text = side1.group(0)
    start_match = re.search(r"\bx=(\d+)\s*\n\s*y=(\d+)", side1_text)
    if not start_match:
        fail(f"{filename}: Side 1 has no numeric starting coordinate")
        continue
    start = tuple(map(int, start_match.groups()))
    if index == 1 and re.search(r"(?m)^\s*recruit=\s*$", side1_text):
        fail(f"{filename}: the first scenario cannot begin with an empty recruit list")

    # Every explicit bait choice must finish bookkeeping even if the boss is at low HP.
    bait = re.search(r'\[option\]\s*\n\s*label= _ "Use them as bait".*?\[/option\]', text, re.S)
    if not bait:
        fail(f"{filename}: missing explicit rescue-versus-bait choice")
    elif "[harm_unit]" in bait.group(0) and "kill=no" not in bait.group(0):
        fail(f"{filename}: bait harm_unit must use kill=no")

    all_used_sounds.update(re.findall(r"(?m)^\s*name=([^\s]+\.(?:ogg|wav))\s*$", text))

    grid = map_cache.setdefault(expected_map, read_map(ROOT / "maps" / expected_map))
    if grid:
        height, width = len(grid), len(grid[0])
        reachable = reachable_cells(grid, start)
        if not reachable:
            fail(f"{filename}: Side 1 starts on impassable terrain at {start[0]},{start[1]}")
        coords = {
            tuple(map(int, m.groups()))
            for m in re.finditer(r"\bx=(\d+)\s*\n\s*y=(\d+)", text)
        }
        for x, y in sorted(coords):
            if not (1 <= x <= width and 1 <= y <= height):
                fail(f"{filename}: coordinate {x},{y} lies outside {width}x{height} map")
            elif (x, y) not in reachable:
                fail(f"{filename}: scripted coordinate {x},{y} is unreachable from Side 1")

unknown_sounds = sorted(all_used_sounds - VERIFIED_CORE_SOUNDS)
if unknown_sounds:
    fail("unverified sound references: " + ", ".join(unknown_sounds))

ffprobe = shutil.which("ffprobe")
for filename in REQUIRED_MUSIC:
    path = ROOT / "music" / filename
    if not path.exists():
        continue
    if path.stat().st_size < 100:
        fail(f"music/{filename}: placeholder is empty or invalid")
    if ffprobe:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or "vorbis" not in result.stdout.lower():
            fail(f"music/{filename}: ffprobe did not recognize Ogg Vorbis audio")
    else:
        warnings.append("ffprobe not installed; OGG codec validation skipped")
        break

if errors:
    print("VALIDATION FAILED")
    for error in errors:
        print(" -", error)
    if warnings:
        print("WARNINGS")
        for warning in sorted(set(warnings)):
            print(" -", warning)
    sys.exit(1)

print("VALIDATION PASSED")
print(" - exact 20-scenario, 20-map, and 20-music filename sets present")
print(" - scenario IDs, map/music references, and 20-link chain verified")
print(" - WML tag nesting passed lightweight static checks")
print(" - custom-victory safeguards and moral-choice bookkeeping verified")
print(" - all scripted coordinates are on-map and reachable from Side 1")
print(" - terrain codes and mainline/core sound basenames matched the manifests")
print(" - all 20 placeholder tracks are nonempty" + (" and ffprobe-readable Ogg Vorbis" if ffprobe else ""))
if warnings:
    print("WARNINGS")
    for warning in sorted(set(warnings)):
        print(" -", warning)
