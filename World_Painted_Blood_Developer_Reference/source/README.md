# World Painted Blood

A twenty-scenario independent horror campaign for **The Battle for Wesnoth 1.18**.

> Development status: structurally complete first test build for iterative playtesting. Static validation has been performed, but this package still requires its first full run inside Wesnoth 1.18. Maps, gold, enemy composition, dialogue timing, and advanced mechanics are expected to change after playtesting.

## Campaign Overview

Across southern Wesnoth, burial grounds have emptied, villages have fallen silent, and red water has begun seeping into the rivers surrounding the Swamp of Esten. A solitary Hunter enters the swamp searching for the source of the undead armies, only for the ground to collapse beneath him. Far below the surface he discovers an immense hidden world of ruined cities, blood reservoirs, ancient battlefields, necromantic factories, and secret kingdoms ruled by the dead.

Cut off from the surface, the Hunter must descend through twenty ordeals and destroy the alliance of undead warlords and evil magicians preparing to conquer Wesnoth. Along the way he may rescue the living—or use them as shields and bait. Both paths can reach victory, but every deliberate sacrifice darkens the story and changes who answers the Hunter when the final command awakens every corpse beneath Esten.

## What This Package Contains

- Twenty linked single-player scenarios using the exact required `.cfg` filenames.
- Twenty distinct underground maps using the exact required `.map` filenames.
- Twenty valid silent OGG placeholder tracks using `01_Scenario.ogg` through `20_Scenario.ogg`; replace these files in place when the recorded music is ready.
- A custom `WPB Hunter` protagonist inheriting the core Ranger’s complete art, animation, and sound definitions.
- Persistent rescue, conscription, sacrifice, corruption, truth, and alliance variables.
- Explicit moral decisions in every scenario. Rescued captives become loyal human units; using them as bait grants an immediate tactical benefit and darkens later content.
- Mainline/core sound references only. See `docs/SOUND_ASSET_MANIFEST.md`.
- A local structural validator in `tools/validate_wpb.py`.

## Installation HOWTO

1. Install or run **Battle for Wesnoth 1.18**.
2. Find the Wesnoth user-data directory. From the title screen, the folder button in the Add-ons interface can usually open the add-ons location. On a typical Linux installation it is beneath the Wesnoth user-data tree in `data/add-ons/`.
3. Copy the complete `World_Painted_Blood/` directory into:

   ```text
   <Wesnoth user data>/data/add-ons/World_Painted_Blood/
   ```

4. Confirm that `_main.cfg` is directly inside that directory—not inside an extra nested folder.
5. Start Wesnoth or press **F5** at the title screen to reload add-ons.
6. Open **Campaigns**, select **World Painted Blood**, and choose a difficulty.
7. During development, enable debug mode and use `:cl` to jump between scenarios, or temporarily change `first_scenario` in `_main.cfg` to the scenario being tested.

## Music HOWTO

The files in `music/` are one-second silent OGG placeholders. They exist so every scenario can load while the real recordings are unfinished.

Replace each placeholder without changing its filename:

```text
music/01_Scenario.ogg
...
music/20_Scenario.ogg
```

Recommended delivery format: Ogg Vorbis, stereo, 44.1 kHz or 48 kHz. Normalize conservatively; Wesnoth music should leave headroom for sound effects.

## Sound HOWTO

This build references existing Wesnoth core sound files such as `cave-in.ogg`, `explosion.ogg`, `bat-flapping.wav`, and `groan.wav`. They are available to an installed 1.18 game, so the test build does not require bundled copies.

For a later fully self-contained asset bundle, copy the documented files from the installed Wesnoth core sound directory into `World_Painted_Blood/sounds/`. Keeping the same basenames means the campaign-local copies will override the core search path automatically.

## Basic Play HOWTO

- The Hunter is the only universally mandatory character. His death ends every scenario.
- Move onto every labeled objective hex. Secured locations lose their lit-brazier overlay and update the internal objective count.
- Defeat every required named enemy leader. Some later scenarios have two or three required leaders.
- Approach the named captive near the Hunter's starting position to make the scenario's moral choice:
  - **Free and arm them:** the captive joins Side 1 as a loyal unit; rescue and alliance values increase.
  - **Use them as bait:** the captive dies, the principal boss takes damage, Side 1 gains gold, and sacrifice/corruption increase.
