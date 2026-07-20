# Sound Asset Manifest

All sound references in the first build point to files verified in the Wesnoth 1.18 core sound tree. They are not copied into this package.

| File | Typical use in World Painted Blood | Mainline source path |
|---|---|---|
| `axe.ogg` | mine and weapon mechanisms | `data/core/sounds/axe.ogg` |
| `bat-flapping.wav` | bat crypts and stalking flight | `data/core/sounds/bat-flapping.wav` |
| `cave-in.ogg` | collapses, reservoir rupture, final escape | `data/core/sounds/cave-in.ogg` |
| `claws.ogg` | infernal throne effects | `data/core/sounds/claws.ogg` |
| `dagger-swish.wav` | the Still One and close ambushes | `data/core/sounds/dagger-swish.wav` |
| `explosion.ogg` | forge overloads and invasion gates | `data/core/sounds/explosion.ogg` |
| `fanfare-short.wav` | arena wave announcement | `data/core/sounds/fanfare-short.wav` |
| `fire.wav` | braziers and forge events | `data/core/sounds/fire.wav` |
| `fuse.ogg` | fortress ward destruction | `data/core/sounds/fuse.ogg` |
| `gold.ogg` | evidence and ledger discoveries | `data/core/sounds/gold.ogg` |
| `groan.wav` | corpse and ghost awakenings | `data/core/sounds/groan.wav` |
| `heal.wav` | cleansing, illusion, and soul events | `data/core/sounds/heal.wav` |
| `hiss-big.wav` | asylum manifestations | `data/core/sounds/hiss-big.wav` |
| `hiss.wav` | laboratory releases | `data/core/sounds/hiss.wav` |
| `human-die-1.ogg` | memory-chamber echoes | `data/core/sounds/human-die-1.ogg` |

To bundle later, create `sounds/` inside the add-on and copy the chosen files there using the same basenames. The campaign's binary path will prefer local files.
