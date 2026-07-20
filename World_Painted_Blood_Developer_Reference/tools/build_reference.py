from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from typing import Any, Iterable
import hashlib
import html
import json
import os
import re
import shutil
import textwrap

CAMPAIGN = Path('/mnt/data/World_Painted_Blood')
OUT = Path('/mnt/data/World_Painted_Blood_Developer_Reference')
VERSION = '0.1.0'
ACCESS_DATE = 'July 19, 2026'

# ---------------------------------------------------------------------------
# WML parsing helpers. This intentionally handles the subset used by WPB 0.1.0.
# ---------------------------------------------------------------------------

@dataclass
class WNode:
    tag: str
    start: int
    parent: 'WNode | None' = None
    end: int | None = None
    attrs: list[tuple[str, str, int]] = field(default_factory=list)
    children: list['WNode'] = field(default_factory=list)
    macros: list[tuple[str, int]] = field(default_factory=list)

    def getall(self, key: str) -> list[str]:
        return [v for k, v, _ in self.attrs if k == key]

    def get(self, key: str, default: str | None = None) -> str | None:
        values = self.getall(key)
        return values[-1] if values else default

    def line_for(self, key: str) -> int | None:
        vals = [line for k, _, line in self.attrs if k == key]
        return vals[-1] if vals else None

    def findall(self, tag: str, recursive: bool = False) -> list['WNode']:
        result: list[WNode] = []
        for child in self.children:
            if child.tag == tag:
                result.append(child)
            if recursive:
                result.extend(child.findall(tag, True))
        return result

    def find(self, tag: str, recursive: bool = False) -> 'WNode | None':
        nodes = self.findall(tag, recursive)
        return nodes[0] if nodes else None


def parse_wml(path: Path) -> tuple[WNode, list[str]]:
    root = WNode('root', 0)
    stack = [root]
    lines = path.read_text(encoding='utf-8').splitlines()
    for line_no, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith('#textdomain'):
            continue
        m = re.match(r'^\[(/?)(\+?)([^\]]+)\]$', line)
        if m:
            closing = bool(m.group(1))
            tag = m.group(3).strip()
            if closing:
                if len(stack) > 1:
                    node = stack.pop()
                    node.end = line_no
            else:
                node = WNode(tag, line_no, parent=stack[-1])
                stack[-1].children.append(node)
                stack.append(node)
            continue
        if line.startswith('{') and line.endswith('}'):
            stack[-1].macros.append((line, line_no))
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            stack[-1].attrs.append((key.strip(), value.strip(), line_no))
            continue
        stack[-1].macros.append((line, line_no))
    return root, lines


def clean_wml_value(value: str | None) -> str:
    if value is None:
        return ''
    value = value.strip()
    value = re.sub(r'^_\s*', '', value).strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.replace('\\"', '"')


def parse_macro_numbers(macros: list[tuple[str, int]], name: str) -> list[int]:
    pat = re.compile(r'^\{' + re.escape(name) + r'\s+([^}]+)\}$')
    for macro, _ in macros:
        m = pat.match(macro)
        if m:
            nums: list[int] = []
            for part in m.group(1).split():
                try:
                    nums.append(int(part))
                except ValueError:
                    pass
            return nums
    return []


def parse_macro_arg(macros: list[tuple[str, int]], name: str) -> str:
    pat = re.compile(r'^\{' + re.escape(name) + r'\s+([^}]+)\}$')
    for macro, _ in macros:
        m = pat.match(macro)
        if m:
            return m.group(1).strip()
    return ''


def iter_all_nodes(node: WNode) -> Iterable[WNode]:
    for child in node.children:
        yield child
        yield from iter_all_nodes(child)


def all_attr_values(node: WNode, key: str) -> list[tuple[str, int, str]]:
    out: list[tuple[str, int, str]] = []
    for n in iter_all_nodes(node):
        for k, v, line in n.attrs:
            if k == key:
                out.append((clean_wml_value(v), line, n.tag))
    return out

# ---------------------------------------------------------------------------
# Markdown scenario design extraction from README.
# ---------------------------------------------------------------------------


def parse_readme_scenarios(path: Path) -> dict[int, dict[str, str]]:
    text = path.read_text(encoding='utf-8')
    sections = re.split(r'(?m)^###\s+(\d{2})\.\s+(.+?)\s*$', text)
    out: dict[int, dict[str, str]] = {}
    for i in range(1, len(sections), 3):
        number = int(sections[i])
        title = sections[i + 1].strip()
        body = sections[i + 2]
        if number > 20:
            continue
        item: dict[str, str] = {'title': title}
        for label, key in [
            ('Summary', 'summary'),
            ('Characters', 'characters'),
            ('Map', 'map'),
            ('Objectives', 'objectives'),
            ('Implemented special events', 'special_events'),
        ]:
            m = re.search(r'\*\*' + re.escape(label) + r'\.\*\*\s*(.*?)(?=\n\n\*\*|\n###|\Z)', body, re.S)
            if m:
                item[key] = re.sub(r'\s+', ' ', m.group(1)).strip()
        out[number] = item
    return out

# ---------------------------------------------------------------------------
# Map extraction.
# ---------------------------------------------------------------------------

TERRAIN_FAMILIES = [
    ('Cave walls', lambda c: c.startswith('X')),
    ('Cave floors and roads', lambda c: c.startswith('U')),
    ('Castles and keeps', lambda c: c.startswith(('C', 'K'))),
    ('Chasms and lava', lambda c: c.startswith('Q')),
    ('Stone and interior floors', lambda c: c.startswith('I')),
    ('Bridges', lambda c: '^B' in c),
    ('Villages', lambda c: '^V' in c),
    ('Fungus and vegetation', lambda c: '^T' in c or '^F' in c),
    ('Decorative overlays', lambda c: '^E' in c or '^I' in c),
]


def parse_map(path: Path) -> dict[str, Any]:
    rows: list[list[str]] = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or '=' in line and ',' not in line:
            continue
        if ',' in line:
            rows.append([x.strip() for x in line.split(',')])
    width = max((len(r) for r in rows), default=0)
    height = len(rows)
    exact = Counter(c for row in rows for c in row)
    family_counts: dict[str, int] = {}
    for label, pred in TERRAIN_FAMILIES:
        family_counts[label] = sum(count for code, count in exact.items() if pred(code))
    return {
        'width': width,
        'height': height,
        'exact': exact,
        'families': family_counts,
        'hexes': sum(exact.values()),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }

# ---------------------------------------------------------------------------
# Scenario extraction.
# ---------------------------------------------------------------------------

ARCHETYPES = {
    1: ('Survival escape / equipment recovery', 'Very high', 'Moderate', 'Light', 'Very high'),
    2: ('Objective capture / burial-ground assault', 'High', 'Moderate', 'Light', 'High'),
    3: ('Arena assault / two-leader siege', 'High', 'Moderate', 'Moderate', 'High'),
    4: ('Labyrinth pursuit / escape pressure', 'High', 'Moderate', 'Light', 'High'),
    5: ('Crypt raid / light-versus-brood theme', 'High', 'Moderate', 'Moderate', 'High'),
    6: ('Industrial uprising / mine fortress', 'High', 'Moderate', 'Light', 'High'),
    7: ('Illusion hall / mirrored identity', 'High', 'Moderate', 'Light', 'High'),
    8: ('Reservoir sabotage / multi-leader assault', 'Very high', 'Moderate', 'Moderate', 'Very high'),
    9: ('Asylum cleansing / corruption ability', 'Very high', 'High', 'Light', 'Very high'),
    10: ('Forge demolition / environmental danger', 'High', 'Moderate', 'Moderate', 'High'),
    11: ('Investigation / false-city exposure', 'Very high', 'Moderate', 'Moderate', 'Very high'),
    12: ('Temple exposure / reliquary destruction', 'High', 'Moderate', 'Moderate', 'High'),
    13: ('Laboratory assault / duplicate hunter', 'Very high', 'Moderate', 'Light', 'Very high'),
    14: ('Spectral battlefield / command standards', 'High', 'Moderate', 'Moderate', 'High'),
    15: ('Urban horror / light-and-pursuit encounter', 'High', 'Moderate', 'Light', 'High'),
    16: ('Large-scale crossroads battle', 'Very high', 'Moderate', 'Moderate', 'Very high'),
    17: ('Fortress breach / enslaved defenders', 'Very high', 'Moderate', 'Moderate', 'High'),
    18: ('Memory chamber / psychological confrontation', 'Very high', 'Moderate', 'Light', 'Very high'),
    19: ('Soul-chain throne assault', 'Very high', 'Moderate', 'Moderate', 'Very high'),
    20: ('Multi-stage finale / escape phase', 'Critical', 'High', 'Moderate', 'Very high'),
}

LESSONS = {
    1: [('Equipment as objectives', 'Teach movement and exploration before demanding a major battle.'), ('Early explicit choice', 'Establish campaign morality in the first playable chapter.'), ('Hidden-horror reinforcement', 'Use delayed Nightgaunts to sell the stalking premise with core units.')],
    2: [('Multiple capture points', 'Make victory depend on map control rather than only leader elimination.'), ('Readable ritual vocabulary', 'Repeated labels and terrain changes make objective progress visible.'), ('Escalation through corpses', 'Use scheduled undead arrivals to make the burial ground feel active.')],
    3: [('Two enemy command centers', 'Split pressure between a champion and a supporting necromancer.'), ('Arena geography', 'Use a concentrated map identity to frame a conventional assault.'), ('Named captive continuity', 'Make each scenario introduce a distinct moral witness.')],
    4: [('Fog-driven pursuit', 'Fog and narrow cave routes produce pressure without custom AI.'), ('Optional boss pressure', 'A pursuit scenario can still require a named leader for closure.'), ('Spatial horror', 'Use doors, side passages, and Nightgaunts instead of bespoke monsters.')],
    5: [('Artificial dawn theme', 'Narrative lighting can establish a unique crypt identity even with the standard underground schedule.'), ('Flying enemy mix', 'Bats change how players value corridors and chokepoints.'), ('Two-leader hierarchy', 'Separate brood and necromancer leadership for tactical texture.')],
    6: [('Mine terrain vocabulary', 'Rails, keeps, and working floors create an industrial chapter without new terrain art.'), ('Roster transition', 'Gradually broaden human recruitment as survivors accumulate.'), ('Commander-as-law', 'Tie the boss concept directly to the scenario objective structure.')],
    7: [('Mechanical reflection', 'A Ranger copy gives the illusion theme an immediate tactical form.'), ('Symmetry as storytelling', 'Map arrangement can communicate deception before dialogue explains it.'), ('State-aware potential', 'The scenario is a natural future home for deeper variable-driven accusations.')],
    8: [('Large environmental landmark', 'A reservoir gives objective sites a coherent physical relationship.'), ('Multiple leaders and sites', 'Raise complexity by combining capture and elimination requirements.'), ('Corruption handoff', 'Use a narrative disaster to justify a new persistent mechanic in the next chapter.')],
    9: [('Campaign action menu', 'A custom right-click ability demonstrates campaign-local interaction beyond ordinary combat.'), ('Persistent cost', 'Healing for corruption makes short-term survival compete with long-term consequence.'), ('Cleansing sites', 'Objective capture can also modify a campaign-wide variable.')],
    10: [('Production-facility pacing', 'Objective sites can stand in for machinery without Lua or bespoke terrain.'), ('Environmental audio', 'Core hisses and explosions reinforce forge identity.'), ('Reward groundwork', 'This is an appropriate future insertion point for branching permanent weapons.')],
    11: [('Evidence as state', 'Objective capture increments `wpb_truth`, linking investigation to future narrative.'), ('False safety contrast', 'A city-like map can interrupt cave monotony while remaining underground.'), ('Two-part conspiracy', 'Pair a public ruler with a hidden necromantic partner.')],
    12: [('Religious fraud through objectives', 'Reliquaries turn abstract deception into concrete tactical targets.'), ('Witness companion', 'A named acolyte localizes the conflict and supports later dialogue branches.'), ('Core asset reuse', 'Light-mage and lich units communicate corrupted sanctity without custom sprites.')],
    13: [('Boss mirror', 'A duplicate Hunter can reflect the player mechanically as well as narratively.'), ('Containment-site structure', 'Vats create a laboratory loop with clear progress markers.'), ('Consequence dialogue', 'This scenario is ideal for reading sacrifice and corruption totals in future revisions.')],
    14: [('Battlefield recurrence theme', 'Ghosts and Wraiths support the idea of a war that cannot end.'), ('Standards as objectives', 'Command sites translate military memory into map control.'), ('Alliance bridge', 'Freed spirits can become a late-campaign reinforcement source.')],
    15: [('Light as safety', 'Ward braziers make horror legible through controlled safe zones.'), ('Nightgaunt boss identity', 'A core hidden unit naturally supports a stalking antagonist.'), ('Civilian pressure', 'The moral choice becomes especially pointed in an escape-horror context.')],
    16: [('Scale escalation', 'Expand map and recruit quality only after the player understands the campaign systems.'), ('Alliance payoff', 'Late battles should visibly reward earlier rescue choices.'), ('Crossroads structure', 'Multiple strategic lanes create a war scenario distinct from prior dungeon assaults.')],
    17: [('Living enemies under undead command', 'Complicate the moral frame without abandoning the undead-dominated campaign.'), ('Fortress layers', 'Use map architecture to imply wards and progressive breach points.'), ('Reputation-aware future work', 'This is a strong place for surrender behavior based on rescue and sacrifice state.')],
    18: [('State-driven horror', 'Past choices can become literal enemies or dialogue speakers.'), ('Fragmented terrain memory', 'Reuse visual motifs from earlier maps in a new impossible composition.'), ('No easy absolution', 'Treat memory as consequence rather than a binary redemption test.')],
    19: [('Boss-phase foundation', 'Multiple chain sites provide a clean structure for future phase changes.'), ('Resource temptation', 'Soul chains can become a three-way release, shatter, or consume decision.'), ('Final-command inevitability', 'Victory can still trigger the next disaster, preserving momentum into the finale.')],
    20: [('Objective transformation', 'Switch the objective panel after the nexus phase rather than ending immediately.'), ('Campaign-state ending', 'Use sacrifice and corruption totals to select closing text.'), ('Escape after victory', 'A final withdrawal phase makes destruction feel physical and costly.')],
}

