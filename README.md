---
title: "Hunter Gath's Campaign Developer Guide for The Battle for Wesnoth"
subtitle: "Creating, testing, and committing a new campaign on Xubuntu / Ubuntu 26.04 LTS"
author: "Hunter Gath"
lang: en-US
date: "2026-07-08"
---

# Table of Contents

1. [About this guide](#about-this-guide)
2. [Chapter 1: What a campaign coder works with](#chapter-1-what-a-campaign-coder-works-with)
3. [Chapter 2: Tools, languages, and setup on Xubuntu 26.04](#chapter-2-tools-languages-and-setup-on-xubuntu-2604)
4. [Chapter 3: Campaign anatomy](#chapter-3-campaign-anatomy)
5. [Chapter 4: Tutorial — Hunter Gath](#chapter-4-tutorial--hunter-gath)
6. [Chapter 5: Testing, debugging, and maintenance](#chapter-5-testing-debugging-and-maintenance)
7. [Chapter 6: Moving from an add-on to a forked Wesnoth branch](#chapter-6-moving-from-an-add-on-to-a-forked-wesnoth-branch)
8. [Appendix A: Complete Hunter Gath file listing](#appendix-a-complete-hunter-gath-file-listing)
9. [Appendix B: Preflight checklist](#appendix-b-preflight-checklist)
10. [References](#references)

# About this guide

This document is a practical campaign-development manual for **The Battle for Wesnoth**, focused on one task: getting a new single-player campaign functional. It is written for **Xubuntu / Ubuntu 26.04 LTS** and assumes you want to work against a fork of the official Wesnoth repository while also testing your campaign as a local add-on during development.

The tutorial campaign is called **Hunter Gath**. It is intentionally small: two scenarios, two maps, one custom unit, a few utility macros, placeholder images, story screens, objectives, dialogue, music references, and add-on server metadata. That small scope is deliberate. A campaign coder needs to understand the whole pipeline before writing twenty scenarios.

The layout mirrors the official manual style in a lightweight way: chapters first, tutorial second, appendices and references last. It does **not** replace the official wiki or repository documentation. Instead, it gives you a working path through the parts of the documentation that matter when you are creating a campaign.

## Assumptions

- You are comfortable using a terminal.
- You can edit text files with VS Code, Vim, Kate, Mousepad, or another UTF-8 capable editor.
- You know basic Git: clone, branch, commit, push, and pull request.
- You are making a single-player campaign first. Multiplayer campaigns add more constraints and are outside the main path here.

## Add-on first, mainline later

During early development, build the campaign as a **user add-on** under your Wesnoth userdata directory. This gives you quick load-test cycles and keeps the game repository clean. When the campaign is ready to propose for inclusion in the game tree, copy or move it to `data/campaigns/Hunter_Gath` in your fork and adjust include paths.

# Chapter 1: What a campaign coder works with

Wesnoth is not only a C++ game engine. It is also a large content platform. Campaign coders normally spend most of their time in **WML**, maps, data files, and asset directories rather than C++.

## Repository areas you should recognize

A campaign contributor should know these parts of the repository:

| Path | What it is | Why campaign coders care |
|---|---|---|
| `src/` | C++ engine code | Usually read-only for campaign work. You may inspect it when engine behavior is unclear. |
| `data/core/` | Core units, macros, images, terrain, eras, help data | Your campaign reuses core unit IDs, macros, terrain strings, attacks, sounds, and images. |
| `data/campaigns/` | Mainline campaign directories | This is where a campaign goes when it is included in the game source tree. Study existing campaigns here. |
| `data/tools/` | WML maintenance tools such as `wmlindent`, `wmllint`, `wmlscope`, and extraction tools | Use these before committing. Wesnoth CI checks WML formatting. |
| `doc/manual/` | Official manual source and generated manual files | Useful for style, organization, and user-facing language. |
| `po/` | Translation catalogs | You do not edit these for initial campaign prototyping, but your strings should be translation-ready. |
| `images/`, `music/`, `sounds/` | Shared game assets | Campaigns may reference core assets or provide campaign-local assets. |

## Where a local campaign add-on lives

On Linux, Wesnoth uses a per-user data directory. The exact versioned directory depends on the Wesnoth build you are running. Confirm it with:

```bash
wesnoth --config-path
```

A typical path is:

```text
~/.local/share/wesnoth/<version>/data/add-ons/
```

For this guide, the local add-on directory is:

```text
~/.local/share/wesnoth/<version>/data/add-ons/Hunter_Gath/
```

The same campaign, if moved into the game source tree for a fork, would live at:

```text
wesnoth/data/campaigns/Hunter_Gath/
```

## Campaign development languages

### WML

**WML** is the main campaign scripting language. You use it for campaign metadata, scenarios, sides, units, events, objectives, story screens, variables, and much of the glue between gameplay and assets.

WML looks simple, but it is strict about tag structure, paths, IDs, and preprocessor macros. Most campaign bugs are not clever programming bugs; they are path mistakes, missing IDs, missing closing tags, wrong macro arguments, or side/team errors.

### Lua

Lua is available for advanced logic. You do not need it for Hunter Gath. Learn WML first; reach for Lua when WML becomes awkward, not as a default.

### C++

The engine is C++17. Campaign coders rarely need C++, but source builds matter because you may need to run the latest development version, use the latest schema/tools, or test a branch exactly as CI will see it.

### Gettext-style translatable strings

User-facing campaign strings should be marked for translation with the `_` marker:

```wml
name= _ "Hunter Gath"
message= _ "The trail goes dark."
```

Keep text in UTF-8 and use US English in this guide's first pass.

# Chapter 2: Tools, languages, and setup on Xubuntu 26.04

This chapter gives you two setup tracks:

1. **Content-only track** — install Wesnoth and build the add-on in your userdata directory.
2. **Contributor track** — clone your fork of the Wesnoth repository, build the game from source, and commit your campaign to a branch.

For serious contribution work, use both.

## Install basic development tools

```bash
sudo apt update
sudo apt install \
  build-essential git cmake ninja-build pkg-config gettext python3 python3-pip \
  python3-pil scons curl ca-certificates
```

## Install Wesnoth source-build dependencies

The exact package set can change as Ubuntu packages move. On Ubuntu 26.04, start with:

```bash
sudo apt install \
  libboost-all-dev \
  libsdl3-dev libsdl3-image-dev libsdl3-mixer-dev \
  libfontconfig1-dev libcairo2-dev libpango1.0-dev \
  libvorbis-dev libbz2-dev zlib1g-dev \
  libssl-dev libcurl4-openssl-dev \
  libdbus-1-dev libreadline-dev
```

If `apt` cannot find a package, search for its current name:

```bash
apt search libsdl3
apt search libboost
```

The official `INSTALL.md` is the authority for required library versions. As of the referenced repository version, Wesnoth requires a C++17-capable compiler, Boost, SDL3, SDL3_image, SDL3_mixer, Fontconfig, Cairo, Pango, Vorbisfile, compression libraries, OpenSSL, libcurl, and gettext for translations.

## Install or run Wesnoth

For add-on-only testing, the packaged game may be enough:

```bash
sudo apt install wesnoth
wesnoth --version
wesnoth --config-path
wesnoth --path
```

For repository work, clone your fork with submodules:

```bash
mkdir -p ~/src
cd ~/src
git clone --recurse-submodules git@github.com:YOUR-GITHUB-NAME/wesnoth.git
cd wesnoth
git remote add upstream https://github.com/wesnoth/wesnoth.git
git fetch upstream
```

Build with CMake and Ninja:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build
```

Run the binary from the build tree. Depending on the build configuration, this is usually:

```bash
./build/wesnoth --version
./build/wesnoth --config-path
```

If the executable path differs, find it:

```bash
find build -type f -executable -name 'wesnoth*' -maxdepth 3
```

## Recommended editor setup

Use any editor that preserves UTF-8 and Unix line endings. Recommended conveniences:

- Show whitespace and line endings.
- Use four spaces for WML indentation.
- Add syntax highlighting for `.cfg` files if your editor supports WML or INI-like highlighting.
- Keep a terminal open beside the editor to launch Wesnoth and read WML errors.

## Learn enough of these tools

| Tool | Minimum useful skill |
|---|---|
| `git` | Fork, branch, commit, rebase or merge from upstream, push, open PR. |
| `cmake` / `ninja` | Build the game from a clean checkout. |
| `wesnoth --config-path` | Locate your userdata directory. |
| `wesnoth --path` | Locate the game data directory being used by this executable. |
| `data/tools/wmlindent` | Format WML before committing. |
| `data/tools/wmllint` | Catch common WML maintenance issues. |
| Wesnoth map editor | Create `.map` files visually, then save them into `maps/`. |
| Image editor | Crop/export PNGs for portraits, story art, icons, and unit art. |

# Chapter 3: Campaign anatomy

A campaign is a set of WML files and assets loaded through one entry file, `_main.cfg`.

## Minimal campaign directory

```text
Hunter_Gath/
├── _main.cfg
├── _server.pbl
├── scenarios/
│   ├── 01_Goblin_Trail.cfg
│   └── 02_River_Poachers.cfg
├── maps/
│   ├── 01_Goblin_Trail.map
│   └── 02_River_Poachers.map
├── units/
│   └── HG_Hunter.cfg
├── utils/
│   └── hg-utils.cfg
├── images/
│   ├── misc/
│   │   └── hunter-gath-icon.png
│   ├── portraits/
│   │   └── hunter-gath.png
│   └── story/
│       └── hunter-gath-forest.png
├── music/
├── sounds/
└── translations/
```

## `_main.cfg`

The `_main.cfg` file is the add-on entry point. Without it, Wesnoth will not recognize the add-on.

For a campaign, `_main.cfg` usually does these jobs:

1. Declares a textdomain for translatable strings.
2. Defines the `[campaign]` menu entry.
3. Provides a unique preprocessor symbol such as `CAMPAIGN_HUNTER_GATH`.
4. Adds a `[binary_path]` so images, maps, music, and sounds can be found.
5. Includes utility macros, units, and scenarios only when the campaign is selected.

## `scenarios/`

Each scenario has an ID, a map, sides, objectives, events, and a next scenario. Scenario IDs are code identifiers; scenario names are user-facing strings.

## `maps/`

Maps are usually created in the map editor. Scenario files reference maps with:

```wml
map_file=01_Goblin_Trail.map
```

The engine finds the map through the campaign's binary path.

## `units/`

Custom units are loaded inside a `[units]` block. For add-ons, do not include the `units/` directory with a plain include alone; wrap it:

```wml
[units]
    {~add-ons/Hunter_Gath/units}
[/units]
```

## `utils/`

Put campaign-local macros here. Keep macros small, documented, and named with a campaign prefix to reduce collisions. Hunter Gath uses `HG_GOLD` and `HG_INCOME`.

## `images/`, `music/`, and `sounds/`

Images, music, and sounds do not need WML include lines in `_main.cfg`. They are referenced by path after `[binary_path]` is set.

For example:

```wml
image="portraits/hunter-gath.png"
background="story/hunter-gath-forest.png"
```

## `_server.pbl`

The `.pbl` file is add-on server metadata. It is needed if you upload the add-on through Wesnoth's add-on publishing system. Keep the passphrase private. Do not commit real credentials into a public repository.

# Chapter 4: Tutorial — Hunter Gath

This tutorial creates the campaign as a local add-on first. The sample code that accompanies this guide already contains the finished version.

## Step 1: Find your Wesnoth userdata directory

Run:

```bash
wesnoth --config-path
```

Set a shell variable using your actual path:

```bash
export WESNOTH_USERDATA="$HOME/.local/share/wesnoth/<version>"
export ADDON="$WESNOTH_USERDATA/data/add-ons/Hunter_Gath"
```

Create the directory tree:

```bash
mkdir -p "$ADDON"/{scenarios,maps,units,utils,music,sounds,translations,tools}
mkdir -p "$ADDON"/images/{misc,portraits,story}
```

## Step 2: Create `_main.cfg`

Create:

```text
$ADDON/_main.cfg
```

Use this content:

```wml
#textdomain wesnoth-Hunter_Gath

[textdomain]
    name="wesnoth-Hunter_Gath"
    path="data/add-ons/Hunter_Gath/translations"
[/textdomain]

[campaign]
    id=Hunter_Gath
    rank=999
    type=sp
    name= _ "Hunter Gath"
    abbrev= _ "HG"
    define=CAMPAIGN_HUNTER_GATH
    icon="misc/hunter-gath-icon.png"
    image="portraits/hunter-gath.png"
    background="story/hunter-gath-forest.png"
    first_scenario=01_Goblin_Trail
    description= _ "A compact sample campaign for learning how Wesnoth campaigns are assembled: add-on metadata, WML, maps, custom units, events, objectives, images, and Git workflow."

    [difficulty]
        define=EASY
        image="units/human-loyalists/bowman.png~RC(magenta>green)"
        label= _ "Tracker"
        description= _ "Easy"
    [/difficulty]
    [difficulty]
        define=NORMAL
        image="units/human-outlaws/trapper.png~RC(magenta>green)"
        label= _ "Hunter"
        description= _ "Normal"
        default=yes
    [/difficulty]
    [difficulty]
        define=HARD
        image="units/orcs/goblin-spearman.png~RC(magenta>green)"
        label= _ "Stalker"
        description= _ "Hard"
    [/difficulty]

    [about]
        title= _ "Campaign design and WML"
        [entry]
            name="Your Name"
            comment= _ "Replace this credit before publishing or proposing the campaign."
        [/entry]
    [/about]
[/campaign]

#ifdef CAMPAIGN_HUNTER_GATH
[binary_path]
    path=data/add-ons/Hunter_Gath
[/binary_path]

{~add-ons/Hunter_Gath/utils}

[units]
    {~add-ons/Hunter_Gath/units}
[/units]

{~add-ons/Hunter_Gath/scenarios}
#endif
```

Important pieces to notice:

- `id=Hunter_Gath` is the internal campaign ID.
- `define=CAMPAIGN_HUNTER_GATH` controls what loads after the campaign is selected.
- `first_scenario=01_Goblin_Trail` must match the first scenario's `id`.
- `[binary_path] path=data/add-ons/Hunter_Gath` lets WML find local maps and images.
- `{~add-ons/Hunter_Gath/scenarios}` includes all scenario files in that directory.

## Step 3: Create utility macros

Create:

```text
$ADDON/utils/hg-utils.cfg
```

Use this content:

```wml
#textdomain wesnoth-Hunter_Gath

# Small campaign-local helpers.
# Keep utility macros in this file so scenarios stay readable.

#define HG_GOLD EASY_AMOUNT NORMAL_AMOUNT HARD_AMOUNT
#ifdef EASY
    gold={EASY_AMOUNT}
#endif
#ifdef NORMAL
    gold={NORMAL_AMOUNT}
#endif
#ifdef HARD
    gold={HARD_AMOUNT}
#endif
#enddef

#define HG_INCOME EASY_AMOUNT NORMAL_AMOUNT HARD_AMOUNT
#ifdef EASY
    income={EASY_AMOUNT}
#endif
#ifdef NORMAL
    income={NORMAL_AMOUNT}
#endif
#ifdef HARD
    income={HARD_AMOUNT}
#endif
#enddef
```

The macros expand to different `gold=` and `income=` keys depending on the selected difficulty. Keeping this logic in `utils/` makes scenario files easier to read.

## Step 4: Create a custom unit

Create:

```text
$ADDON/units/HG_Hunter.cfg
```

Use this content:

```wml
#textdomain wesnoth-Hunter_Gath

[unit_type]
    id=HG Hunter
    name= _ "Hunter"
    race=human
    image="units/human-outlaws/trapper.png"
    profile="portraits/hunter-gath.png"
    hitpoints=34
    movement_type=woodland
    movement=6
    experience=44
    level=1
    alignment=neutral
    advances_to=Ranger
    cost=17
    usage=archer
    description= _ "A Hunter knows how to read old tracks, find water in bad ground, and vanish before a patrol realizes it has been followed. This sample unit exists to show where custom campaign units go and how they are loaded."
    die_sound={SOUND_LIST:HUMAN_DIE}
    {DEFENSE_ANIM "units/human-outlaws/trapper-defend.png" "units/human-outlaws/trapper.png" {SOUND_LIST:HUMAN_HIT} }

    [attack]
        name=knife
        description= _ "knife"
        icon="attacks/dagger-human.png"
        type=blade
        range=melee
        damage=4
        number=2
    [/attack]
    [attack]
        name=bow
        description= _ "bow"
        icon="attacks/bow.png"
        type=pierce
        range=ranged
        damage=6
        number=3
    [/attack]
[/unit_type]
```

Notes:

- `id=HG Hunter` is the code ID used by scenarios.
- `name= _ "Hunter"` is the translated display name.
- `image=` uses a core Wesnoth unit image, so you do not need to draw unit sprites yet.
- `profile=` points to a campaign-local portrait placeholder.
- `attacks` define the unit's melee and ranged options.

## Step 5: Create the first map

Create:

```text
$ADDON/maps/01_Goblin_Trail.map
```

Use this content:

```text
border_size=1
usage=map

Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg
Gg, Ff, Ff, Gg, Gg, Gg, Hh, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg
Gg, Ff, 1 Kh, Ch, Ch, Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg
Gg, Gg, Ch, Ch, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ff, Gg, Hh, Hh, Gg, Gg, Gg
Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg
Gg, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Ff, Gg, Gg, Gg
Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Hh
Gg, Gg, Gg, Gg, Gg, Gg, Hh, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ch, Ch, Gg
Gg, Gg, Hh, Hh, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg, Ch, 2 Kh, Ch
Gg, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ch, Gg
Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg
Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg
```

In real campaign work, create maps with the built-in map editor, then cleanly name them in `maps/`. Map start positions such as `1 Kh` and `2 Kh` correspond to side numbers.

## Step 6: Create the first scenario

Create:

```text
$ADDON/scenarios/01_Goblin_Trail.cfg
```

Use this content:

```wml
#textdomain wesnoth-Hunter_Gath

[scenario]
    id=01_Goblin_Trail
    name= _ "Goblin Trail"
    map_file=01_Goblin_Trail.map
    next_scenario=02_River_Poachers
    turns=18
    victory_when_enemies_defeated=yes

    {DEFAULT_SCHEDULE}
    {SCENARIO_MUSIC "wanderer.ogg"}
    {EXTRA_SCENARIO_MUSIC "knolls.ogg"}

    [story]
        [part]
            story= _ "When smoke rose from the northern timberline, the village elders sent for Gath, a hunter who knew the old paths better than any mapmaker."
            background="story/hunter-gath-forest.png"
        [/part]
        [part]
            story= _ "The tracks were not human. Small feet, many of them, cut across the wet earth toward the river road."
            background="story/hunter-gath-forest.png"
        [/part]
    [/story]

    [side]
        side=1
        controller=human
        team_name=hunters
        user_team_name= _ "Hunters"
        id=Gath
        name= _ "Gath"
        type=HG Hunter
        canrecruit=yes
        recruit=Bowman,Spearman,Woodsman
        {HG_GOLD 95 85 75}
        {HG_INCOME 1 0 0}
    [/side]

    [side]
        side=2
        controller=ai
        team_name=goblins
        user_team_name= _ "Goblins"
        id=Ruk
        name= _ "Ruk"
        type=Goblin Rouser
        canrecruit=yes
        recruit=Goblin Spearman,Goblin Impaler,Wolf Rider
        {HG_GOLD 45 60 75}
        {HG_INCOME 0 1 2}
    [/side]

    [event]
        name=prestart

        [objectives]
            side=1
            [objective]
                description= _ "Defeat Ruk, the goblin rouser"
                condition=win
            [/objective]
            [objective]
                description= _ "Death of Gath"
                condition=lose
            [/objective]
            [objective]
                description= _ "Turns run out"
                condition=lose
            [/objective]
            note= _ "This first scenario demonstrates sides, recruits, objectives, story screens, music, and victory by defeating the enemy leader."
        [/objectives]
    [/event]

    [event]
        name=start

        [message]
            speaker=Gath
            message= _ "The raiders are close. Take the ridge, keep the trees at your back, and leave their chief to me."
        [/message]
        [message]
            speaker=Ruk
            message= _ "Big hunter talks! Little blades answer!"
        [/message]
    [/event]

    [event]
        name=moveto
        first_time_only=yes
        [filter]
            side=1
            x=12-15
            y=2-5
        [/filter]

        [message]
            speaker=unit
            message= _ "Fresh tracks turn east. They were not alone."
        [/message]
    [/event]

    [event]
        name=last breath
        [filter]
            id=Gath
        [/filter]

        [message]
            speaker=Gath
            message= _ "The trail... goes dark."
        [/message]
        [endlevel]
            result=defeat
        [/endlevel]
    [/event]

    [event]
        name=victory

        [message]
            speaker=Gath
            message= _ "Their camp is broken, but these tracks keep running toward the river. We move before dawn."
        [/message]
    [/event]
[/scenario]
```

What this scenario teaches:

- A scenario connects to a map with `map_file=`.
- `next_scenario=` creates campaign flow.
- `[side]` blocks define leaders, teams, gold, income, and recruit lists.
- `[objectives]` defines visible win/loss conditions.
- `[story]` creates pre-scenario story screens.
- `[event] name=start` runs opening dialogue.
- `[event] name=moveto` reacts to unit movement.
- `[event] name=last breath` handles the hero's death.

## Step 7: Create the second map

Create:

```text
$ADDON/maps/02_River_Poachers.map
```

Use this content:

```text
border_size=1
usage=map

Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg, Gg, Gg
Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg, Ww, Ww, Gg, Gg, Gg, Ff, Ff, Gg, Hh, Gg, Gg, Gg
Gg, Ff, 1 Kh, Ch, Ch, Gg, Hh, Gg, Ww, Ww, Gg, Hh, Gg, Gg, Ff, Gg, Gg, Gg, Hh, Gg
Gg, Gg, Ch, Ch, Gg, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Hh, Gg, Ff, Ff, Gg, Hh, Hh, Gg
Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Ww, Ww, Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg
Gg, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Ww, Ww, Gg, Ff, Ff, Gg, Gg, Gg, Ff, Ff, Gg, Gg
Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Ww, Ww, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ch, Ch, Gg
Gg, Gg, Hh, Gg, Gg, Gg, Hh, Gg, Ww, Ww, Gg, Gg, Gg, Hh, Gg, Gg, Ch, 2 Kh, Ch, Gg
Gg, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ww, Ww, Gg, Hh, Hh, Gg, Gg, Gg, Gg, Ch, Gg, Gg
Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg, Gg
Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg, Ww, Ww, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg
Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg
```

## Step 8: Create the second scenario

Create:

```text
$ADDON/scenarios/02_River_Poachers.cfg
```

Use this content:

```wml
#textdomain wesnoth-Hunter_Gath

[scenario]
    id=02_River_Poachers
    name= _ "River Poachers"
    map_file=02_River_Poachers.map
    next_scenario=null
    turns=22
    victory_when_enemies_defeated=yes

    {DEFAULT_SCHEDULE}
    {SCENARIO_MUSIC "traveling_minstrels.ogg"}
    {EXTRA_SCENARIO_MUSIC "the_city_falls.ogg"}

    [story]
        [part]
            story= _ "At the river crossing, Gath found the goblins' allies: poachers cutting the king's preserve and selling safe passage to anyone with coin."
            background="story/hunter-gath-forest.png"
        [/part]
    [/story]

    [side]
        side=1
        controller=human
        team_name=hunters
        user_team_name= _ "Hunters"
        id=Gath
        name= _ "Gath"
        type=HG Hunter
        canrecruit=yes
        recruit=Bowman,Spearman,Woodsman,Thief
        {HG_GOLD 110 95 80}
        {HG_INCOME 2 1 0}
    [/side]

    [side]
        side=2
        controller=ai
        team_name=poachers
        user_team_name= _ "Poachers"
        id=Tharn
        name= _ "Tharn"
        type=Bandit
        canrecruit=yes
        recruit=Thug,Poacher,Thief,Footpad
        {HG_GOLD 70 90 110}
        {HG_INCOME 2 3 4}
    [/side]

    [event]
        name=prestart

        [objectives]
            side=1
            [objective]
                description= _ "Defeat Tharn, the poacher captain"
                condition=win
            [/objective]
            [objective]
                description= _ "Death of Gath"
                condition=lose
            [/objective]
            [objective]
                description= _ "Turns run out"
                condition=lose
            [/objective]
            note= _ "This finale adds a second map, carryover from the campaign flow, a turn event, and a small ambush."
        [/objectives]
    [/event]

    [event]
        name=start

        [message]
            speaker=Tharn
            message= _ "You should have stayed in your trees, hunter. The river belongs to my knives now."
        [/message]
        [message]
            speaker=Gath
            message= _ "A river belongs to itself. The rest is just men making noise."
        [/message]
    [/event]

    [event]
        name=turn 4

        [unit]
            side=2
            type=Poacher
            x=17
            y=6
        [/unit]
        [unit]
            side=2
            type=Footpad
            x=18
            y=7
        [/unit]
        [message]
            speaker=narrator
            image="wesnoth-icon.png"
            message= _ "More poachers slip from the reeds. Events can create units, change terrain, set variables, and alter objectives while a scenario is running."
        [/message]
    [/event]

    [event]
        name=last breath
        [filter]
            id=Gath
        [/filter]

        [message]
            speaker=Gath
            message= _ "The river takes us all, in the end."
        [/message]
        [endlevel]
            result=defeat
        [/endlevel]
    [/event]

    [event]
        name=victory

        [message]
            speaker=Gath
            message= _ "The road is clear. Tomorrow the village will have a safer river and a better story."
        [/message]
        [endlevel]
            result=victory
            linger_mode=yes
            carryover_report=no
            save=no
        [/endlevel]
    [/event]
[/scenario]
```

What this scenario adds:

- A campaign finale using `next_scenario=null`.
- A timed event on turn 4.
- Units created by an event.
- A final `[endlevel]` with no next scenario.

## Step 9: Add placeholder images

The package accompanying this guide includes placeholder PNG files. To regenerate them, create:

```text
$ADDON/tools/make_placeholder_assets.py
```

Use this content:

```python
#!/usr/bin/env python3
"""Regenerate the simple placeholder PNGs used by the Hunter Gath tutorial."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]

def make(path, size, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, (49, 73, 50))
    draw = ImageDraw.Draw(img)
    w, h = size
    draw.rectangle([10, 10, w - 11, h - 11], outline=(230, 220, 170), width=max(2, w // 80))
    draw.line([15, h - 20, w - 15, 20], fill=(180, 140, 80), width=max(2, w // 90))
    draw.text((20, h // 2 - 10), label, fill=(245, 235, 200))
    img.save(path)

make(ROOT / "images/misc/hunter-gath-icon.png", (72, 72), "HG")
make(ROOT / "images/portraits/hunter-gath.png", (350, 350), "Hunter Gath")
make(ROOT / "images/story/hunter-gath-forest.png", (1024, 768), "Northern Timberline")
```

Run:

```bash
python3 "$ADDON/tools/make_placeholder_assets.py"
```

These placeholder images are scaffolding only. Before publishing or proposing mainline inclusion, replace them with art that has clear license provenance and matches Wesnoth's art direction.

## Step 10: Add add-on metadata

Create:

```text
$ADDON/_server.pbl
```

Use this content:

```text
title="Hunter Gath"
type="campaign"
icon="misc/hunter-gath-icon.png"
version="0.1.0"
author="Your Name"
email="you@example.com"
passphrase="replace-this-before-uploading"
description="A compact two-scenario campaign used as a development tutorial sample."
```

Before uploading, replace `author`, `email`, and `passphrase`. Do not commit a real private passphrase into a public repository.

## Step 11: Run the campaign

Launch Wesnoth from a terminal so WML errors are visible:

```bash
wesnoth
```

Open **Campaigns**, find **Hunter Gath**, choose a difficulty, and start the first scenario.

If the campaign does not appear:

- Confirm `_main.cfg` is directly inside `Hunter_Gath/`.
- Confirm the add-on folder is under `data/add-ons/` in the userdata path printed by `wesnoth --config-path`.
- Confirm the folder is named `Hunter_Gath`, not `Hunter Gath`.
- Check the terminal output for WML parse errors.

If the campaign appears but fails to start:

- Confirm `first_scenario=01_Goblin_Trail` matches the scenario `id` exactly.
- Confirm `map_file=01_Goblin_Trail.map` matches the map filename exactly.
- Confirm custom unit ID `HG Hunter` matches `type=HG Hunter` in the first `[side]`.
- Confirm every opening WML tag has a matching closing tag.

# Chapter 5: Testing, debugging, and maintenance

## Use the terminal as your first debugger

Wesnoth reports WML errors on startup and scenario load. When something breaks, do not guess from the UI. Start the game from a terminal, reproduce the failure, and read the first error. The first error is usually more useful than the later cascade.

## Format WML with `wmlindent`

From your Wesnoth repository checkout:

```bash
cd ~/src/wesnoth
python3 data/tools/wmlindent ~/.local/share/wesnoth/<version>/data/add-ons/Hunter_Gath
```

Or, after moving the campaign into the repository:

```bash
python3 data/tools/wmlindent data/campaigns/Hunter_Gath
```

Review the diff after formatting:

```bash
git diff -- data/campaigns/Hunter_Gath
```

## Run maintenance checks

`wmllint` and related tools can produce noisy output, especially while content is incomplete. Treat them as maintenance assistants, not as a substitute for loading and playing the campaign.

A typical later-stage check from the repository root is:

```bash
python3 data/tools/wmllint data/core data/campaigns/Hunter_Gath
```

Use existing mainline campaigns as examples when a warning is unclear.

## Test like a player and like a maintainer

Player testing:

- Can each scenario be won and lost?
- Are objectives accurate after events fire?
- Does the turn limit create pressure without being arbitrary?
- Are recruit lists and gold fair on all difficulties?
- Are dialogue and story screens clear without being too long?

Maintainer testing:

- Are IDs stable and consistently prefixed where needed?
- Are paths relative to the correct binary path?
- Are all strings intended for players marked with `_`?
- Are there unused images, maps, units, or macros?
- Is every asset license recorded?
- Does the campaign load from a clean checkout, not only from your own machine?

## Common campaign bugs

| Symptom | Likely cause |
|---|---|
| Campaign not listed | `_main.cfg` missing, wrong add-on directory, parse error before `[campaign]`. |
| Scenario not found | `first_scenario` or `next_scenario` does not match a scenario `id`. |
| Map not found | Wrong `map_file`, missing map, missing `[binary_path]`, or mainline/add-on path mismatch. |
| Unknown unit type | Custom unit not inside `[units]`, typo in `type=`, or dependency on a unit not available in core. |
| Image not found | Wrong image path, missing `[binary_path]`, file name case mismatch. |
| Difficulty values wrong | Macro not included before scenarios or difficulty symbol mismatch. |
| Translation extraction misses strings | Missing `_` marker or wrong textdomain. |

# Chapter 6: Moving from an add-on to a forked Wesnoth branch

Once Hunter Gath works locally, commit it to your fork of the Wesnoth repository.

## Step 1: Sync your fork

```bash
cd ~/src/wesnoth
git fetch upstream
git checkout master
git merge upstream/master
git push origin master
```

## Step 2: Create a feature branch

```bash
git checkout -b hunter-gath-campaign
```

## Step 3: Copy the campaign into `data/campaigns`

```bash
mkdir -p data/campaigns/Hunter_Gath
rsync -a --delete \
  ~/.local/share/wesnoth/<version>/data/add-ons/Hunter_Gath/ \
  data/campaigns/Hunter_Gath/
```

Do not copy private upload credentials. If `_server.pbl` contains a real passphrase, remove or sanitize it before committing.

## Step 4: Convert add-on include paths to mainline paths

For a local add-on, Hunter Gath uses:

```wml
[binary_path]
    path=data/add-ons/Hunter_Gath
[/binary_path]

{~add-ons/Hunter_Gath/utils}
[units]
    {~add-ons/Hunter_Gath/units}
[/units]
{~add-ons/Hunter_Gath/scenarios}
```

For a campaign inside the source tree, use:

```wml
[binary_path]
    path=data/campaigns/Hunter_Gath
[/binary_path]

{campaigns/Hunter_Gath/utils}
[units]
    {campaigns/Hunter_Gath/units}
[/units]
{campaigns/Hunter_Gath/scenarios}
```

Also update the textdomain path:

```wml
[textdomain]
    name="wesnoth-Hunter_Gath"
    path="data/campaigns/Hunter_Gath/translations"
[/textdomain]
```

Mainline campaigns are included through the game's campaign data loading. Study nearby campaigns in `data/campaigns/` and match current conventions before opening a pull request.

## Step 5: Format and inspect

```bash
python3 data/tools/wmlindent data/campaigns/Hunter_Gath
git status
git diff --check
git diff -- data/campaigns/Hunter_Gath
```

## Step 6: Build and run from the branch

```bash
cmake --build build
./build/wesnoth
```

Load Hunter Gath from the campaign menu and play both scenarios. Fix every terminal error before committing.

## Step 7: Commit

```bash
git add data/campaigns/Hunter_Gath
git commit -m "Add Hunter Gath sample campaign"
```

Good campaign commits are readable. If you are adding a large campaign, split work into meaningful commits:

1. Campaign scaffold and metadata.
2. Maps and scenario WML.
3. Units and macros.
4. Art/music/sound assets with license notes.
5. Balancing and text revisions.

## Step 8: Push and open a pull request

```bash
git push -u origin hunter-gath-campaign
```

Open a pull request from your fork to the official repository. In the PR description, include:

- What the campaign adds.
- How many scenarios are playable.
- How it was tested.
- Known missing assets or balance concerns.
- Licensing notes for all new assets.
- Any design discussion links from forums, Discord, or issue threads.

## Step 9: Expect review

Wesnoth is a volunteer project. Make the review easy:

- Keep formatting clean.
- Explain unusual WML.
- Do not mix unrelated engine changes into a campaign PR.
- Respond politely and specifically to review comments.
- If generated or assisted code is involved, be ready to explain what it does and why.

# Appendix A: Complete Hunter Gath file listing

The accompanying code includes this file tree:

```text
ART_LICENSE
COPYING.txt
README.md
_main.cfg
_server.pbl
images/misc/hunter-gath-icon.png
images/portraits/hunter-gath.png
images/story/hunter-gath-forest.png
maps/01_Goblin_Trail.map
maps/02_River_Poachers.map
music/.keep
scenarios/01_Goblin_Trail.cfg
scenarios/02_River_Poachers.cfg
sounds/.keep
tools/make_placeholder_assets.py
translations/.keep
units/HG_Hunter.cfg
utils/hg-utils.cfg
```

## `_main.cfg`

```wml
#textdomain wesnoth-Hunter_Gath

[textdomain]
    name="wesnoth-Hunter_Gath"
    path="data/add-ons/Hunter_Gath/translations"
[/textdomain]

[campaign]
    id=Hunter_Gath
    rank=999
    type=sp
    name= _ "Hunter Gath"
    abbrev= _ "HG"
    define=CAMPAIGN_HUNTER_GATH
    icon="misc/hunter-gath-icon.png"
    image="portraits/hunter-gath.png"
    background="story/hunter-gath-forest.png"
    first_scenario=01_Goblin_Trail
    description= _ "A compact sample campaign for learning how Wesnoth campaigns are assembled: add-on metadata, WML, maps, custom units, events, objectives, images, and Git workflow."

    [difficulty]
        define=EASY
        image="units/human-loyalists/bowman.png~RC(magenta>green)"
        label= _ "Tracker"
        description= _ "Easy"
    [/difficulty]
    [difficulty]
        define=NORMAL
        image="units/human-outlaws/trapper.png~RC(magenta>green)"
        label= _ "Hunter"
        description= _ "Normal"
        default=yes
    [/difficulty]
    [difficulty]
        define=HARD
        image="units/orcs/goblin-spearman.png~RC(magenta>green)"
        label= _ "Stalker"
        description= _ "Hard"
    [/difficulty]

    [about]
        title= _ "Campaign design and WML"
        [entry]
            name="Your Name"
            comment= _ "Replace this credit before publishing or proposing the campaign."
        [/entry]
    [/about]
[/campaign]

#ifdef CAMPAIGN_HUNTER_GATH
[binary_path]
    path=data/add-ons/Hunter_Gath
[/binary_path]

{~add-ons/Hunter_Gath/utils}

[units]
    {~add-ons/Hunter_Gath/units}
[/units]

{~add-ons/Hunter_Gath/scenarios}
#endif
```

## `utils/hg-utils.cfg`

```wml
#textdomain wesnoth-Hunter_Gath

# Small campaign-local helpers.
# Keep utility macros in this file so scenarios stay readable.

#define HG_GOLD EASY_AMOUNT NORMAL_AMOUNT HARD_AMOUNT
#ifdef EASY
    gold={EASY_AMOUNT}
#endif
#ifdef NORMAL
    gold={NORMAL_AMOUNT}
#endif
#ifdef HARD
    gold={HARD_AMOUNT}
#endif
#enddef

#define HG_INCOME EASY_AMOUNT NORMAL_AMOUNT HARD_AMOUNT
#ifdef EASY
    income={EASY_AMOUNT}
#endif
#ifdef NORMAL
    income={NORMAL_AMOUNT}
#endif
#ifdef HARD
    income={HARD_AMOUNT}
#endif
#enddef
```

## `units/HG_Hunter.cfg`

```wml
#textdomain wesnoth-Hunter_Gath

[unit_type]
    id=HG Hunter
    name= _ "Hunter"
    race=human
    image="units/human-outlaws/trapper.png"
    profile="portraits/hunter-gath.png"
    hitpoints=34
    movement_type=woodland
    movement=6
    experience=44
    level=1
    alignment=neutral
    advances_to=Ranger
    cost=17
    usage=archer
    description= _ "A Hunter knows how to read old tracks, find water in bad ground, and vanish before a patrol realizes it has been followed. This sample unit exists to show where custom campaign units go and how they are loaded."
    die_sound={SOUND_LIST:HUMAN_DIE}
    {DEFENSE_ANIM "units/human-outlaws/trapper-defend.png" "units/human-outlaws/trapper.png" {SOUND_LIST:HUMAN_HIT} }

    [attack]
        name=knife
        description= _ "knife"
        icon="attacks/dagger-human.png"
        type=blade
        range=melee
        damage=4
        number=2
    [/attack]
    [attack]
        name=bow
        description= _ "bow"
        icon="attacks/bow.png"
        type=pierce
        range=ranged
        damage=6
        number=3
    [/attack]
[/unit_type]
```

## `scenarios/01_Goblin_Trail.cfg`

```wml
#textdomain wesnoth-Hunter_Gath

[scenario]
    id=01_Goblin_Trail
    name= _ "Goblin Trail"
    map_file=01_Goblin_Trail.map
    next_scenario=02_River_Poachers
    turns=18
    victory_when_enemies_defeated=yes

    {DEFAULT_SCHEDULE}
    {SCENARIO_MUSIC "wanderer.ogg"}
    {EXTRA_SCENARIO_MUSIC "knolls.ogg"}

    [story]
        [part]
            story= _ "When smoke rose from the northern timberline, the village elders sent for Gath, a hunter who knew the old paths better than any mapmaker."
            background="story/hunter-gath-forest.png"
        [/part]
        [part]
            story= _ "The tracks were not human. Small feet, many of them, cut across the wet earth toward the river road."
            background="story/hunter-gath-forest.png"
        [/part]
    [/story]

    [side]
        side=1
        controller=human
        team_name=hunters
        user_team_name= _ "Hunters"
        id=Gath
        name= _ "Gath"
        type=HG Hunter
        canrecruit=yes
        recruit=Bowman,Spearman,Woodsman
        {HG_GOLD 95 85 75}
        {HG_INCOME 1 0 0}
    [/side]

    [side]
        side=2
        controller=ai
        team_name=goblins
        user_team_name= _ "Goblins"
        id=Ruk
        name= _ "Ruk"
        type=Goblin Rouser
        canrecruit=yes
        recruit=Goblin Spearman,Goblin Impaler,Wolf Rider
        {HG_GOLD 45 60 75}
        {HG_INCOME 0 1 2}
    [/side]

    [event]
        name=prestart

        [objectives]
            side=1
            [objective]
                description= _ "Defeat Ruk, the goblin rouser"
                condition=win
            [/objective]
            [objective]
                description= _ "Death of Gath"
                condition=lose
            [/objective]
            [objective]
                description= _ "Turns run out"
                condition=lose
            [/objective]
            note= _ "This first scenario demonstrates sides, recruits, objectives, story screens, music, and victory by defeating the enemy leader."
        [/objectives]
    [/event]

    [event]
        name=start

        [message]
            speaker=Gath
            message= _ "The raiders are close. Take the ridge, keep the trees at your back, and leave their chief to me."
        [/message]
        [message]
            speaker=Ruk
            message= _ "Big hunter talks! Little blades answer!"
        [/message]
    [/event]

    [event]
        name=moveto
        first_time_only=yes
        [filter]
            side=1
            x=12-15
            y=2-5
        [/filter]

        [message]
            speaker=unit
            message= _ "Fresh tracks turn east. They were not alone."
        [/message]
    [/event]

    [event]
        name=last breath
        [filter]
            id=Gath
        [/filter]

        [message]
            speaker=Gath
            message= _ "The trail... goes dark."
        [/message]
        [endlevel]
            result=defeat
        [/endlevel]
    [/event]

    [event]
        name=victory

        [message]
            speaker=Gath
            message= _ "Their camp is broken, but these tracks keep running toward the river. We move before dawn."
        [/message]
    [/event]
[/scenario]
```

## `scenarios/02_River_Poachers.cfg`

```wml
#textdomain wesnoth-Hunter_Gath

[scenario]
    id=02_River_Poachers
    name= _ "River Poachers"
    map_file=02_River_Poachers.map
    next_scenario=null
    turns=22
    victory_when_enemies_defeated=yes

    {DEFAULT_SCHEDULE}
    {SCENARIO_MUSIC "traveling_minstrels.ogg"}
    {EXTRA_SCENARIO_MUSIC "the_city_falls.ogg"}

    [story]
        [part]
            story= _ "At the river crossing, Gath found the goblins' allies: poachers cutting the king's preserve and selling safe passage to anyone with coin."
            background="story/hunter-gath-forest.png"
        [/part]
    [/story]

    [side]
        side=1
        controller=human
        team_name=hunters
        user_team_name= _ "Hunters"
        id=Gath
        name= _ "Gath"
        type=HG Hunter
        canrecruit=yes
        recruit=Bowman,Spearman,Woodsman,Thief
        {HG_GOLD 110 95 80}
        {HG_INCOME 2 1 0}
    [/side]

    [side]
        side=2
        controller=ai
        team_name=poachers
        user_team_name= _ "Poachers"
        id=Tharn
        name= _ "Tharn"
        type=Bandit
        canrecruit=yes
        recruit=Thug,Poacher,Thief,Footpad
        {HG_GOLD 70 90 110}
        {HG_INCOME 2 3 4}
    [/side]

    [event]
        name=prestart

        [objectives]
            side=1
            [objective]
                description= _ "Defeat Tharn, the poacher captain"
                condition=win
            [/objective]
            [objective]
                description= _ "Death of Gath"
                condition=lose
            [/objective]
            [objective]
                description= _ "Turns run out"
                condition=lose
            [/objective]
            note= _ "This finale adds a second map, carryover from the campaign flow, a turn event, and a small ambush."
        [/objectives]
    [/event]

    [event]
        name=start

        [message]
            speaker=Tharn
            message= _ "You should have stayed in your trees, hunter. The river belongs to my knives now."
        [/message]
        [message]
            speaker=Gath
            message= _ "A river belongs to itself. The rest is just men making noise."
        [/message]
    [/event]

    [event]
        name=turn 4

        [unit]
            side=2
            type=Poacher
            x=17
            y=6
        [/unit]
        [unit]
            side=2
            type=Footpad
            x=18
            y=7
        [/unit]
        [message]
            speaker=narrator
            image="wesnoth-icon.png"
            message= _ "More poachers slip from the reeds. Events can create units, change terrain, set variables, and alter objectives while a scenario is running."
        [/message]
    [/event]

    [event]
        name=last breath
        [filter]
            id=Gath
        [/filter]

        [message]
            speaker=Gath
            message= _ "The river takes us all, in the end."
        [/message]
        [endlevel]
            result=defeat
        [/endlevel]
    [/event]

    [event]
        name=victory

        [message]
            speaker=Gath
            message= _ "The road is clear. Tomorrow the village will have a safer river and a better story."
        [/message]
        [endlevel]
            result=victory
            linger_mode=yes
            carryover_report=no
            save=no
        [/endlevel]
    [/event]
[/scenario]
```

## `maps/01_Goblin_Trail.map`

```text
border_size=1
usage=map

Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg
Gg, Ff, Ff, Gg, Gg, Gg, Hh, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg
Gg, Ff, 1 Kh, Ch, Ch, Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg
Gg, Gg, Ch, Ch, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ff, Gg, Hh, Hh, Gg, Gg, Gg
Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg
Gg, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Ff, Gg, Gg, Gg
Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Hh
Gg, Gg, Gg, Gg, Gg, Gg, Hh, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ch, Ch, Gg
Gg, Gg, Hh, Hh, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg, Ch, 2 Kh, Ch
Gg, Gg, Gg, Hh, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ch, Gg
Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg
Gg, Gg, Ff, Ff, Gg, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg
```

## `maps/02_River_Poachers.map`

```text
border_size=1
usage=map

Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg, Gg, Gg
Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg, Ww, Ww, Gg, Gg, Gg, Ff, Ff, Gg, Hh, Gg, Gg, Gg
Gg, Ff, 1 Kh, Ch, Ch, Gg, Hh, Gg, Ww, Ww, Gg, Hh, Gg, Gg, Ff, Gg, Gg, Gg, Hh, Gg
Gg, Gg, Ch, Ch, Gg, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Hh, Gg, Ff, Ff, Gg, Hh, Hh, Gg
Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Ww, Ww, Gg, Gg, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg
Gg, Hh, Gg, Gg, Ff, Ff, Gg, Gg, Ww, Ww, Gg, Ff, Ff, Gg, Gg, Gg, Ff, Ff, Gg, Gg
Gg, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Ww, Ww, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Ch, Ch, Gg
Gg, Gg, Hh, Gg, Gg, Gg, Hh, Gg, Ww, Ww, Gg, Gg, Gg, Hh, Gg, Gg, Ch, 2 Kh, Ch, Gg
Gg, Gg, Gg, Hh, Hh, Gg, Gg, Gg, Ww, Ww, Gg, Hh, Hh, Gg, Gg, Gg, Gg, Ch, Gg, Gg
Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Gg, Ff, Ff, Gg, Gg, Gg, Gg, Gg
Gg, Ff, Ff, Gg, Gg, Gg, Hh, Gg, Ww, Ww, Gg, Gg, Ff, Ff, Gg, Gg, Hh, Hh, Gg, Gg
Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Ww, Ww, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg, Gg
```

## `_server.pbl`

```text
title="Hunter Gath"
type="campaign"
icon="misc/hunter-gath-icon.png"
version="0.1.0"
author="Your Name"
email="you@example.com"
passphrase="replace-this-before-uploading"
description="A compact two-scenario campaign used as a development tutorial sample."
```

# Appendix B: Preflight checklist

Before local testing:

- [ ] `_main.cfg` exists directly inside `Hunter_Gath/`.
- [ ] The directory is under `data/add-ons/` in the userdata path printed by `wesnoth --config-path`.
- [ ] The folder and include paths use `Hunter_Gath`, not `Hunter Gath`.
- [ ] `[campaign] first_scenario=` matches the first scenario `id`.
- [ ] Every scenario's `map_file=` exists in `maps/`.
- [ ] Custom units are included inside `[units]`.
- [ ] Images referenced by campaign metadata exist under `images/` or in core.

Before committing:

- [ ] WML is formatted with `wmlindent`.
- [ ] `git diff --check` is clean.
- [ ] The campaign works from a clean checkout or clean userdata directory.
- [ ] No private `_server.pbl` passphrase is committed.
- [ ] Placeholder art is replaced or clearly marked as placeholder.
- [ ] Asset licenses are documented.
- [ ] All user-facing strings are marked for translation.
- [ ] US English spelling and punctuation are consistent.
- [ ] The PR description explains testing and known limitations.

## References

Official Wesnoth references used while compiling this guide:

- Project / developers entry point: https://wiki.wesnoth.org/Project#Developers
- Wesnoth repository: https://github.com/wesnoth/wesnoth
- Source build instructions: https://github.com/wesnoth/wesnoth/blob/master/INSTALL.md
- Contribution guidelines: https://github.com/wesnoth/wesnoth/blob/master/CONTRIBUTING.md
- Official manual sources: https://github.com/wesnoth/wesnoth/tree/master/doc/manual
- Add-on structure: https://wiki.wesnoth.org/AddonStructure
- Editing Wesnoth / paths: https://wiki.wesnoth.org/EditingWesnoth
- WML reference index: https://wiki.wesnoth.org/ReferenceWML
- Campaign WML: https://wiki.wesnoth.org/CampaignWML
- Scenario WML: https://wiki.wesnoth.org/ScenarioWML
- Side WML: https://wiki.wesnoth.org/SideWML
- Event WML: https://wiki.wesnoth.org/EventWML
- Unit type WML: https://wiki.wesnoth.org/UnitTypeWML
- Preprocessor reference: https://wiki.wesnoth.org/PreprocessorRef
- Maps / map editor: https://wiki.wesnoth.org/BuildingMaps
- Distributing content: https://wiki.wesnoth.org/Distributing_content
- PBL / add-on server metadata: https://wiki.wesnoth.org/PBLWML
- Maintenance tools: https://wiki.wesnoth.org/Maintenance_tools
- Gettext for Wesnoth developers: https://wiki.wesnoth.org/GettextForWesnothDevelopers
- Typography style guide: https://wiki.wesnoth.org/Typography_Style_Guide
