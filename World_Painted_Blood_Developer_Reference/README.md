# World Painted Blood Developer Reference

Offline developer-reference site for **World Painted Blood 0.1.0**.

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