- Ordinary battlefield deaths are not automatically counted as deliberate sacrifices. Only explicit choice events alter the moral variables.
- Gold carryover is 40 percent with an early-finish bonus.
- Scenario 20 does not end when the nexus objectives are completed. Return the Hunter to the western sinkhole after the escape phase begins.

## Persistent Campaign Variables

| Variable | Meaning |
|---|---|
| `wpb_rescued` | Named captives deliberately saved |
| `wpb_conscripted` | Saved captives turned into player-controlled units |
| `wpb_sacrificed` | Named captives deliberately spent as bait |
| `wpb_corruption` | Supernatural and moral corruption accumulated by the Hunter |
| `wpb_truth` | Evidence gathered against the cabal |
| `wpb_alliance_strength` | Strength of groups willing to help later |

## Technical Structure

```text
World_Painted_Blood/
├── _main.cfg
├── README.md
├── CHANGELOG.md
├── LICENSE
├── scenarios/              # exact required filenames
├── maps/                   # exact required filenames
├── music/                  # exact required filenames; silent placeholders
├── units/Hunter.cfg
├── utils/macros.cfg
├── docs/
├── tools/validate_wpb.py
└── translations/
```

The campaign uses a standard `[campaign]` definition, a campaign-specific preprocessor symbol, a `[binary_path]`, one custom unit, reusable WML macros, `map_file` references, event-driven objectives, persistent WML variables, and explicit `[endlevel]` transitions.

## Scenario Design and Implementation

### 01. When the Stillness Comes

**Summary.** The Hunter awakens at the bottom of the sinkhole in a corpse chamber where even dripping water seems afraid to make a sound. Bodies cover the floor, his equipment is scattered among them, and a silent executioner moves whenever the living are isolated. To escape, the Hunter must recover his weapons, free another survivor, and destroy Collector Oth, the necromancer who prepares surface victims for transport deeper underground. The records left behind reveal that the massacre is only the first station in an organized supply line.

**Characters.** The Hunter; Eda Varr, a stranded swamp guide; Collector Oth, keeper of the corpse chamber; the unseen Still One, represented by stalking Nightgaunts.

**Map.** A natural sinkhole opening into a circular slaughter chamber, corpse alcoves, mushroom-lit side tunnels, a central chasm, and a barred southeastern gate. Purple-green tint.

**Objectives.** Secure 2 equipment cache locations and defeat the scenario's required enemy leader.

**Implemented special events.** Recover two equipment caches. A turn-four Nightgaunt reinforcement represents the Still One entering the hunt. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 02. Cast the First Stone

**Summary.** The passage opens into a terraced burial ground where surface prisoners are condemned before open graves. Vardoc calls each execution an act of penance and waits for the first act of resistance to awaken the dead beneath every stone. The Hunter must seize the ritual stones, release at least one prisoner, and overthrow Vardoc before the execution cycle is completed. By striking first, he announces to the entire underground that a living enemy is coming for its masters.

**Characters.** The Hunter; Brother Celn, a captive temple attendant; Vardoc the Penitent; Ossur, the revenant grave warden.

**Map.** Descending grave terraces around a central execution platform, catacomb walls, ossuary villages, open pits, and a ruined keep. Red-orange tint.

**Objectives.** Secure 3 ritual stone locations and defeat the scenario's required enemy leader.

**Implemented special events.** Capturing ritual stones prevents scheduled corpse reinforcements. The player can arm Celn or spend him to weaken Vardoc. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 03. Here Comes the Pain

**Summary.** A fortress gate is protected by an arena where intruders are broken before an audience of silent dead. Its champion, Gorath, has piled the weapons of every challenger beneath his throne. The Hunter must seize the arena controls and survive successive waves before confronting Gorath and the necromancer Nethys. Winning opens the gate and turns the lost surface-dweller into a threat recognized by the underground command.

**Characters.** The Hunter; Torren Hale, an arena survivor; Gorath the Agony; Nethys, Master of Trials; the Bone Herald.

