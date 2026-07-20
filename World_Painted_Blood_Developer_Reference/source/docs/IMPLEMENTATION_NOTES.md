# Implementation Notes

## Design Level

This is a structurally complete first test implementation of the twenty-scenario chain. It has not yet received a full engine playthrough. It intentionally emphasizes stable, inspectable WML over highly abstract macro metaprogramming. Every scenario owns its story, sides, objectives, moral event, objective-site events, boss death events, reinforcements, and progression link.

## Objective State Model

Each scenario stores two local campaign variables, for example `wpb_s08_sites` and `wpb_s08_bosses`. Objective-site events and boss-death events both call the same generated completion condition, so the player may complete those requirements in either order.

Scenario 20 adds `wpb_final_escape`. Completing the pylon and boss counts changes the objectives rather than ending the scenario.

## Moral State Model

The explicit choice event is intentionally adjacent to the starting area. It avoids treating routine tactical casualties as moral decisions. Rescued captives become loyal Side 1 units and enter normal campaign persistence. Bait choices damage the principal boss and award gold so the anti-hero path is mechanically viable.

## Expansion Hooks

The following areas are natural next revisions after the first full playthrough:

- replace generic objective braziers with custom item art;
- expand Scenario 3 into a true multi-round arena state machine;
- add closing dialogue unique to every rescue/sacrifice combination;
- implement timed executions, rising-water masks, civilian belief, and controlled surrender;
- add custom Hunter AMLAs and corruption-based attack changes;
- add story portraits, campaign art, and a transparent Eidolon-based campaign icon;
- replace the silent music placeholders;
- tune AI goals and recruitment patterns scenario by scenario.