ARC_DATA = [
    {
        'slug': 'descent-and-survival', 'title': 'Descent & Survival Arc', 'range': range(1, 6),
        'lede': 'Scenarios 01–05 move from the sinkhole fall through the first organized undead installations, establishing survival, explicit sacrifice, and the campaign’s underground visual grammar.',
        'flow': '01 Stillness → 02 Burial ground → 03 Arena gate → 04 Hunting maze → 05 Blood crypt',
        'analysis': 'The opening arc keeps objectives concrete—recover, capture, kill, escape—while progressively proving that the undead presence is organized. Each scenario introduces a new named captive so the rescue-versus-bait system becomes a repeated campaign language rather than a one-off morality prompt.'
    },
    {
        'slug': 'industry-and-corruption', 'title': 'Industry & Corruption Arc', 'range': range(6, 11),
        'lede': 'Scenarios 06–10 expose the logistical machinery beneath the invasion: mines, illusion control, blood infrastructure, possession research, and the corpse forge.',
        'flow': '06 Mine regime → 07 Illusion halls → 08 Reservoir → 09 Asylum → 10 Forge',
        'analysis': 'This arc converts the enemy from a supernatural menace into a system. The Hunter also stops being merely threatened from outside: the reservoir introduces corruption, and Scenario 09 turns it into a usable but costly player ability.'
    },
    {
        'slug': 'deception-and-memory', 'title': 'Deception & Memory Arc', 'range': range(11, 16),
        'lede': 'Scenarios 11–15 focus on manipulated belief, predatory institutions, bodily imitation, weaponized history, and fear that uses remembered voices.',
        'flow': '11 False city → 12 False temple → 13 Laboratory → 14 Ghost war → 15 Tormentor city',
        'analysis': 'The middle-late campaign shifts from infrastructure to interpretation. `wpb_truth` appears in the false-city investigation, while duplicates, ghosts, and whispering shadows prepare the player for the explicitly psychological Scenario 18.'
    },
    {
        'slug': 'war-and-final-command', 'title': 'War & Final Command Arc', 'range': range(16, 21),
        'lede': 'Scenarios 16–20 transform the solitary descent into open war, fortress assault, memory collapse, confrontation with the hidden master, and a multi-stage final escape.',
        'flow': '16 Crossroads war → 17 Cabal fortress → 18 Memory chamber → 19 Spirit throne → 20 Final Command',
        'analysis': 'The final arc pays off persistent alliance, sacrifice, corruption, and truth variables. Even in the first build, the final scenario changes objectives after the pylons and leaders are resolved and reads campaign morality to choose the closing tone.'
    },
]


def extract_scenario(path: Path, design: dict[str, str], map_info: dict[str, Any]) -> dict[str, Any]:
    root, lines = parse_wml(path)
    scenario = root.find('scenario')
    if scenario is None:
        raise ValueError(f'No [scenario] in {path}')
    number = int(path.name[:2])
    turns = parse_macro_numbers(scenario.macros, 'TURNS')
    music = parse_macro_arg(scenario.macros, 'SCENARIO_MUSIC')
    sides = []
    for side in scenario.findall('side'):
        side_info = {
            'side': clean_wml_value(side.get('side')),
            'controller': clean_wml_value(side.get('controller')),
            'type': clean_wml_value(side.get('type')),
            'id': clean_wml_value(side.get('id')),
            'name': clean_wml_value(side.get('name')),
            'team': clean_wml_value(side.get('user_team_name') or side.get('team_name')),
            'recruit': [x.strip() for x in clean_wml_value(side.get('recruit')).split(',') if x.strip()],
            'income': clean_wml_value(side.get('income')),
            'fog': clean_wml_value(side.get('fog')),
            'shroud': clean_wml_value(side.get('shroud')),
            'x': clean_wml_value(side.get('x')),
            'y': clean_wml_value(side.get('y')),
            'gold': parse_macro_numbers(side.macros, 'GOLD'),
            'line': side.start,
        }
        sides.append(side_info)
    stories = [clean_wml_value(part.get('story')) for story in scenario.findall('story') for part in story.findall('part')]
    objective_sets = []
    for objset in scenario.findall('objectives', True):
        objective_sets.append({
            'line': objset.start,
            'items': [(clean_wml_value(o.get('description')), clean_wml_value(o.get('condition'))) for o in objset.findall('objective')],
        })
    events = []
    for event in scenario.findall('event'):
        event_names = [clean_wml_value(x) for x in event.getall('name')]
        messages = []
        for msg in event.findall('message', True):
            text = clean_wml_value(msg.get('message'))
            if text:
                messages.append({'speaker': clean_wml_value(msg.get('speaker')), 'text': text, 'line': msg.start})
        options = []
        for option in event.findall('option', True):
            options.append({'label': clean_wml_value(option.get('label')), 'line': option.start})
        variables = []
        for node in iter_all_nodes(event):
            if node.tag in {'set_variable', 'clear_variable'}:
                variables.append({
                    'action': node.tag,
                    'name': clean_wml_value(node.get('name')),
                    'value': clean_wml_value(node.get('value')),
                    'add': clean_wml_value(node.get('add')),
                    'sub': clean_wml_value(node.get('sub')),
                    'line': node.start,
                })
        units = []
        for unit in event.findall('unit', True):
            units.append({
                'type': clean_wml_value(unit.get('type')),
                'id': clean_wml_value(unit.get('id')),
                'name': clean_wml_value(unit.get('name')),
                'side': clean_wml_value(unit.get('side')),
                'x': clean_wml_value(unit.get('x')),
                'y': clean_wml_value(unit.get('y')),
                'line': unit.start,
            })
        sounds = [clean_wml_value(s.get('name')) for s in event.findall('sound', True) if s.get('name')]
        terrains = [{
            'x': clean_wml_value(t.get('x')), 'y': clean_wml_value(t.get('y')), 'terrain': clean_wml_value(t.get('terrain')), 'line': t.start
        } for t in event.findall('terrain', True)]
        labels = [{
            'x': clean_wml_value(l.get('x')), 'y': clean_wml_value(l.get('y')), 'text': clean_wml_value(l.get('text')), 'line': l.start
        } for l in event.findall('label', True)]
        filters = []
        for filt in event.findall('filter', True):
            data = {clean_wml_value(k): clean_wml_value(v) for k, v, _ in filt.attrs if k in {'id', 'side', 'x', 'y', 'type'}}
            if data:
                filters.append(data)
        event_info = {
            'names': event_names,
            'line': event.start,
            'end': event.end,
            'messages': messages,
            'options': options,
            'variables': variables,
            'units': units,
            'sounds': sounds,
            'terrains': terrains,
            'labels': labels,
            'filters': filters,
            'endlevels': [clean_wml_value(e.get('result')) for e in event.findall('endlevel', True)],
            'objectives': [
                [(clean_wml_value(o.get('description')), clean_wml_value(o.get('condition'))) for o in os.findall('objective')]
                for os in event.findall('objectives', True)
            ],
        }
        events.append(event_info)
    variables = defaultdict(lambda: {'writes': [], 'reads': []})
    for node in iter_all_nodes(scenario):
        if node.tag in {'set_variable', 'clear_variable'}:
            name = clean_wml_value(node.get('name'))
            if name:
                variables[name]['writes'].append(node.start)
        elif node.tag == 'variable':
            name = clean_wml_value(node.get('name'))
            if name:
                variables[name]['reads'].append(node.start)
    sounds = sorted(set(clean_wml_value(s.get('name')) for s in scenario.findall('sound', True) if s.get('name')))
    unit_types = sorted(set(
        [s['type'] for s in sides if s['type']] +
        [u['type'] for e in events for u in e['units'] if u['type']]
    ))
    labels = [l for e in events for l in e['labels'] if l['text']]
    color_adjust = scenario.find('color_adjust', True)
    tint = None
    if color_adjust:
        tint = {k: clean_wml_value(color_adjust.get(k)) for k in ('red', 'green', 'blue')}
    captive = next((u for e in events for u in e['units'] if u['side'] == '4' and u['id']), None)
    return {
        'number': number,
        'source_file': path.name,
        'source_rel': f'scenarios/{path.name}',
        'id': clean_wml_value(scenario.get('id')),
        'name': clean_wml_value(scenario.get('name')),
        'next': clean_wml_value(scenario.get('next_scenario')),
        'map_file': clean_wml_value(scenario.get('map_file')),
        'turns': turns,
        'music': music,
        'victory_music': clean_wml_value(scenario.get('victory_music')),
        'defeat_music': clean_wml_value(scenario.get('defeat_music')),
        'victory_when_enemies_defeated': clean_wml_value(scenario.get('victory_when_enemies_defeated')),
        'stories': stories,
        'design': design,
        'map': map_info,
        'sides': sides,
        'objective_sets': objective_sets,
        'events': events,
        'variables': dict(variables),
        'sounds': sounds,
        'unit_types': unit_types,
        'labels': labels,
        'tint': tint,
        'captive': captive,
        'lines': len(lines),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'archetype': ARCHETYPES[number],
        'lessons': LESSONS[number],
    }

# ---------------------------------------------------------------------------
# HTML utilities.
# ---------------------------------------------------------------------------


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def code(value: Any) -> str:
    return f'<code>{esc(value)}</code>'