**Map.** A dark-flagstone arena ringed by ruined stands, holding cells, barred gates, and four control braziers. Orange-red tint.

**Objectives.** Secure 3 arena control locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Each control reduces the reinforcement wave. Gorath and Nethys must both fall. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 04. Show No Mercy

**Summary.** Past the arena lies a maze built for pursuit. Bells alter its gates, undead patrols enter from sealed passages, and Veil-Mistress Ysara hunts escaped captives for sport. The Hunter must silence the hunt bells and force open the southern route while patrols close behind him. Mercy is optional; escape is not.

**Characters.** The Hunter; Noma Reed, a smuggler familiar with hidden shafts; Veil-Mistress Ysara; the Near One, a stalking Nightgaunt.

**Map.** A long maze of cave paths, alternating wall gates, dead-end chasms, fungal side shafts, and a southern escape keep. Purple-green tint and shroud.

**Objectives.** Secure 3 hunt bell locations and defeat the scenario's required enemy leader.

**Implemented special events.** Bell controls are the objectives. A Nightgaunt arrives behind the player during the pursuit. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 05. At Dawn They Sleep

**Summary.** A false dawn shines through crystals above a crypt packed with sleeping bats and blood-drinking undead. The light does not destroy them; it merely holds them inside their dreams. Before the crystals dim, the Hunter must destroy the blood cisterns and kill Seryn and Vaska. Captives chained beside the controls can maintain the light—or be abandoned to occupy the brood.

**Characters.** The Hunter; Lethan Crow, a captured scholar; Seryn of the Hollow Vein; Vaska, Brood-Mother; the Coffin Keeper.

**Map.** A radial crypt with four coffin wings, a central blood well, crystal stations, catacomb walls, and cave villages. Purple-red tint.

**Objectives.** Secure 4 blood cistern locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Four cisterns control reinforcement frequency. The bat brood intensifies after turn six. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 06. Die by the Sword

**Summary.** The blood shipments lead to a mining settlement where living laborers work until death and continue their shifts after being raised. Sir Malrec claims the sword is the only law the helpless understand. The Hunter must capture the rail junctions, destroy the corpse-processing line, and take Malrec's ledger. The miners can be evacuated, armed, or ordered to hold lethal side tunnels.

**Characters.** The Hunter; Aldren Vale, a captive guard captain; Sir Malrec the Red Blade; Sytha of the Ledger; Harl Dane, mine foreman.

**Map.** Mine rails cross three work shafts, a smelting pocket, rockbound caverns, dwarven villages, bridges, and an administrative fortress. Orange-red tint.

**Objectives.** Secure 3 rail junction locations and defeat the scenario's required enemy leader.

**Implemented special events.** Junctions interrupt enemy supply waves. A Revenant work gang arrives on turn five. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 07. You Against You

**Summary.** Perfectly symmetrical halls turn suspicion into memory and reflections into enemies. Every companion sees proof that the others have betrayed them, while a false Hunter repeats the accusations the real one refuses to hear. The party must shatter the mirror anchors and identify Istrava's true body. Violence against the wrong reflections makes the battle harder, while trust opens the direct path.

**Characters.** The Hunter; Selka Morn, an outlaw survivor; Istrava of the Second Face; the Hunter’s Reflection; spectral mirror guards.

**Map.** Symmetrical ancient-stone chambers divided by mirror-water channels, identical throne rooms, clean walls, and purple-green anchor light.

**Objectives.** Secure 3 mirror anchor locations and defeat the scenario's required enemy leader.

**Implemented special events.** Each anchor removes a defensive bonus from Istrava. A hostile Ranger reflection appears mid-scenario. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 08. Raining Blood

**Summary.** A crimson reservoir rains upon an unfinished fortress, carrying stolen life and obedience into the body of an ancient ruler. Souls hang above the channels like ornaments, stabilizing the resurrection. The Hunter must close the sluices, destroy the ritual pylons, and bring down Kharos and his drowned warden. When the system ruptures, the entire cavern begins to flood.

**Characters.** The Hunter; Meris Vell, a captive engineer; Kharos the Red-Crowned; Uln the Drowned Warden; the Hanging Choir.

