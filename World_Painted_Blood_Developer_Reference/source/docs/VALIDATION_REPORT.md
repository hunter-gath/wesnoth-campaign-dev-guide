# Validation Report

**Build:** 0.1.0  
**Target:** Battle for Wesnoth 1.18  
**Static validation date:** 2026-07-20 UTC

## Passed Checks

- Exact required sets of 20 scenario files, 20 map files, and 20 custom music filenames are present.
- Scenario IDs, `next_scenario` chain, `map_file` values, and scenario music references match their fixed filenames.
- Lightweight WML tag nesting checks pass for `_main.cfg`, utilities, units, and every scenario.
- All scenarios disable default enemy-leader victory and use explicit objective-state completion.
- Every scenario includes an explicit rescue-versus-bait decision; bait damage cannot accidentally kill a boss before moral bookkeeping completes.
- All scripted numeric coordinates are inside their maps and reachable from Side 1.
- Every map uses terrain codes from the campaign's verified Wesnoth 1.18 terrain whitelist.
- All referenced scenario sound basenames occur in the verified core sound manifest.
- All 20 silent placeholder tracks decode as Ogg Vorbis through `ffprobe`.
- ZIP archive integrity was checked after packaging.

## Not Performed in This Environment

A Wesnoth executable, `wmllint`, and `wmlscope` were not available. Consequently, this package has not yet been launched through the actual Wesnoth 1.18 preprocessor, scenario loader, AI, save/recall system, or campaign UI. The first local engine run may expose WML-version details or balancing issues that static checks cannot detect.

## Recommended First Engine Test

1. Install the top-level `World_Painted_Blood/` directory in the Wesnoth user-data `data/add-ons/` directory.
2. Reload add-ons and confirm the campaign appears in the campaign menu.
3. Start Scenario 1 on the middle difficulty.
4. Test both the rescue and bait branches, both orders of completing sites versus killing leaders, turn-limit defeat, Hunter death, and transition to Scenario 2.
5. Use debug `:cl` or temporarily edit `first_scenario` to smoke-test each remaining scenario.
6. Record any engine error with the scenario filename, turn, action, and `stderr.txt` or Wesnoth log excerpt.