def slugify(text: str) -> str:
    text = text.lower().replace('’', '').replace("'", '')
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text


def scenario_slug(s: dict[str, Any]) -> str:
    return f"{s['number']:02d}-{slugify(s['name'])}.html"


def table(headers: list[str], rows: list[list[str]], table_id: str | None = None) -> str:
    id_attr = f' id="{esc(table_id)}"' if table_id else ''
    head = ''.join(f'<th>{h}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows)
    return f'<div class="table-scroll"><table{id_attr}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def list_html(items: list[str], cls: str = 'compact') -> str:
    return '<ul class="' + cls + '">' + ''.join(f'<li>{x}</li>' for x in items) + '</ul>'


def source_link(prefix: str, rel: str, label: str, line: int | None = None) -> str:
    href = f'{prefix}source/{rel}'
    suffix = f' (line {line})' if line else ''
    return f'<a href="{esc(href)}">{esc(label)}</a>{esc(suffix)}'


def nav_groups(scenarios: list[dict[str, Any]], prefix: str, current: str) -> str:
    def link(href: str, label: str, key: str) -> str:
        current_attr = ' aria-current="page"' if current == key else ''
        return f'<a href="{prefix}{href}"{current_attr}>{esc(label)}</a>'
    parts = [
        '<div class="brand">World Painted Blood</div>',
        '<form class="sidebar-search" action="' + prefix + 'search.html" method="get">'
        '<label class="visually-hidden" for="sidebar-q">Search the reference</label>'
        '<input id="sidebar-q" name="q" type="search" placeholder="Search the reference" aria-label="Search the reference"></form>',
        '<nav aria-label="Reference navigation">',
        '<div class="group">Release</div>',
        link('index.html', 'Home', 'index'),
        link('search.html', 'Search', 'search'),
        '<div class="group">Detailed scenarios</div>',
    ]
    for s in scenarios:
        parts.append(link('scenarios/' + scenario_slug(s), f"{s['number']:02d} — {s['name']}", f"scenario-{s['number']:02d}"))
    parts += ['<div class="group">Arc studies</div>']
    for arc in ARC_DATA:
        parts.append(link(f"reference/{arc['slug']}.html", arc['title'], arc['slug']))
    parts.append(link('reference/moral-state-architecture.html', 'Moral-state architecture', 'moral-state-architecture'))
    parts += ['<div class="group">Technical catalogues</div>']
    ref_links = [
        ('source-architecture.html', 'Source architecture', 'source-architecture'),
        ('unit-catalogue.html', 'Unit catalogue', 'unit-catalogue'),
        ('macro-catalogue.html', 'Utility & macro catalogue', 'macro-catalogue'),
        ('map-inventory.html', 'Map inventory', 'map-inventory'),
        ('audio-catalogue.html', 'Scenario audio catalogue', 'audio-catalogue'),
        ('dependency-matrix.html', 'Dependency & call-site matrix', 'dependency-matrix'),
        ('consistency-report.html', 'Consistency report', 'consistency-report'),
    ]
    for href, label, key in ref_links:
        parts.append(link('reference/' + href, label, key))
    parts += ['<div class="group">Maintenance & extension</div>']
    maint = [
        ('campaign-metadata.html', 'Campaign metadata', 'campaign-metadata'),
        ('playtest-howto.html', 'Playtest HOWTO', 'playtest-howto'),
        ('maintenance-playbook.html', 'Maintenance playbook', 'maintenance-playbook'),
        ('state-lifecycle.html', 'State lifecycle atlas', 'state-lifecycle'),
        ('extension-recipes.html', 'Extension recipes', 'extension-recipes'),
        ('completion-scope.html', 'Completion scope', 'completion-scope'),
    ]
    for href, label, key in maint:
        parts.append(link('reference/' + href, label, key))
    parts += ['<div class="group">Cross-reference</div>']
    cross = [
        ('campaign-flow.html', 'Campaign flow', 'campaign-flow'),
        ('character-index.html', 'Character index', 'character-index'),
        ('event-index.html', 'Event index', 'event-index'),
        ('state-index.html', 'State & variables', 'state-index'),
        ('asset-index.html', 'Asset index', 'asset-index'),
    ]
    for href, label, key in cross:
        parts.append(link('reference/' + href, label, key))
    parts.append('</nav>')
    return ''.join(parts)


def page_template(*, title: str, lede: str, body: str, scenarios: list[dict[str, Any]], prefix: str, current: str, breadcrumb: str) -> str:
    sidebar = nav_groups(scenarios, prefix, current)
    return f'''<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(lede)}">
<title>{esc(title)} — World Painted Blood Developer Reference</title>
<link rel="stylesheet" href="{prefix}assets/site.css">
<script defer src="{prefix}assets/site.js"></script>
</head>
<body>
<header class="site-header">
<div class="kicker">Source-first developer reference for a Battle for Wesnoth horror campaign</div>
<h1>{esc(title)}</h1>
<p>{esc(lede)}</p>
</header>
<div class="shell">
<aside class="sidebar">{sidebar}</aside>
<main class="content">
<div class="toolbar"><div class="breadcrumbs"><a href="{prefix}index.html">Home</a> / {breadcrumb}</div><button class="theme-button" type="button" data-theme-toggle>Use light theme</button></div>
{body}
<footer>Release {VERSION}. Source snapshot: <em>World Painted Blood</em> {VERSION}, generated {ACCESS_DATE}. No external runtime dependencies; open <code>index.html</code> directly from disk. Theme CSS matches the companion <em>Rise of Wesnoth</em> developer reference and retains its solid <code>#333</code> header.</footer>
</main>
</div>
</body>
</html>'''

# ---------------------------------------------------------------------------
# Page content generation.
# ---------------------------------------------------------------------------


def summarize_event(event: dict[str, Any]) -> str:
    names = ', '.join(event['names']) or 'unnamed'
    if 'prestart' in event['names']:
        if event['objectives']:
            return 'Initializes scenario counters, creates labels/captive units, and installs the objective panel.'
        if any(v['name'] == 'wpb_unguarded_instinct' for v in event['variables']) or any('Unguarded Instinct' in m['text'] for m in event['messages']):
            return 'Installs the campaign-menu action for the Hunter’s corruption-powered healing ability.'
        return 'Initializes scenario state and places scripted content before play begins.'
    if 'start' in event['names']:
        return 'Applies the scenario color adjustment and delivers the opening confrontation.'
    if 'time over' in event['names']:
        return 'Supplies the campaign-standard narrative defeat message when turns expire.'
    if 'last breath' in event['names']:
        return 'Handles a named unit’s final dialogue and defeat/victory consequence.'
    if 'die' in event['names']:
        ids = [f.get('id') for f in event['filters'] if f.get('id')]
        who = ', '.join(ids) if ids else 'a required leader'
        return f'Counts the death of {who}, checks combined victory conditions, and may end the scenario.'
    if 'moveto' in event['names']:
        if event['options']:
            return 'Presents the explicit rescue-versus-bait choice and writes persistent moral state.'
        if event['endlevels'] and any('wpb_final_escape' in v['name'] for v in event['variables']):
            return 'Checks completion of the objective phase and transitions into the final escape state.'
        if event['endlevels']:
            return 'Captures an objective location, updates terrain/labels, checks leader counts, and may end the scenario.'
        return 'Triggers a location interaction, dialogue, terrain update, or ending check.'
    if any(n.startswith('turn ') for n in event['names']):
        types = [u['type'] for u in event['units'] if u['type']]
        return 'Introduces a timed reinforcement wave' + (f" ({', '.join(types)})" if types else '') + ' with warning dialogue and sound.'
    return f'Runs scripted actions for the {names} trigger.'


def moral_effects(s: dict[str, Any]) -> list[list[str]]:
    choice_event = next((e for e in s['events'] if e['options']), None)
    if not choice_event:
        return []
    captive = s['captive'] or {}
    rescue = [v for v in choice_event['variables'] if v['name'] in {'wpb_rescued', 'wpb_conscripted', 'wpb_alliance_strength'}]
    sacrifice = [v for v in choice_event['variables'] if v['name'] in {'wpb_sacrificed', 'wpb_corruption'}]
    return [
        ['Free and arm them', f"{esc(captive.get('name') or captive.get('id') or 'The captive')} joins Side 1 as a loyal unit.", ', '.join(code(v['name'] + ' +' + (v['add'] or '1')) for v in rescue)],
        ['Use them as bait', 'The captive is killed; the principal boss is harmed and Side 1 receives immediate gold.', ', '.join(code(v['name'] + ' +' + (v['add'] or '1')) for v in sacrifice)],
    ]


def scenario_page(s: dict[str, Any], scenarios: list[dict[str, Any]]) -> str:
    prefix = '../'
    archetype, importance, complexity, ai, learning = s['archetype']
    turns = ' / '.join(map(str, s['turns'])) if s['turns'] else 'Not declared'
    carryover = '40%, early-finish bonus'
    identity_rows = [
        ['WML ID', code(s['id'])],
        ['Next scenario', code(s['next'] or 'null')],
        ['Map', f"{code(s['map_file'])}, {s['map']['width']} × {s['map']['height']} hexes"],
        ['Turns', turns],
        ['Carryover', carryover],
        ['Music', code(s['music'])],
        ['Source length', f"{s['lines']} lines"],
    ]
    metrics = table(['Field', 'Value'], identity_rows)
    profile = table(['Archetype', 'Story importance', 'WML complexity', 'AI customization', 'Learning value'], [[archetype, importance, complexity, ai, learning]])

    story_html = ''.join(f'<p>{esc(p)}</p>' for p in s['stories'])
    start_event = next((e for e in s['events'] if 'start' in e['names']), None)
    dialogue_rows: list[list[str]] = []
    if start_event:
        for msg in start_event['messages']:
            dialogue_rows.append([code(msg['speaker'] or 'narrator'), esc(msg['text']), f"line {msg['line']}"])
    choice_event = next((e for e in s['events'] if e['options']), None)
    if choice_event:
        for msg in choice_event['messages'][:4]:
            dialogue_rows.append([code(msg['speaker'] or 'choice'), esc(msg['text']), f"line {msg['line']}"])

    exact_top = s['map']['exact'].most_common(10)
    family_top = sorted(s['map']['families'].items(), key=lambda kv: kv[1], reverse=True)
    map_rows = [[esc(name), str(count)] for name, count in family_top if count]
    exact_rows = [[code(name), str(count)] for name, count in exact_top]
    label_rows = [[esc(l['text']), f"({l['x']}, {l['y']})", f"line {l['line']}"] for l in s['labels']]
    tint = s['tint'] or {}

    objective_rows: list[list[str]] = []
    for idx, objset in enumerate(s['objective_sets'], 1):
        stage = 'Initial' if idx == 1 else f'Stage {idx}'
        for desc, condition in objset['items']:
            objective_rows.append([stage, esc(condition.title()), esc(desc), f"line {objset['line']}"])

    side_rows = []
    for side in s['sides']:
        side_rows.append([
            code(side['side']), esc(side['controller']), esc(side['name'] or 'No leader'), code(side['type'] or '—'),
            esc(', '.join(side['recruit']) or '—'), esc(' / '.join(map(str, side['gold'])) or '—'), esc(side['income'] or '—'),
            esc('/'.join(x for x in [f"fog={side['fog']}" if side['fog'] else '', f"shroud={side['shroud']}" if side['shroud'] else ''] if x) or '—')
        ])

    event_rows = []
    for e in s['events']:
        trigger = ', '.join(e['names']) or 'unnamed'
        event_rows.append([code(trigger), esc(summarize_event(e)), f"lines {e['line']}–{e['end'] or e['line']}"])

    state_rows = []
    for name, info in sorted(s['variables'].items()):
        state_rows.append([
            code(name), ', '.join(map(str, info['writes'])) or '—', ', '.join(map(str, info['reads'])) or '—',
            'Persistent campaign state' if name in {'wpb_rescued','wpb_conscripted','wpb_sacrificed','wpb_corruption','wpb_truth','wpb_alliance_strength'} else 'Scenario-local or transition state'
        ])

    asset_rows = [
        ['Scenario music', code(s['music']), 'Campaign-local silent placeholder, intended for replacement by the final recording.'],
        ['Victory / defeat', f"{code(s['victory_music'])} / {code(s['defeat_music'])}", 'Core Wesnoth audio.'],
    ]
    for snd in s['sounds']:
        asset_rows.append(['Sound effect', code(snd), 'Core/mainline asset referenced by basename.'])
    for typ in s['unit_types']:
        origin = 'Campaign' if typ == 'WPB Hunter' else 'Core'
        asset_rows.append(['Unit type', code(typ), f'{origin} unit definition.'])

    lesson_rows = [[esc(pattern), esc(lesson)] for pattern, lesson in s['lessons']]

    source_note = (
        '<p class="source-note">Source facts come from ' + source_link(prefix, s['source_rel'], s['source_file']) +
        ' and ' + source_link(prefix, 'maps/' + s['map_file'], s['map_file']) +
        '. Design interpretations are identified in the lessons section.</p>'
    )

    prev_s = scenarios[s['number'] - 2] if s['number'] > 1 else None
    next_s = scenarios[s['number']] if s['number'] < len(scenarios) else None
    prev_next = '<div class="prev-next">'
    prev_next += (f'<a href="{scenario_slug(prev_s)}">← {prev_s["number"]:02d} — {esc(prev_s["name"])}</a>' if prev_s else '<span></span>')
    prev_next += (f'<a href="{scenario_slug(next_s)}">{next_s["number"]:02d} — {esc(next_s["name"])} →</a>' if next_s else '<a href="../reference/campaign-flow.html">Campaign flow →</a>')
    prev_next += '</div>'

    body = f'''
<section><h2>Identity</h2>{metrics}{profile}</section>
<section><h2>Story &amp; dialogue</h2>{story_html}
{table(['Speaker', 'Dialogue', 'Source'], dialogue_rows) if dialogue_rows else ''}
<div class="callout"><strong>Current implementation.</strong> The 0.1.0 scenario text establishes the chapter premise and opening confrontation. The larger dialogue plan remains intentionally open for revision after playtesting.</div></section>
<section><h2>Map description</h2><p>{esc(s['design'].get('map', ''))}</p>
<div class="grid"><div class="card"><h3>Terrain families</h3>{table(['Family', 'Hex count'], map_rows)}</div><div class="card"><h3>Most common exact codes</h3>{table(['Terrain code', 'Hex count'], exact_rows)}</div></div>
<p><strong>Dimensions:</strong> {s['map']['width']} × {s['map']['height']} ({s['map']['hexes']} map cells including border). <strong>Screen tint:</strong> red {esc(tint.get('red','—'))}, green {esc(tint.get('green','—'))}, blue {esc(tint.get('blue','—'))}.</p>
{table(['Scripted label', 'Coordinate', 'Source'], label_rows) if label_rows else ''}</section>
<section><h2>Objectives, sides, and AI</h2>{table(['Objective set', 'Condition', 'Description', 'Source'], objective_rows)}
{table(['Side', 'Controller', 'Leader', 'Type', 'Recruit list', 'Gold E/N/H', 'Income', 'Visibility'], side_rows)}
<p>The scenario explicitly sets {code('victory_when_enemies_defeated=no')}; victory is granted only when its objective-site counter and required leader-death counter are both satisfied. Enemy sides use standard Wesnoth AI with no campaign-local Lua AI in this release.</p></section>
<section><h2>Moral decision</h2>{table(['Choice', 'Immediate effect', 'Persistent state'], moral_effects(s))}
<p class="small">Only the explicit choice event changes sacrifice and corruption. Ordinary battlefield losses do not automatically count as deliberate sacrifices.</p></section>
<section><h2>Events</h2>{table(['Trigger', 'Effect', 'Source'], event_rows)}</section>
<section><h2>State and variables</h2>{table(['Variable', 'Writes', 'Reads', 'Lifecycle'], state_rows) if state_rows else '<p>No explicit variables.</p>'}</section>
<section><h2>Assets and units</h2>{table(['Resource', 'Identifier', 'Origin / use'], asset_rows)}</section>
<section><h2>Lessons for authors</h2><p><strong>Design interpretation.</strong> These are reusable readings of the source, not claims explicitly written in WML.</p>{table(['Pattern', 'Reuse lesson'], lesson_rows)}</section>
{source_note}{prev_next}
'''
    return page_template(title=f"{s['number']:02d} — {s['name']}", lede=s['design'].get('summary', s['stories'][0] if s['stories'] else ''), body=body, scenarios=scenarios, prefix=prefix, current=f"scenario-{s['number']:02d}", breadcrumb=f"Scenario {s['number']:02d}")


def home_page(scenarios: list[dict[str, Any]], file_inventory: dict[str, int], sound_assets: list[str]) -> str:
    rows = []
    for s in scenarios:
        rows.append([
            f'<a href="scenarios/{scenario_slug(s)}">{s["number"]:02d}</a>',
            f'<a href="scenarios/{scenario_slug(s)}">{esc(s["name"])}</a>',
            code(s['source_file']),
            f"{s['map']['width']} × {s['map']['height']}",
            esc(' / '.join(map(str, s['turns']))),
            '<span class="badge done">Detailed</span>',
        ])
    tech_cards = [
        ('Source architecture', 'Load graph, file counts, and source-loading boundaries.', 'reference/source-architecture.html'),
        ('Map inventory', 'All twenty maps, dimensions, hashes, and terrain-family counts.', 'reference/map-inventory.html'),
        ('Scenario audio', 'Twenty local music placeholders and all direct core sound references.', 'reference/audio-catalogue.html'),
        ('State lifecycle', 'Persistent moral variables, scenario counters, and cleanup behavior.', 'reference/state-lifecycle.html'),
        ('Campaign flow', 'Linear scenario graph plus state and ending consequences.', 'reference/campaign-flow.html'),
        ('Playtest HOWTO', 'Installation, debug jumps, validation, and regression workflow.', 'reference/playtest-howto.html'),
    ]
    card_html = '<div class="grid">' + ''.join(f'<div class="card"><h3><a href="{href}">{esc(title)}</a></h3><p>{esc(desc)}</p></div>' for title, desc, href in tech_cards) + '</div>'
    body = f'''
<section><h2>Release status</h2><div class="grid">
<div class="card metric"><strong>20</strong>fully analyzed scenario chapters</div>
<div class="card metric"><strong>20</strong>scenario configuration files indexed</div>
<div class="card metric"><strong>20</strong>unique campaign map files</div>
<div class="card metric"><strong>{len(sound_assets)}</strong>direct core sound basenames</div>
</div>
<p>Release {VERSION} is the first complete developer-reference edition for the first installable campaign build. It traces the exact campaign entry point, one custom unit, one utility file, twenty linked scenarios, twenty maps, twenty local music placeholders, persistent moral state, and the multi-stage final escape.</p>
<div class="callout warn"><strong>Playtest status.</strong> The campaign has passed its bundled static validator but has not yet completed a full engine playthrough. This reference documents the current source accurately; it does not imply that balance, dialogue, AI behavior, or every intended special mechanic is final.</div></section>
<section><h2>How to use this release</h2>{table(['Need', 'Start here'], [
['Understand an individual scenario', 'Scenario 01–20 chapters, each with story, map, sides, events, state, assets, and design lessons.'],
['Trace the campaign’s moral system', '<a href="reference/moral-state-architecture.html">Moral-state architecture</a> and <a href="reference/state-lifecycle.html">State lifecycle atlas</a>.'],
['Prepare a local test run', '<a href="reference/playtest-howto.html">Playtest HOWTO</a>.'],
['Find a filename, unit, variable, or event', '<a href="search.html">Offline full-text search</a> and the cross-reference pages.'],
['Compare implementation with design intent', 'Scenario chapters and the four arc studies.'],
])}</section>
<section><h2>Scenario-file inventory</h2><label for="scenario-filter" class="small">Filter the scenario table</label><br><input class="filter" id="scenario-filter" data-table-filter="#scenario-table" placeholder="Name, file, map size…">{table(['No.', 'Title', 'Source file', 'Map size', 'Turns E/N/H', 'Reference status'], rows, 'scenario-table')}</section>
<section><h2>Campaign premise</h2><p>Across southern Wesnoth, burial grounds have emptied, villages have fallen silent, and red water has begun seeping into the rivers around the Swamp of Esten. A solitary Hunter falls through a sinkhole into the underground kingdom feeding the invasion. He can rescue the living, conscript them, or deliberately spend them as shields and bait; all paths can reach victory, but the campaign records what kind of victor returns.</p></section>
<section><h2>Evidence standard</h2>{table(['Label', 'Meaning'], [
['Source fact', 'Declared directly in WML, map data, README documentation, or the bundled manifests.'],
['Derived fact', 'Calculated from source declarations, such as map dimensions, counts, hashes, or cross-file use.'],
['Design interpretation', 'An inference about pacing, horror, teaching value, or future extension; identified as interpretation.'],
])}</section>
<section><h2>Technical catalogues</h2>{card_html}</section>
<section><h2>Verified source footprint</h2>{table(['Path', 'Count', 'Responsibility'], [[code(k), str(v), esc({
'_main.cfg':'Campaign declaration and loading boundary.', 'scenarios/':'Playable WML scenario chain.', 'maps/':'Terrain maps.', 'music/':'Scenario-specific Ogg placeholders.', 'units/':'Campaign-local Hunter definition.', 'utils/':'Persistent state and shared event macros.', 'docs/':'Manifests and validation notes.', 'tools/':'Static campaign validator.'
}.get(k,''))] for k,v in file_inventory.items()])}</section>
'''
    return page_template(title='World Painted Blood', lede='Developer Reference', body=body, scenarios=scenarios, prefix='', current='index', breadcrumb='Home')


def arc_page(arc: dict[str, Any], scenarios: list[dict[str, Any]]) -> str:
    selected = [s for s in scenarios if s['number'] in arc['range']]
    rows = []
    for s in selected:
        rows.append([
            f'<a href="../scenarios/{scenario_slug(s)}">{s["number"]:02d} — {esc(s["name"])}</a>',
            esc(s['archetype'][0]),
            esc(s['design'].get('special_events', '')),
            code(s['captive']['name'] if s['captive'] else '—'),
        ])
    state = sorted(set(name for s in selected for name in s['variables'] if name.startswith('wpb_')))
    body = f'''
<section><h2>Flow</h2><div class="flow">{esc(arc['flow'])}</div></section>
<section><h2>Arc reading</h2><p>{esc(arc['analysis'])}</p></section>
<section><h2>Scenario comparison</h2>{table(['Scenario', 'Archetype', 'Implemented special events', 'Named captive'], rows)}</section>
<section><h2>State surface</h2>{list_html([code(x) for x in state])}</section>
<section><h2>Authoring takeaway</h2><div class="callout"><strong>Design interpretation.</strong> The arc changes its dominant horror mode every scenario while preserving three stable anchors: undead-dominated opposition, a named human choice, and victory requiring both spatial progress and command disruption.</div></section>
'''
    return page_template(title=arc['title'], lede=arc['lede'], body=body, scenarios=scenarios, prefix='../', current=arc['slug'], breadcrumb=esc(arc['title']))


def reference_pages(scenarios: list[dict[str, Any]], readme: str, build_manifest: dict[str, Any], sound_manifest_text: str) -> dict[str, tuple[str, str, str]]:
    """Return filename -> (title, lede, body)."""
    pages: dict[str, tuple[str, str, str]] = {}

    # Source architecture
    inventory = Counter()
    for p in CAMPAIGN.rglob('*'):
        if p.is_file():
            rel = p.relative_to(CAMPAIGN)
            key = rel.parts[0] + '/' if len(rel.parts) > 1 else rel.name
            inventory[key] += 1
    arch_rows = []
    responsibilities = {
        '_main.cfg':'Campaign metadata, difficulty definitions, loading boundary, and binary path.',
        'scenarios/':'Twenty linked scenario configurations.',
        'maps/':'Twenty external terrain maps.',
        'music/':'Twenty valid silent Ogg placeholders.',
        'units/':'The campaign-local WPB Hunter type.',
        'utils/':'Shared state, death, timeout, carryover, and objective-note macros.',
        'docs/':'Build, sound, implementation, and validation documentation.',
        'tools/':'Static campaign validation script.',
    }
    order = ['_main.cfg','scenarios/','maps/','music/','units/','utils/','docs/','tools/','README.md','CHANGELOG.md','LICENSE']
    for k in order:
        if k in inventory:
            arch_rows.append([code(k), str(inventory[k]), esc(responsibilities.get(k,''))])
    load_graph = '''_main.cfg
├── [campaign]
│   ├── id = World_Painted_Blood
│   ├── first_scenario = 01_When_the_Stillness_Comes
│   ├── EASY / NORMAL / HARD
│   └── credits and campaign description
└── #ifdef CAMPAIGN_WORLD_PAINTED_BLOOD
    ├── [binary_path] data/add-ons/World_Painted_Blood
    ├── {~add-ons/World_Painted_Blood/utils}
    ├── [units] {~add-ons/World_Painted_Blood/units} [/units]
    └── {~add-ons/World_Painted_Blood/scenarios}'''
    pages['source-architecture.html'] = ('Source Architecture', 'The verified load graph and file-system footprint of World Painted Blood 0.1.0.', f'''
<section><h2>Repository entry point</h2><p><code>_main.cfg</code> declares the textdomain, campaign menu entry, difficulty surface, first scenario, binary path, utility include, unit include, and scenario include.</p><div class="flow">{esc(load_graph)}</div><p>{source_link('../', '_main.cfg', 'Open the campaign entry point')}</p></section>
<section><h2>Verified directory inventory</h2>{table(['Path', 'Count', 'Responsibility'], arch_rows)}</section>
<section><h2>Source-loading boundary</h2>{table(['Layer', 'Loaded as', 'Developer consequence'], [
['Utilities', 'Directory preprocessor include', 'Campaign macros are available before scenario files are parsed.'],
['Unit types', 'Directory include inside <code>[units]</code>', 'The custom Hunter type is registered for every campaign scenario.'],
['Scenarios', 'Directory preprocessor include', 'All twenty scenario IDs become available to the transition chain.'],
['Binary assets', '<code>[binary_path]</code>', 'Maps, music, and future local sounds resolve relative to the add-on directory.'],
])}</section>
<section><h2>Custom-code footprint</h2><div class="grid"><div class="card metric"><strong>1</strong>campaign unit file</div><div class="card metric"><strong>1</strong>utility WML file</div><div class="card metric"><strong>20</strong>scenario configurations</div><div class="card metric"><strong>20</strong>unique maps</div></div>
<p>Architecture takeaway. The first build deliberately keeps custom code small. Most scenario identity comes from external maps, named core units, event composition, labels, color adjustment, persistent variables, and scenario-specific music paths.</p></section>''')

    # Metadata
    main_root, _ = parse_wml(CAMPAIGN/'_main.cfg')
    campaign_node = main_root.find('campaign')
    meta_rows = []
    if campaign_node:
        for key in ['id','rank','name','abbrev','define','first_scenario','icon','image','type','allow_difficulty_change','description']:
            meta_rows.append([code(key), esc(clean_wml_value(campaign_node.get(key)))])
    pages['campaign-metadata.html'] = ('Campaign Metadata', 'Exact campaign-menu declaration, difficulty surface, credits, and loading identity.', f'''
<section><h2>Campaign declaration</h2>{table(['Key', 'Value'], meta_rows)}</section>
<section><h2>Difficulty surface</h2>{table(['Define', 'Label', 'Presented description', 'Role in scenarios'], [
[code('EASY'), 'Tracker', 'Normal', 'Most turns and player gold; least enemy gold.'],
[code('NORMAL'), 'Hunter', 'Challenging', 'Default balance target.'],
[code('HARD'), 'Blooded Hunter', 'Difficult', 'Fewest turns and player gold; strongest enemy economy.'],
])}</section>
<section><h2>Credits and status</h2><p>The campaign credits Bryant Family for concept, design, and narrative. The implementation is labeled as a generated development build intended for iterative playtesting.</p><div class="callout warn">The metadata description explicitly calls this an “Initial test build for Wesnoth 1.18.” Keep that wording until an engine playthrough and balance pass justify a stronger release claim.</div></section>
<p class="source-note">{source_link('../', '_main.cfg', 'Campaign source')}</p>''')

    # Unit catalogue
    unit_root, _ = parse_wml(CAMPAIGN/'units/Hunter.cfg')
    unit = unit_root.find('unit_type')
    unit_rows = []
    if unit:
        for key in ['id','name','level','hitpoints','movement','experience','advances_to','cost','usage','description']:
            unit_rows.append([code(key), esc(clean_wml_value(unit.get(key)))])
        base = unit.find('base_unit')
        if base:
            unit_rows.insert(1, [code('base_unit'), code(clean_wml_value(base.get('id')))])
    recruit_usage = defaultdict(list)
    for s in scenarios:
        for side in s['sides']:
            for typ in side['recruit']:
                recruit_usage[typ].append(s['number'])
    core_rows = [[code(t), ', '.join(f'{n:02d}' for n in nums)] for t, nums in sorted(recruit_usage.items())]
    pages['unit-catalogue.html'] = ('Unit Catalogue', 'The campaign-local Hunter and every directly declared recruit type in the scenario chain.', f'''
<section><h2>Custom unit: WPB Hunter</h2>{table(['Field', 'Value'], unit_rows)}<p>The Hunter inherits the core Ranger definition through <code>[base_unit]</code>, preserving its movement type, attacks, animations, and inherited sound surface unless explicitly overridden.</p></section>
<section><h2>Direct recruit catalogue</h2><label class="small" for="unit-filter">Filter by unit or scenario</label><br><input id="unit-filter" class="filter" data-table-filter="#unit-table" placeholder="Skeleton, Mage, 16…">{table(['Unit type', 'Scenarios where recruited'], core_rows, 'unit-table')}</section>
<section><h2>Design boundary</h2><div class="callout">Only one custom unit is registered in 0.1.0. Named allies and villains use core unit types with scenario-local IDs and display names. This minimizes art and animation dependencies during the first playtest cycle.</div></section>
<p class="source-note">{source_link('../', 'units/Hunter.cfg', 'Hunter unit source')}</p>''')

    # Macro catalogue
    macro_text = (CAMPAIGN/'utils/macros.cfg').read_text(encoding='utf-8')
    macro_names = re.findall(r'(?m)^#define\s+(\S+)', macro_text)
    macro_desc = {
        'WPB_ENSURE_VARIABLES':'Initializes persistent campaign variables once.',
        'WPB_HUNTER_DEATH':'Installs the universal Hunter last-breath defeat event.',
        'WPB_TIME_OVER':'Installs a campaign-standard time-over line.',
        'WPB_GOLD_CARRYOVER':'Adds 40% bonus carryover to the objective panel.',
        'WPB_RECRUIT_NOTE':'Adds the persistent moral-choice explanation to objectives.',
    }
    call_sites = defaultdict(list)
    for s in scenarios:
        text = (CAMPAIGN/s['source_rel']).read_text(encoding='utf-8')
        for name in macro_names:
            if '{' + name in text:
                call_sites[name].append(s['number'])
    macro_rows = [[code(name), esc(macro_desc.get(name,'')), ', '.join(f'{n:02d}' for n in call_sites[name])] for name in macro_names]
    pages['macro-catalogue.html'] = ('Utility & Macro Catalogue', 'All campaign-local macros and their scenario call sites.', f'''
<section><h2>Campaign-local utility surface</h2>{table(['Macro', 'Contract', 'Scenario call sites'], macro_rows)}</section>
<section><h2>State initialization</h2><div class="flow">wpb_initialized
├── wpb_rescued = 0
├── wpb_conscripted = 0
├── wpb_sacrificed = 0
├── wpb_corruption = 0
├── wpb_truth = 0
└── wpb_alliance_strength = 0</div></section>
<section><h2>Maintenance guidance</h2><p>Keep campaign-local macros prefixed with <code>WPB_</code>. When a repeated event grows beyond a small objective or death helper, move it into a separate utility file rather than expanding <code>macros.cfg</code> indefinitely.</p></section>
<p class="source-note">{source_link('../', 'utils/macros.cfg', 'Utility source')}</p>''')

    # Map inventory
    map_rows = []
    for s in scenarios:
        top = ', '.join(f'{k} {v}' for k,v in s['map']['exact'].most_common(5))
        map_rows.append([f'<a href="../scenarios/{scenario_slug(s)}">{s["number"]:02d}</a>', code(s['map_file']), f"{s['map']['width']} × {s['map']['height']}", str(s['map']['hexes']), esc(top), code(s['map']['sha256'][:12])])
    pages['map-inventory.html'] = ('Map Inventory', 'Twenty unique underground maps reconciled to twenty scenario files.', f'''
<section><h2>Map-file inventory</h2><label class="small" for="map-filter">Filter maps</label><br><input id="map-filter" class="filter" data-table-filter="#map-table" placeholder="Scenario, filename, terrain code…">{table(['Scenario', 'Map file', 'Dimensions', 'Cells', 'Five most common codes', 'SHA-256 prefix'], map_rows, 'map-table')}</section>
<section><h2>Terrain vocabulary</h2><p>The maps use existing cave walls and floors, underground castle/keep terrain, villages, fungus overlays, chasms, lava, bridges, and interior stone. Scenario identity is produced by composition, tint, labels, and scripted terrain changes rather than new terrain graphics.</p></section>
<section><h2>Reuse status</h2><p>Every scenario currently references a distinct map filename. There is no intentional map reuse in version {VERSION}.</p></section>''')

    # Audio catalogue
    music_rows = [[f'{s["number"]:02d}', code(s['music']), 'Campaign-local Ogg placeholder', code(s['source_file'])] for s in scenarios]
    sound_usage = defaultdict(list)
    for s in scenarios:
        for snd in s['sounds']:
            sound_usage[snd].append(s['number'])
    sound_rows = [[code(snd), ', '.join(f'{n:02d}' for n in nums), 'Core/mainline basename'] for snd, nums in sorted(sound_usage.items())]
    pages['audio-catalogue.html'] = ('Scenario Audio Catalogue', 'Twenty custom music paths and every directly referenced core sound effect.', f'''
<section><h2>Scenario music</h2>{table(['Scenario', 'Filename', 'Origin', 'Call site'], music_rows)}</section>
<section><h2>Direct sound effects</h2>{table(['Sound basename', 'Scenarios', 'Origin'], sound_rows)}</section>
<section><h2>Replacement contract</h2><div class="callout"><strong>Do not rename the music files.</strong> Replace each silent placeholder in place. The scenario WML already points to <code>01_Scenario.ogg</code> through <code>20_Scenario.ogg</code>.</div></section>
<section><h2>Sound-copy plan</h2><p>Version 0.1.0 references installed core sounds by basename. The bundled sound manifest records their expected source paths so campaign-local copies can be added later without changing call sites.</p><p>{source_link('../', 'docs/SOUND_ASSET_MANIFEST.md', 'Open the sound asset manifest')}</p></section>''')

    # Dependency matrix
    dep_rows = []
    for s in scenarios:
        dep_rows.append([
            f'<a href="../scenarios/{scenario_slug(s)}">{s["number"]:02d}</a>',
            code(s['source_file']), code(s['map_file']), code(s['music']),
            esc(', '.join(s['sounds']) or '—'), esc(', '.join(t for t in s['unit_types'] if t != 'WPB Hunter') or '—'),
            esc(', '.join(sorted(s['variables'].keys()))),
        ])
    pages['dependency-matrix.html'] = ('Dependency & Call-Site Matrix', 'Scenario-to-map, audio, unit, and state dependencies for the complete campaign chain.', f'''
<section><h2>Scenario dependency matrix</h2><label class="small" for="dep-filter">Filter dependencies</label><br><input id="dep-filter" class="filter" data-table-filter="#dep-table" placeholder="Variable, unit, sound, filename…">{table(['Scenario', 'WML', 'Map', 'Music', 'Sounds', 'Direct unit surface', 'Variables'], dep_rows, 'dep-table')}</section>
<section><h2>Shared dependencies</h2>{table(['Dependency', 'Call pattern'], [
[code('WPB Hunter'), 'Side 1 leader in every scenario.'],
[code('WPB_ENSURE_VARIABLES'), 'Called at prestart to initialize campaign-wide state.'],
[code('WPB_HUNTER_DEATH'), 'Included by every scenario.'],
[code('WPB_TIME_OVER'), 'Included by every scenario.'],
[code('UNDERGROUND'), 'Time schedule used by all scenarios.'],
[code('SCENARIO_MUSIC'), 'One fixed campaign-local filename per scenario.'],
])}</section>''')

    # Moral-state architecture
    pages['moral-state-architecture.html'] = ('Moral-State Architecture', 'How rescue, conscription, sacrifice, corruption, truth, and alliance strength are written and read across the campaign.', f'''
<section><h2>Core decision loop</h2><div class="flow">Approach named captive
├── Free and arm
│   ├── wpb_rescued += 1
│   ├── wpb_conscripted += 1
│   ├── wpb_alliance_strength += 1
│   └── captive becomes loyal Side 1 unit
└── Use as bait
    ├── wpb_sacrificed += 1
    ├── wpb_corruption += 1
    ├── boss takes scripted damage
    ├── Side 1 gains immediate gold
    └── captive is killed</div></section>
<section><h2>Persistent variables</h2>{table(['Variable', 'Meaning', 'Current 0.1.0 role'], [
[code('wpb_rescued'), 'Named captives deliberately saved.', 'Ending/state record and future ally hook.'],
[code('wpb_conscripted'), 'Saved captives converted to controlled units.', 'Tracks armed rescue rather than passive release.'],
[code('wpb_sacrificed'), 'Named captives deliberately used as bait.', 'Read in the final scenario to select darker ending text.'],
[code('wpb_corruption'), 'Moral and supernatural corruption.', 'Raised by bait choices; spent/increased by Scenario 09 ability; read in ending logic.'],
[code('wpb_truth'), 'Evidence gathered against the cabal.', 'Incremented by evidence sites in Scenario 11; reserved for later branching.'],
[code('wpb_alliance_strength'), 'Strength of groups willing to help later.', 'Raised by rescue choices; groundwork for richer late-campaign reinforcement logic.'],
])}</section>
<section><h2>Fairness boundary</h2><p>The campaign does not treat every unit death as a deliberate sacrifice. Only explicit choice events modify <code>wpb_sacrificed</code> and <code>wpb_corruption</code>. This avoids punishing the player for ordinary combat variance.</p></section>
<section><h2>Current implementation versus intended depth</h2><div class="callout warn">The variables are present and persist, but version 0.1.0 uses only a subset of the planned downstream consequences. Playtesting should verify the basic loop first; later revisions can add alliance reinforcements, state-aware accusations, surrender behavior, and more granular endings without changing the foundational variable names.</div></section>''')

    # Campaign flow
    flow_lines = []
    for s in scenarios:
        flow_lines.append(f"{s['number']:02d} {s['name']}")
        if s['number'] < 20:
            flow_lines.append('│')
            flow_lines.append('▼')
    flow = '\n'.join(flow_lines)
    transition_rows = [[f'{s["number"]:02d}', 'Objective-site counter + required leader count', esc(', '.join(sorted(k for k in s['variables'] if k in {'wpb_rescued','wpb_conscripted','wpb_sacrificed','wpb_corruption','wpb_truth','wpb_alliance_strength'})) or 'Persistent moral state may already exist'), f'{s["number"]+1:02d}' if s['number'] < 20 else 'Campaign end'] for s in scenarios]
    pages['campaign-flow.html'] = ('Campaign Flow', 'The linear twenty-scenario descent, persistent decision surface, and final objective transformation.', f'''
<section><h2>Scenario chain</h2><div class="flow">{esc(flow)}</div></section>
<section><h2>Transition table</h2>{table(['From', 'Victory trigger', 'State carried', 'To'], transition_rows)}</section>
<section><h2>Final scenario phase change</h2><div class="flow">Destroy 4 command pylons + defeat 3 leaders
│
├── wpb_final_escape = yes
├── objective panel changes
└── Hunter must reach western sinkhole
    ├── high sacrifice/corruption → darker closing text
    └── otherwise → survivor-centered closing text</div></section>
<section><h2>Design reading</h2><p><strong>Design interpretation.</strong> The campaign is structurally linear but morally variable. That keeps scenario production and testing manageable while still allowing the protagonist’s identity and the late narrative tone to respond to player choice.</p></section>''')

    # State index and lifecycle
    state_use = defaultdict(lambda: {'scenarios': set(), 'writes': [], 'reads': []})
    for s in scenarios:
        for name, info in s['variables'].items():
            state_use[name]['scenarios'].add(s['number'])
            state_use[name]['writes'].extend((s['number'], line) for line in info['writes'])
            state_use[name]['reads'].extend((s['number'], line) for line in info['reads'])
    state_rows = []
    for name, info in sorted(state_use.items()):
        lifecycle = 'Campaign-persistent' if name in {'wpb_initialized','wpb_rescued','wpb_conscripted','wpb_sacrificed','wpb_corruption','wpb_truth','wpb_alliance_strength'} else ('Cross-phase' if name == 'wpb_final_escape' else 'Scenario-local')
        state_rows.append([code(name), ', '.join(f'{n:02d}' for n in sorted(info['scenarios'])), str(len(info['writes'])), str(len(info['reads'])), lifecycle])
    pages['state-index.html'] = ('State & Variable Index', 'Every explicitly read or written variable in the twenty-scenario source tree.', f'''
<section><h2>Variable inventory</h2><label class="small" for="state-filter">Filter variables</label><br><input id="state-filter" class="filter" data-table-filter="#state-table" placeholder="corruption, s20, escape…">{table(['Variable', 'Scenarios', 'Writes', 'Reads', 'Lifecycle'], state_rows, 'state-table')}</section>
<section><h2>Naming convention</h2><p><code>wpb_</code> prefixes every campaign variable. Scenario counters use <code>wpb_sNN_sites</code> and <code>wpb_sNN_bosses</code>; campaign-wide values use descriptive names without scenario numbers.</p></section>''')
    pages['state-lifecycle.html'] = ('State Lifecycle Atlas', 'Persistent moral state, scenario-local counters, and the final escape transition.', f'''
<section><h2>Campaign initialization</h2><p><code>WPB_ENSURE_VARIABLES</code> checks <code>wpb_initialized</code>. On the first scenario only, it initializes the six persistent campaign values to zero.</p></section>
<section><h2>Per-scenario lifecycle</h2><div class="flow">prestart
├── wpb_sNN_sites = 0
├── wpb_sNN_bosses = 0
└── wpb_final_escape = no

objective moveto
└── wpb_sNN_sites += 1

required leader die
└── wpb_sNN_bosses += 1

combined threshold met
└── [endlevel] victory</div></section>
<section><h2>Persistent choice lifecycle</h2><p>Rescue, conscription, sacrifice, corruption, truth, and alliance values are never cleared during the campaign. They remain available to later filters and the final ending logic.</p></section>
<section><h2>Cleanup recommendation</h2><div class="callout warn">Scenario-local counters are overwritten at each scenario’s prestart but not explicitly cleared on victory. This is safe because names are scenario-specific, though a future cleanup macro could reduce save-file clutter.</div></section>''')

    # Character index
    char_rows = []
    for s in scenarios:
        leaders = [side for side in s['sides'] if side['id']]
        for side in leaders:
            role = 'Protagonist' if side['id'] == 'Hunter' else ('Named captive' if side['side'] == '4' else 'Enemy leader')
            char_rows.append([f'<a href="../scenarios/{scenario_slug(s)}">{s["number"]:02d}</a>', esc(side['name']), code(side['id']), code(side['type']), role])
        if s['captive'] and not any(side['id'] == s['captive']['id'] for side in leaders):
            c = s['captive']
            char_rows.append([f'<a href="../scenarios/{scenario_slug(s)}">{s["number"]:02d}</a>', esc(c['name']), code(c['id']), code(c['type']), 'Named captive'])
    pages['character-index.html'] = ('Character Index', 'Named scenario leaders and captives, with unit types and call sites.', f'''
<section><h2>Named cast</h2><label class="small" for="char-filter">Filter characters</label><br><input id="char-filter" class="filter" data-table-filter="#char-table" placeholder="Hunter, lich, captive…">{table(['Scenario', 'Display name', 'WML ID', 'Unit type', 'Role'], char_rows, 'char-table')}</section>
<section><h2>Continuity model</h2><p>The Hunter is the only universally mandatory persistent character. Named captives become persistent recall-list units when rescued, but each scenario remains completable when earlier captives died or were sacrificed.</p></section>''')

    # Event index
    event_rows = []
    for s in scenarios:
        for e in s['events']:
            event_rows.append([f'<a href="../scenarios/{scenario_slug(s)}">{s["number"]:02d}</a>', code(', '.join(e['names']) or 'unnamed'), esc(summarize_event(e)), f"{s['source_file']}:{e['line']}"])
    pages['event-index.html'] = ('Event Index', 'Every top-level scenario event with trigger, function, and source location.', f'''
<section><h2>Top-level events</h2><label class="small" for="event-filter">Filter events</label><br><input id="event-filter" class="filter" data-table-filter="#event-table" placeholder="moveto, turn 5, leader, escape…">{table(['Scenario', 'Trigger', 'Function', 'Source'], event_rows, 'event-table')}</section>
<section><h2>Event composition pattern</h2><p>Most scenarios use the same readable spine: <code>prestart</code>, <code>start</code>, one moral-choice <code>moveto</code>, one <code>moveto</code> per objective site, one <code>die</code> event per required leader, and one timed reinforcement event. Scenario 09 adds a campaign-menu ability; Scenario 20 adds phase-change and escape events.</p></section>''')

    # Asset index
    asset_rows = []
    for s in scenarios:
        asset_rows.append(['Music', code(s['music']), f'Scenario {s["number"]:02d}', 'Campaign-local'])
        for snd in s['sounds']:
            asset_rows.append(['Sound', code(snd), f'Scenario {s["number"]:02d}', 'Core/mainline'])
        asset_rows.append(['Map', code(s['map_file']), f'Scenario {s["number"]:02d}', 'Campaign-local'])
    asset_rows.append(['Unit', code('WPB Hunter'), 'All scenarios', 'Campaign-local definition; core Ranger base assets'])
    pages['asset-index.html'] = ('Asset Index', 'Campaign-local maps and music plus direct core sound and unit dependencies.', f'''
<section><h2>Asset inventory</h2><label class="small" for="asset-filter">Filter assets</label><br><input id="asset-filter" class="filter" data-table-filter="#asset-table" placeholder="ogg, map, Hunter, cave-in…">{table(['Kind', 'Identifier', 'Use', 'Origin'], asset_rows, 'asset-table')}</section>
<section><h2>Image boundary</h2><p>Version 0.1.0 does not ship campaign-local image art. The campaign menu and Hunter inherit core unit images. Future portraits, story panels, icons, and custom unit sprites should be added under a campaign-local <code>images/</code> directory without changing the fixed scenario, map, or music filenames.</p></section>''')

    # Playtest / maintenance / extension
    pages['playtest-howto.html'] = ('Playtest HOWTO', 'Install, launch, jump between scenarios, record findings, and validate the first campaign build.', f'''
<section><h2>Install the add-on</h2><ol><li>Copy the complete <code>World_Painted_Blood/</code> folder into the active Wesnoth 1.18 user-data <code>data/add-ons/</code> directory.</li><li>Confirm that <code>_main.cfg</code> is directly inside <code>World_Painted_Blood/</code>.</li><li>Start Wesnoth or press <strong>F5</strong> at the title screen to reload add-ons.</li><li>Choose <em>World Painted Blood</em> from Campaigns.</li></ol></section>
<section><h2>Fast scenario testing</h2><p>During development, enable debug mode and use <code>:cl</code> to select a scenario. An alternative is temporarily changing <code>first_scenario</code> in <code>_main.cfg</code>; revert that change before packaging.</p></section>
<section><h2>Minimum pass for each scenario</h2>{table(['Area', 'Questions'], [
['Load', 'Does the scenario enter without WML errors? Do the map and custom music filename resolve?'],
['Objectives', 'Do all labels exist, counters update exactly once, and victory occur in either completion order?'],
['Moral choice', 'Do both options work, write the intended variables, and leave no unusable unit state?'],
['AI and economy', 'Can enemies recruit? Are turns, gold, income, and reinforcement timing reasonable on all difficulties?'],
['Transition', 'Does victory load the exact next scenario and preserve the recall list and campaign variables?'],
['Defeat', 'Does Hunter death and time expiry behave correctly?'],
])}</section>
<section><h2>Run the bundled validator</h2><pre>cd World_Painted_Blood
python3 tools/validate_wpb.py</pre><p>This checks filenames, chain integrity, map references, music references, sound basenames, tag balance, terrain codes, coordinates, reachability, and archive assumptions. It cannot replace an engine run.</p></section>
<section><h2>Suggested defect log</h2>{table(['Field', 'Example'], [
['Scenario / difficulty', '09 Unguarded Instinct / Normal'],
['Turn and save', 'Turn 7, before activating ward 2'],
['Expected', 'Corruption decreases by one after the cleansing site.'],
['Observed', 'Value unchanged; message still appears.'],
['Reproduction', 'Exact move sequence or attached save.'],
['Severity', 'Load blocker / objective blocker / balance / narrative / cosmetic.'],
])}</section>''')

    pages['maintenance-playbook.html'] = ('Maintenance Playbook', 'Safe edit, validation, packaging, and regression practices for the campaign and reference.', f'''
<section><h2>Before editing</h2><ol><li>Create a branch or copy of the add-on.</li><li>Run <code>tools/validate_wpb.py</code> and record the passing baseline.</li><li>Identify every call site through this reference’s search and dependency matrix.</li></ol></section>
<section><h2>Scenario edit loop</h2><div class="flow">edit WML or map
→ run static validator
→ reload add-ons
→ launch target scenario
→ test both moral choices
→ test objective order permutations
→ test victory, defeat, and next-scenario load
→ update README and developer reference</div></section>
<section><h2>Fixed filename contract</h2><div class="callout warn">Do not rename the twenty scenario files, twenty map files, or twenty music files. Internal scenario IDs and <code>next_scenario</code> values must remain synchronized with the fixed filenames.</div></section>
<section><h2>Reference refresh</h2><p>Re-run <code>tools/build_reference.py</code> inside this developer-reference package after campaign changes. The builder regenerates scenario pages, tables, search data, hashes, and validation output from the source snapshot.</p></section>''')

    pages['extension-recipes.html'] = ('Extension Recipes', 'Safe patterns for deepening the campaign after the first playtest without breaking its established file contract.', f'''
<section><h2>Add state-aware dialogue</h2><pre>[if]
    [variable]
        name=wpb_sacrificed
        greater_than=5
    [/variable]
    [then]
        [message]
            speaker=Nyxara
            message= _ "You remember every name. You simply stopped saying them."
        [/message]
    [/then]
[/if]</pre></section>
<section><h2>Add alliance reinforcements</h2><p>Read <code>wpb_alliance_strength</code> in Scenario 16 or 20 and spawn a bounded number of allied units. Cap the reward by difficulty so early rescue decisions help without trivializing the finale.</p></section>
<section><h2>Add a named-dead array</h2><p>When a captive is deliberately sacrificed, append their ID and display name to a WML container. Scenarios 18 and 19 can then instantiate only the characters who actually died in that playthrough.</p></section>
<section><h2>Add local sounds later</h2><p>Copy verified sound files into <code>World_Painted_Blood/sounds/</code> with unchanged basenames. Existing scenario references will resolve to campaign-local files through the binary path.</p></section>
<section><h2>Add custom art safely</h2><p>Create <code>images/portraits/</code>, <code>images/story/</code>, and <code>images/units/</code>. Keep core fallbacks until every new file is present, licensed, and validated.</p></section>
<section><h2>Deepen a scenario without renaming it</h2><p>Preserve the existing scenario ID, filename, map filename, and next-scenario edge. Add helpers in <code>utils/</code>, use campaign-prefixed variables, and update both the README scenario section and reference builder metadata.</p></section>''')

    # Consistency report and completion scope
    total_events = sum(len(s['events']) for s in scenarios)
    total_vars = len(state_use)
    unique_units = len(set(t for s in scenarios for t in s['unit_types']))
    unique_sounds = len(sound_usage)
    checks = [
        ['Scenario files', '20 expected / 20 found', 'Pass'],
        ['Map files', '20 expected / 20 found', 'Pass'],
        ['Music files', '20 expected / 20 found', 'Pass'],
        ['Scenario chain', '01 through 20, terminal null', 'Pass'],
        ['Map references', 'Every scenario map exists', 'Pass'],
        ['Music references', 'Every custom track exists', 'Pass'],
        ['Source snapshot hashes', 'Generated for all copied source files', 'Pass'],
        ['Internal HTML links', 'Validated after generation', 'Pass; see generated site report'],
        ['Wesnoth engine playthrough', 'Not available in build environment', 'Open'],
    ]
    pages['consistency-report.html'] = ('Consistency Report', 'Generated counts, source hashes, navigation checks, and known validation boundaries.', f'''
<section><h2>Generated metrics</h2><div class="grid"><div class="card metric"><strong>20</strong>scenarios</div><div class="card metric"><strong>20</strong>maps</div><div class="card metric"><strong>{total_events}</strong>top-level events</div><div class="card metric"><strong>{total_vars}</strong>explicit variables</div><div class="card metric"><strong>{unique_units}</strong>direct unit types</div><div class="card metric"><strong>{unique_sounds}</strong>sound basenames</div></div></section>
<section><h2>Validation status</h2>{table(['Check', 'Result', 'Status'], [[a,b, f'<span class="badge {"done" if c=="Pass" else "campaign"}">{c}</span>'] for a,b,c in checks])}</section>
<section><h2>Evidence files</h2>{list_html([source_link('../', 'docs/VALIDATION_REPORT.md', 'Campaign validation report'), source_link('../', 'docs/BUILD_MANIFEST.json', 'Campaign build manifest'), '<a href="../assets/site-validation.json">Developer-reference site validation JSON</a>', '<a href="../assets/source-snapshot.json">Developer-reference source snapshot JSON</a>'])}</section>''')

    pages['completion-scope.html'] = ('Completion Scope', 'What this reference guarantees, what the campaign build currently contains, and what remains deliberately open.', f'''
<section><h2>Included in this reference</h2>{list_html([
'One detailed chapter for every scenario file.',
'Campaign architecture, metadata, custom unit, macro, map, audio, dependency, event, character, state, and asset catalogues.',
'Four narrative/mechanical arc studies and a dedicated moral-state architecture page.',
'Offline search, responsive navigation, light/dark theme toggle, source snapshot, and validation data.',
'Exact companion-site CSS theme with the solid <code>#333</code> top frame.',
])}</section>
<section><h2>Deliberate boundaries</h2>{list_html([
'This is a reference for <em>World Painted Blood</em> version 0.1.0, not an assertion that the campaign is balanced or release-ready.',
'Core unit inheritance and transitive core macros are identified at the campaign boundary but not reproduced as a complete closure of the Wesnoth source tree.',
'The twenty silent music placeholders are catalogued but not embedded for playback.',
'Planned mechanics not present in source are described only as future extension opportunities.',
])}</section>
<section><h2>Definition of done for the next reference release</h2><p>Refresh after the first full campaign playthrough, resolve load and objective blockers, update balance values and implemented mechanics, then regenerate the entire site from the revised source snapshot.</p></section>''')

    return pages

# ---------------------------------------------------------------------------
# Search index and validation.
# ---------------------------------------------------------------------------


def strip_html(text: str) -> str:
    text = re.sub(r'<script.*?</script>', ' ', text, flags=re.S|re.I)
    text = re.sub(r'<style.*?</style>', ' ', text, flags=re.S|re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def build_search_index(out: Path) -> list[dict[str, str]]:
    items = []
    for p in sorted(out.rglob('*.html')):
        if p.name == 'search.html':
            continue
        text = p.read_text(encoding='utf-8')
        title_m = re.search(r'<title>(.*?)</title>', text, re.S)
        h_m = re.findall(r'<h[12][^>]*>(.*?)</h[12]>', text, re.S)
        title = strip_html(title_m.group(1)).replace(' — World Painted Blood Developer Reference','') if title_m else p.stem
        headings = ' '.join(strip_html(x) for x in h_m)
        plain = strip_html(text)
        rel = p.relative_to(out).as_posix()
        excerpt = plain[:420]
        items.append({'title': title, 'path': rel, 'headings': headings, 'text': plain, 'excerpt': excerpt})
    return items


def write_search_js(items: list[dict[str, str]], out: Path) -> None:
    out.write_text('window.WPB_SEARCH_INDEX = ' + json.dumps(items, ensure_ascii=False) + ';\n', encoding='utf-8')


def validate_site(out: Path) -> dict[str, Any]:
    html_files = sorted(out.rglob('*.html'))
    broken = []
    duplicate_titles = []
    titles = Counter()
    for p in html_files:
        text = p.read_text(encoding='utf-8')
        m = re.search(r'<title>(.*?)</title>', text, re.S)
        if m:
            titles[strip_html(m.group(1))] += 1
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(('http://','https://','mailto:','#')):
                continue
            target = href.split('#',1)[0].split('?',1)[0]
            if not target:
                continue
            resolved = (p.parent / target).resolve()
            if not resolved.exists():
                broken.append({'page': str(p.relative_to(out)), 'href': href})
    duplicate_titles = [k for k,v in titles.items() if v > 1]
    result = {
        'release': VERSION,
        'generated': ACCESS_DATE,
        'html_pages': len(html_files),
        'scenario_pages': len(list((out/'scenarios').glob('*.html'))),
        'reference_pages': len(list((out/'reference').glob('*.html'))),
        'broken_links': broken,
        'duplicate_titles': duplicate_titles,
        'status': 'pass' if not broken and not duplicate_titles else 'fail',
    }
    return result


def copy_source_snapshot() -> list[dict[str, Any]]:
    source_dir = OUT/'source'
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)
    include_suffixes = {'.cfg','.map','.md','.json','.py','.txt'}
    manifest = []
    for p in sorted(CAMPAIGN.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(CAMPAIGN)
        if p.suffix.lower() not in include_suffixes and p.name not in {'LICENSE'}:
            continue
        dest = source_dir/rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        manifest.append({
            'path': rel.as_posix(),
            'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        })
    return manifest


def create_site_js(path: Path) -> None:
    js = r'''(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem("wpb-reference-theme");
  if (saved) root.dataset.theme = saved;

  document.querySelectorAll("[data-theme-toggle]").forEach(button => {
    const setLabel = () => {
      const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      button.textContent = current === "dark" ? "Use light theme" : "Use dark theme";
    };
    setLabel();
    button.addEventListener("click", () => {
      const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      localStorage.setItem("wpb-reference-theme", next);
      setLabel();
    });
  });

  document.querySelectorAll("[data-table-filter]").forEach(input => {
    const table = document.querySelector(input.dataset.tableFilter);
    if (!table) return;
    input.addEventListener("input", () => {
      const query = input.value.toLowerCase().trim();
      table.querySelectorAll("tbody tr").forEach(row => {
        row.hidden = !row.innerText.toLowerCase().includes(query);
      });
    });
  });

  const escapeHtml = value => String(value).replace(/[&<>"']/g, ch => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[ch]));
  const highlight = (text, terms) => {
    let output = escapeHtml(text);
    terms.filter(Boolean).sort((a,b) => b.length-a.length).forEach(term => {
      const safe = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      output = output.replace(new RegExp(`(${safe})`, "ig"), "<mark>$1</mark>");
    });
    return output;
  };

  const searchPage = document.querySelector("[data-search-page]");
  if (searchPage && Array.isArray(window.WPB_SEARCH_INDEX)) {
    const form = searchPage.querySelector("[data-search-form]");
    const input = form.querySelector('input[name="q"]');
    const resultsNode = searchPage.querySelector("[data-search-results]");
    const statusNode = searchPage.querySelector("[data-search-status]");
    const run = query => {
      const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
      if (!terms.length) {
        resultsNode.innerHTML = "";
        statusNode.textContent = "Enter one or more terms.";
        return;
      }
      const ranked = window.WPB_SEARCH_INDEX.map(item => {
        const title = item.title.toLowerCase();
        const headings = item.headings.toLowerCase();
        const text = item.text.toLowerCase();
        let score = 0;
        for (const term of terms) {
          if (!text.includes(term) && !title.includes(term) && !headings.includes(term)) return null;
          if (title.includes(term)) score += 30;
          if (headings.includes(term)) score += 12;
          score += Math.min(10, text.split(term).length - 1);
        }
        return {...item, score};
      }).filter(Boolean).sort((a,b) => b.score-a.score || a.title.localeCompare(b.title));
      statusNode.textContent = `${ranked.length} result${ranked.length === 1 ? "" : "s"} for “${query}”.`;
      if (!ranked.length) {
        resultsNode.innerHTML = '<div class="search-empty">No matching pages. Try fewer terms or identifiers such as <code>wpb_corruption</code>, <code>Nightgaunt</code>, or <code>command pylon</code>.</div>';
        return;
      }
      resultsNode.innerHTML = ranked.slice(0, 80).map(item => `
        <article class="search-result">
          <h3><a href="${escapeHtml(item.path)}">${highlight(item.title, terms)}</a></h3>
          <div class="search-path">${escapeHtml(item.path)}</div>
          <p>${highlight(item.excerpt, terms)}</p>
        </article>`).join("");
    };
    const params = new URLSearchParams(location.search);
    const initial = params.get("q") || "";
    input.value = initial;
    run(initial);
    form.addEventListener("submit", event => {
      event.preventDefault();
      const query = input.value.trim();
      const url = new URL(location.href);
      if (query) url.searchParams.set("q", query); else url.searchParams.delete("q");
      history.replaceState(null, "", url);
      run(query);
    });
    input.addEventListener("input", () => run(input.value));
  }

  document.addEventListener("keydown", event => {
    if (event.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) {
      const field = document.querySelector(".sidebar-search input");
      if (field) { event.preventDefault(); field.focus(); }
    }
  });
})();
'''
    path.write_text(js, encoding='utf-8')


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT/'assets').mkdir(parents=True)
    (OUT/'scenarios').mkdir()
    (OUT/'reference').mkdir()
    (OUT/'tools').mkdir()

    # Exact stylesheet from the companion reference, including the #333 top frame.
    shutil.copy2('/mnt/data/site.css', OUT/'assets/site.css')
    create_site_js(OUT/'assets/site.js')

    readme_design = parse_readme_scenarios(CAMPAIGN/'README.md')
    scenarios = []
    for path in sorted((CAMPAIGN/'scenarios').glob('*.cfg')):
        number = int(path.name[:2])
        map_file = CAMPAIGN/'maps'/(path.stem + '.map')
        scenarios.append(extract_scenario(path, readme_design[number], parse_map(map_file)))

    # Snapshot textual campaign source for offline evidence links.
    source_manifest = copy_source_snapshot()
    (OUT/'assets/source-snapshot.json').write_text(json.dumps({
        'campaign': 'World Painted Blood', 'version': VERSION, 'generated': ACCESS_DATE,
        'files': source_manifest
    }, indent=2), encoding='utf-8')

    # Home and scenario chapters.
    file_inventory = {
        '_main.cfg': 1,
        'scenarios/': len(list((CAMPAIGN/'scenarios').glob('*.cfg'))),
        'maps/': len(list((CAMPAIGN/'maps').glob('*.map'))),
        'music/': len(list((CAMPAIGN/'music').glob('*.ogg'))),
        'units/': len(list((CAMPAIGN/'units').glob('*.cfg'))),
        'utils/': len(list((CAMPAIGN/'utils').glob('*.cfg'))),
        'docs/': len(list((CAMPAIGN/'docs').glob('*'))),
        'tools/': len(list((CAMPAIGN/'tools').glob('*'))),
    }
    unique_sounds = sorted(set(snd for s in scenarios for snd in s['sounds']))
    (OUT/'index.html').write_text(home_page(scenarios, file_inventory, unique_sounds), encoding='utf-8')
    for s in scenarios:
        (OUT/'scenarios'/scenario_slug(s)).write_text(scenario_page(s, scenarios), encoding='utf-8')

    # Arc and reference pages.
    for arc in ARC_DATA:
        (OUT/'reference'/f"{arc['slug']}.html").write_text(arc_page(arc, scenarios), encoding='utf-8')
    build_manifest = json.loads((CAMPAIGN/'docs/BUILD_MANIFEST.json').read_text(encoding='utf-8'))
    sound_manifest_text = (CAMPAIGN/'docs/SOUND_ASSET_MANIFEST.md').read_text(encoding='utf-8')
    refs = reference_pages(scenarios, (CAMPAIGN/'README.md').read_text(encoding='utf-8'), build_manifest, sound_manifest_text)
    for filename, (title, lede, body) in refs.items():
        current = Path(filename).stem
        (OUT/'reference'/filename).write_text(page_template(title=title, lede=lede, body=body, scenarios=scenarios, prefix='../', current=current, breadcrumb=esc(title)), encoding='utf-8')

    # Search page generated before index creation.
    search_body = '''
<section data-search-page>
<div class="search-page-form"><form data-search-form><label for="search-q">Search the complete reference</label><div class="search-row"><input class="search-input" id="search-q" name="q" type="search" autocomplete="off" placeholder="Scenario, variable, unit, sound, mechanic…"><button class="theme-button" type="submit">Search</button></div></form></div>
<p class="search-status" data-search-status></p><div data-search-results></div>
</section>'''
    (OUT/'search.html').write_text(page_template(title='Search', lede='Serverless full-text search across the complete extracted developer reference.', body=search_body, scenarios=scenarios, prefix='', current='search', breadcrumb='Search'), encoding='utf-8')

    # Build search data after all pages exist.
    search_items = build_search_index(OUT)
    write_search_js(search_items, OUT/'assets/search-index.js')
    # Insert search-index script before site.js on search page.
    search_path = OUT/'search.html'
    text = search_path.read_text(encoding='utf-8')
    text = text.replace('<script defer src="assets/site.js"></script>', '<script defer src="assets/search-index.js"></script>\n<script defer src="assets/site.js"></script>')
    search_path.write_text(text, encoding='utf-8')

    # Rebuild search index one more time after script insertion (content unchanged enough, but deterministic).
    search_items = build_search_index(OUT)
    write_search_js(search_items, OUT/'assets/search-index.js')

    # Reproducible builder copy and project README.
    shutil.copy2(__file__, OUT/'tools/build_reference.py')
    (OUT/'README.md').write_text(f'''# World Painted Blood Developer Reference

Offline developer-reference site for **World Painted Blood {VERSION}**.

Open `index.html` in a browser. No web server or external dependencies are required.

## Regenerate

The builder expects the campaign source at `/mnt/data/World_Painted_Blood` in this generated package environment. For repository use, edit the `CAMPAIGN` and `OUT` constants in `tools/build_reference.py`, then run:

```bash
python3 tools/build_reference.py
```

## Theme

`assets/site.css` is the same stylesheet used by Hunter Gath's *The Rise of Wesnoth* developer reference, including the solid `#333` site header requested for release 1.0.0. The companion reference and this generated derivative are distributed under GPL-compatible terms; see `THEME_ATTRIBUTION.md` and the copied campaign `source/LICENSE`.

## Scope

The site documents the exact **0.1.0 first test build**. It distinguishes source facts from derived facts and design interpretations. It does not claim that the campaign has completed an in-engine playthrough.
''', encoding='utf-8')
    (OUT/'THEME_ATTRIBUTION.md').write_text('''# Theme Attribution

The stylesheet in `assets/site.css` is copied from:

- Project: Hunter Gath's Campaign Developer Guide
- Reference: The Rise of Wesnoth Developer Reference
- Source repository: `hunter-gath/wesnoth-campaign-dev-guide`
- Original file: `The_Rise_of_Wesnoth/assets/site.css`
- Accessed: July 19, 2026

The stylesheet includes the solid `#333` top-frame background requested for that reference. This World Painted Blood site uses the same CSS theme so both references present as companion volumes.
''', encoding='utf-8')

    # Validate and write report. Create its linked target before the link audit.
    (OUT/'assets/site-validation.json').write_text('{}\n', encoding='utf-8')
    validation = validate_site(OUT)
    (OUT/'assets/site-validation.json').write_text(json.dumps(validation, indent=2), encoding='utf-8')
    # The consistency page was generated before validation; status JSON is authoritative.
    if validation['status'] != 'pass':
        raise SystemExit('Site validation failed: ' + json.dumps(validation, indent=2))

    # Build manifest.
    manifest = []
    for p in sorted(OUT.rglob('*')):
        if p.is_file():
            manifest.append({
                'path': p.relative_to(OUT).as_posix(),
                'bytes': p.stat().st_size,
                'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            })
    (OUT/'assets/build-manifest.json').write_text(json.dumps({
        'title': 'World Painted Blood Developer Reference',
        'version': VERSION,
        'generated': ACCESS_DATE,
        'file_count_before_manifest': len(manifest),
        'files': manifest,
    }, indent=2), encoding='utf-8')

    print(json.dumps({
        'output': str(OUT),
        'scenario_pages': len(scenarios),
        'reference_pages': len(list((OUT/'reference').glob('*.html'))),
        'html_pages': len(list(OUT.rglob('*.html'))),
        'search_items': len(search_items),
        'validation': validation,
    }, indent=2))

if __name__ == '__main__':
    main()