**Map.** A tiered reservoir of dark water, stone channels, hanging bridges, ritual towers, and a central ruined fortress. Crimson-purple tint.

**Objectives.** Secure 4 sluice control locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Activating sluices changes nearby floor to muddy water and damages adjacent undead. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 09. Unguarded Instinct

**Summary.** Blood magic from the reservoir sharpens the Hunter's senses while feeding impulses that do not feel like his own. The only possible cure is hidden inside an asylum whose wards were designed to divide body, soul, and conscience. The Hunter must recover the ward sigils and enter the treatment circle while Doctor Vael releases the asylum's surviving experiments. The player may accept controlled corruption for power or pursue a slower cleansing.

**Characters.** The Hunter; Sister Tirin, a healer; Doctor Vael; the Feral Echo; unquiet patients.

**Map.** A radial asylum with four cell wings, damaged stone rooms, mycelium, alchemical pools, wooden doors, and a central treatment circle. Purple-green tint.

**Objectives.** Secure 3 ward sigil locations and defeat the scenario's required enemy leader.

**Implemented special events.** Each sigil reduces the Hunter’s corruption counter by one. A Ghast manifestation arrives on turn five. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 10. Born of Fire

**Summary.** Beyond the asylum lies a forge where corpses are burned clean of memory and rebuilt as weapons. Every furnace is fed by bound spirits and every completed blade contains someone who once resisted. The Hunter must disable the furnaces, destroy the forge heart, and kill Azkar and Vharr. Cooling the machinery frees its captives; overloading it is faster and far less merciful.

**Characters.** The Hunter; Oren Flint, a captive smith; Azkar Born-in-Flame; Vharr the Bone-Smith; Asha of the Embers.

**Map.** An industrial forge divided by lava channels, mine rails, dwarven floors, furnace bridges, binding circles, and a central forge heart. Orange-yellow tint.

**Objectives.** Secure 3 furnace control locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Furnaces generate undead until disabled. Activating a control causes a local explosion. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 11. Fictional Reality

**Summary.** The next cavern contains a human city beneath a bright false sky. Its people believe the surface has fallen and that Provost Caldrin alone protects them from staged undead attacks. The Hunter must gather evidence, reveal the corpse warehouses, and overthrow Caldrin and his necromantic partner Morrowmask. Destroying the illusion forces the population to confront the cavern walls around them.

**Characters.** The Hunter; Veyla Sorn, a dissident; Provost Caldrin; Captain Rusk Var; Morrowmask.

**Map.** An orderly underground city of roads, human villages, interior floors, hidden corpse rooms, and illusion machinery. Gold light turns purple-green when controls fall.

**Objectives.** Secure 4 evidence cache locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Each cache adds to the campaign truth counter. Undead stage a raid on turn six. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 12. Read Between the Lies

**Summary.** The frightened city turns toward a temple promising salvation and a road to the surface. Prelate Othmar converts donations into obedience and prayers into contracts claimed by the lich beneath his altar. The Hunter must expose the fraud, break the soul reliquaries, and defeat Othmar and the Benefactor before the final ceremony binds the congregation forever.

**Characters.** The Hunter; Maelis, a doubtful acolyte; Prelate Othmar; Elden Grey; the Benefactor.

**Map.** A bright ancient-stone temple above a dark catacomb, with rugs, donor chambers, hidden stairs, reliquaries, and green-red soul channels.

**Objectives.** Secure 3 soul reliquary locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Reliquaries strengthen the Benefactor. Destroying one releases a small undead wave. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 13. Aggressive Perfector

**Summary.** A hidden laboratory attempts to combine the strongest traits of living and undead bodies. Its failed creations fill the cells, while a perfected copy of the Hunter waits in the central chamber. The Hunter must disable the vats, defeat the imitation built from his choices, and destroy Sileth's archive. Every vat can be opened carefully or shattered with whoever remains inside.

**Characters.** The Hunter; Kessa Thorn, an altered test subject; Magus Sileth; the Perfect Hunter; the Rejected.

**Map.** Clean and damaged laboratory rooms, green pools, mycelium, five vat stations, surgical corridors, and a central duplication chamber. Purple-green tint.

**Objectives.** Secure 4 perfection vat locations and defeat the scenario's required enemy leader.

**Implemented special events.** A Ranger duplicate appears after two vats are disabled. Vats release different undead reinforcements. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 14. Ghosts of War

**Summary.** The laboratory collapses into an ancient battlefield where spectral armies repeat a war whose kingdoms vanished centuries ago. The cabal has chained their memories to three command standards. The Hunter must break or purify the standards and defeat Marshal Vaulk and Iskar. Spirits released through mercy return as allies; spirits dominated through corruption obey for different reasons.

**Characters.** The Hunter; Teren Oss, a historian; Marshal Vaulk; Iskar the Banner-Wraith; three forgotten ghost captains.

**Map.** A broad ruined battlefield with collapsed trenches, broken castles, stone bridges, three standards, and spectral green zones under red-purple light.

**Objectives.** Secure 3 command standard locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Active standards repeatedly spawn Ghosts. Capturing them adds to alliance strength. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 15. Tormentor

**Summary.** An abandoned underground city appears empty, yet shadows stop whenever they are watched and familiar voices call from unopened doors. The Tormentor feeds upon the moment before violence rather than the killing itself. The Hunter must light the ward braziers, preserve at least one witness if possible, and force the unseen predator into a place where it can be killed. Civilians can guard the lights—or become lures in the dark.

**Characters.** The Hunter; Elra Noll, a survivor-guide; three frightened civilians; the Tormentor; lesser Whisperers.

**Map.** A dense ruined city of winding streets, courtyards, abandoned houses, fungus, four ward braziers, and heavy shroud. Purple-black tint.

**Objectives.** Secure 4 ward brazier locations and defeat the scenario's required enemy leader.

**Implemented special events.** Each brazier removes concealment from the Tormentor. Shadows arrive from unlit districts. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 16. War Ensemble

**Summary.** At the great crossroads the conflict becomes open war. Undead columns march toward three surface shafts while freed miners, citizens, spirits, and former prisoners gather according to the choices made along the descent. The Hunter must destroy the invasion gates and kill Bone Marshal Rhadek and Banebow Keth before a commander reaches the surface. Engineers can dismantle each gate safely—or carry charges on a one-way mission.

**Characters.** The Hunter; Nara Feld, engineer; Commander Bren Caul; Bone Marshal Rhadek; Banebow Keth; the gathered resistance.

**Map.** A large three-front crossroads with fortified roads, bridges, rails, ruined keeps, chasms, lava channels, and three invasion gates. Red-orange tint.

**Objectives.** Secure 3 invasion gate locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Prior rescue totals grant gold and allied veterans. Gate captures trigger large undead counterattacks. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 17. Repentless

**Summary.** The cabal's outer fortress is defended by living soldiers who remain awake inside magical compulsion. The Hunter must continue forward without confusing relentless purpose with indiscriminate cruelty. Three ward rings protect Magister Vorn and Saedra. Each can be opened by a key, a control circle, or a living sacrifice, allowing the player's established moral method to become a direct tactical choice.

**Characters.** The Hunter; General Jalen Rusk and the bound garrison; Magister Vorn; Magister Saedra; Warden Kelm.

**Map.** A layered fortress of dark stone, three ward rings, lava moats, control towers, bridges, and a sealed descent gate. Purple-red tint.

**Objectives.** Secure 3 fortress ward locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Breaking wards frees nearby human soldiers. Sacrifice choices instead grant gold and damage the enemy leaders. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 18. Eyes of the Insane

**Summary.** A memory chamber assembles fragments of every previous battlefield into an impossible whole. The dead return with accusations shaped from the campaign's actual sacrifices and failures. The Hunter must destroy the memory lenses, distinguish the true Nyxara from her false images, and survive the final assault on his identity. The chamber cannot erase what happened; it can only decide who controls the meaning.

**Characters.** The Hunter; the Witness; Seer Nyxara; false Nyxaras; echoes of named dead and surviving companions.

**Map.** A fragmented map combining corpse chamber, arena, reservoir, forge, city, and battlefield terrain into colored memory quadrants.

**Objectives.** Secure 4 memory lens locations and defeat the scenario's required enemy leader.

**Implemented special events.** Each lens summons an echo from a previous scenario. Campaign sacrifice totals alter the opening dialogue and bonus enemy count. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 19. Spirit in Black

**Summary.** At the deepest point beneath Esten stands the throne of Nhal-Zor, the ancient will that shaped the cabal through generations of dreams. Four rivers of imprisoned souls feed its immortality. The Hunter must break the soul chains and destroy Nhal-Zor's forms. Souls may be released, shattered, or consumed, and those deliberately sacrificed earlier return as guards around the throne.

**Characters.** The Hunter; Oris the Unclaimed; Nhal-Zor; four conceptual Chain Keepers represented by the chain objectives and undead reinforcements; remembered dead.

**Map.** An infernal throne complex with four wings, soul-chain braziers, lava rivers, ethereal abysses, ancient stone, and a central black keep.

**Objectives.** Secure 4 soul chain locations and defeat the scenario's required enemy leaders.

**Implemented special events.** Each chain weakens Nhal-Zor and spawns an undead guardian. High sacrifice totals grant the enemy extra gold. The named captive presents the campaign's explicit rescue-versus-bait choice.
### 20. The Final Command

**Summary.** The Final Command passes through the caverns like a heartbeat and every corpse beneath Esten begins marching toward the surface. The underground kingdom collapses even as its command nexus continues issuing orders. The Hunter must sever the command arteries, kill the surviving cabal, destroy the nexus, and escape through the original sinkhole. Allies, hostile memories, equipment, and the final ending all reflect the campaign's accumulated rescue, sacrifice, truth, alliance, and corruption variables.

**Characters.** The Hunter; the Last Survivor; High Magister Serath; Commandant Velis; Kharos; surviving allied factions and remembered dead.

**Map.** A large engineered command fortress with three arteries, rail-fed reserves, lava channels, pylons, the central nexus, and a collapsing route back to the sinkhole.

**Objectives.** Secure 4 command pylon locations and defeat the scenario's required enemy leaders.

**Implemented special events.** All three enemy leaders are required. Once the pylons and leaders fall, the escape phase begins and the Hunter must reach the western sinkhole. The named captive presents the campaign's explicit rescue-versus-bait choice.


## Testing Checklist

Run `python3 tools/validate_wpb.py` from inside the campaign directory. It checks the required filenames, scenario chain, map row widths, known terrain codes used by this package, music placeholders, and basic WML tag balance.

In Wesnoth, test at least the following:

1. The campaign appears in the campaign selector on all three difficulties.
2. Scenario 1 starts with the custom Hunter and can reach Scenario 2.
3. Every labeled objective fires once and changes terrain.
4. Bosses killed before the final objective are still counted correctly.
5. Objective locations completed before bosses are still counted correctly.
6. Rescue and bait options both work and persist into the next scenario.
7. Recallable rescued units carry over.
8. Scenario 9's one-use context-menu ability functions.
9. Scenario 16's alliance gold scales with prior rescues.
10. Scenario 19's enemy gold scales with deliberate sacrifices.
11. Scenario 20 enters escape mode only after four pylons and all three enemy leaders are defeated.
12. Both final ending texts can be reached.

## Known First-Build Limitations

- This package has been structurally validated in the build environment, but the Wesnoth executable and official `wmllint` were not available there. The first launch on an installed Wesnoth 1.18 system remains the authoritative runtime test.
- The sophisticated design document described several mechanics—moving water fronts, multi-phase arena rounds, dynamic civilian belief, exact campaign-history apparitions, and more elaborate AI goals. This first build implements their playable core using labeled objectives, reinforcements, terrain changes, persistent choices, and multi-leader victories. Those systems are intentionally isolated for later expansion.
- Balance values are placeholders. Expect to tune turn limits, gold, recruitment, and reinforcement timing extensively.
- The real music has not yet been inserted.
- Story portraits and bespoke art have not yet been created; core art is used throughout.

## Licensing and Mainline Assets

Campaign WML, prose, generated maps, validator, and placeholder audio in this package are released under the GNU GPL version 2 or later. Core images, unit definitions, terrain graphics, and sounds referenced by filename remain part of Battle for Wesnoth and retain their original licensing and attribution.
