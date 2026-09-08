# Changelog

Append-only. Every `evolve` run adds one entry here before committing, whether
it succeeded, failed tests, or was reverted. This is the human-readable trail
of everything the world has decided about itself.

## Genesis

World created. Single species, single resource type, 40x40 grid, mutation on
speed and sense_range. See `state/goals.md` for what happens next.

## 2026-09-03T20:16:59

evolve run REJECTED: 229 lines changed, max is 150

## 2026-09-03T20:18:36

evolve run REJECTED: 224 lines changed, max is 150

## 2026-09-03T20:39:52

evolve run REJECTED: 409 lines changed, max is 350

## 2026-09-04T10:12:06

evolve run REJECTED: 449 lines changed, max is 350

## 2026-09-04 (manual dev session, not an evolve run)

All 4 evolve attempts above had been rejected by a guardrail bug: the diff-size
check counted each proposed file's full length instead of the actual changed
lines, so any proposal touching both `rules/ecosystem.py` and `viewer/index.html`
(351 lines combined) exceeded the 350-line cap regardless of how small the real
edit was - evolve could never succeed. Fixed `_validate_proposal` in `driver.py`
to diff against the file on disk. Also replaced the protected-path denylist with
an allowlist (evolve may only write `rules/`, `viewer/`, `state/goals.md`) and
added `tests/`, `state/world.json`, `state/changelog.md` to `PROTECTED.md` so
evolve can no longer legally rewrite its own tests or history to force a pass.

Separately, hand-built a predator/prey split since the world was still one
species and the daily evolve budget makes organic growth very slow: grazers
(unchanged food-seeking, now flee any hunter within sense_range) and hunters
(faster, seek out grazers, eat them on contact, costlier to reproduce so one
lucky kill doesn't spiral into a hunter population that outstrips its own food
supply). Also fixed `RESOURCE_SPAWN_RATE` (0.08 -> 0.6): at the old rate the
original single-species world was already headed for starvation-driven
extinction within a few hundred ticks, independent of anything predator-related.
`viewer/index.html` now renders hunters as a distinct red/orange triangle
against the grazer's green circle, per the visual parity rule. See
`state/goals.md` for the known remaining balance risk (grazers going fully
extinct in a minority of long runs) and what's next.

## 2026-09-04T21:19:48

evolve run FAILED: could not parse model response as JSON.

## 2026-09-04T21:23:24

evolve run REVERTED (tests failed): attempted - The world was sitting at 1 grazer vs 7 hunters at tick 79 - the known extinction-risk balance issue actually happening, not hypothetical. Implemented the top candidate from goals.md: forest tiles now give grazers cover, halving a hunter's effective sense_range against a grazer standing on a forest cell (`_nearest_creature` in rules/ecosystem.py takes an optional `terrain` arg, passed only for the hunter-seeking-grazer lookup so grazers' own threat detection is unaffected). No viewer change needed since forest tiles are already rendered distinctly - this only changes behavior on an existing visual element, not what's drawn.

## 2026-09-05T03:03:50

Added the first real trait to the empty genome framework: `camouflage` (grazer gene, 0-3, mutation step 0.5) shrinks a hunter's effective sense_range specifically when that hunter is hunting that grazer, via a new `camouflage_aware` flag on `_nearest_creature` - a second, independent lever against predation alongside sense_range, giving grazers and hunters a real arms race to mutate against each other instead of just tuning constants. Updated `viewer/index.html` so grazers visibly fade toward the background in proportion to their camouflage value, per the visual parity rule.

## 2026-09-05T11:02:59

The genome snapshot showed grazers averaging speed 3.0 against hunters' 2.0 - the reverse of the intended predator/prey asymmetry - because speed had zero energy cost, so it could only ratchet upward, while hunters keep getting reset to the species default every time they go extinct and migrate back in (as just happened again around tick 224). Made MOVE_COST scale with a creature's own speed (`creature.energy -= MOVE_COST * creature.speed`) so being fast now costs energy every tick, giving speed a real tradeoff against food-finding instead of one-way escalation that only ever favored whichever species last avoided a population crash. Purely a constants/mechanics change with nothing new to render, so no viewer update needed.

## 2026-09-05T22:08:46

The event log shows twenty consecutive ticks of HUNTERS EXTINCT before a lone migrant wandered back in at tick 878: a hunter burns 2 energy/tick since move cost started scaling with speed, and with ~10 grazers scattered over 1600 tiles it starves long before it corners a fleeing one. Added carrion - any death that isn't a kill (starvation, old age) leaves a static carcass worth 30 energy that rots after 40 ticks, hunters walk toward whichever is nearer (live prey or a carcass) and scavenge one they're standing on if they made no kill that tick. It's a lifeline rather than a living (reproduction still needs the 110-energy threshold, so it still takes real kills), and it's self-correcting in both directions: predation produces no carcasses, so a hunter boom eats its own scavenging supply, while a hunter crash leaves an unhunted grazer population's bodies lying around for the next migrant. `viewer/index.html` draws carcasses as hollow bone-grey rings that fade as they rot, plus a carcass count in the stats line.

## 2026-09-06T03:09:34

Gave the world a genetic memory: `World.lineage` records the genome of every creature that successfully reproduces (last 8 per species), and a migrant arriving after an extinction now spawns as a mutated descendant of that remembered stock instead of a blank species default. Hunters were sitting at exactly the default genome (speed 2.0, sense 4.67, camouflage 0.0) after ~20 straight ticks of HUNTERS EXTINCT while grazer camouflage climbed to 0.58 — every crash was wiping the predator side of the arms race, so camouflage had nothing evolving against it; an extinction is now a bottleneck rather than a factory reset. `viewer/index.html` marks recent migrants with a fading dashed violet halo and shows the remembered bloodline for each species under the legend, so you can see what the next arrival will inherit.

## 2026-09-06T19:07:49

Lineage memory paid off - the hunter that migrated in at tick 1132 arrived with sense_range 6.0 instead of the old 5.0 default, so hunter genomes now survive their crashes - which finally makes a predator-side counter-gene worth having. Added `acuity` (hunter gene, 0-3, step 0.5): it adds to a hunter's effective sense_range only when looking for live prey, cancelling grazer camouflage point for point, and costs 1 energy per tick per full point (half-points free by truncation) so it can't ratchet upward for free the way speed once did - camouflage was at 0.538 and climbing with literally nothing evolving against it. `viewer/index.html` draws acuity as concentric orange sensing rings beneath a hunter's triangle (more rings, reaching further, the keener the predator) and the remembered-bloodline readout now shows each species its own side of the arms race: camo for grazers, acuity for hunters.

## 2026-09-07T11:46:33

evolve run REVERTED (tests failed): attempted - The world went from 13 grazers and 1 hunter at tick 1147 to 2 grazers and 4 hunters at tick 1229 - a hunter boom converting an entire prey population into predators faster than it could replace itself, which is the exact sequence that ends in GRAZERS EXTINCT and then the hunters starving too. Added predator interference: a hunter pays 2 energy per tick for every rival hunter within 3 tiles, and a hunter with no prey or carcass in range now walks away from its nearest rival instead of wandering at random, so predation spreads across the grid instead of piling onto the last few animals. It's density-dependent rather than a flat nerf - a lone hunter, this world's usual state, pays nothing - so it brakes the boom without deepening the chronic hunter extinctions; `viewer/index.html` strings a pulsing red tension line between every contesting pair and counts contested hunters in the stats line.

## 2026-09-07T12:04:34

Grazers went from 13 to 1 between ticks 1147 and 1234 - a hunter boom mowing down a scattered prey population, which is the sequence that ends in GRAZERS EXTINCT and the hunters starving behind them. Added herd cover: every other grazer within 2 tiles subtracts 0.5 (cap 2.0) from a hunter's effective sense_range when it looks for that grazer, plus a `gregariousness` gene (0-3, step 0.5) that makes an unthreatened grazer walk toward company instead of food, so clumping is an evolvable strategy paid for in missed meals rather than an accident of position. It's density-dependent and prey-side - a lone straggler gets nothing, so it brakes the boom without deepening the chronic hunter extinctions, and `acuity` is already the counter; `viewer/index.html` threads soft green bonds between herd-mates (brighter with deeper cover), rings gregarious grazers with a fine dotted circle, and counts herded grazers in the stats line.

## 2026-09-07T21:39:13

At tick 1728 the world had 2 grazers against 6 hunters that had drifted down to speed 1 - too slow to catch anything, living entirely off carcasses - while grazers at sense_range 7 and speed 5 were dying of STARVATION rather than predation: fleeing was a reflex, any hunter anywhere in a 15x15 sense box made them bolt, and with six hunters on the grid that box was nearly always occupied, so they burned 5 energy a tick running and never stood on a resource long enough to eat. Added `nerve` (grazer gene, 0-3, step 0.5): it shrinks the distance at which a grazer abandons its meal and runs (`_panic_radius`) without touching what it perceives - a nervy grazer sees the predator perfectly well and keeps eating - amplified 1.5x while hungry, floored at one tile, and priced in the shorter head start it leaves itself; at nerve 0 the panic radius is exactly sense_range, so this world's original reflex is still the starting point. `viewer/index.html` draws each grazer's flight bubble as a thin ring at its actual panic radius, turning amber and dashed when hunger is what's shrinking it, and counts grazers currently holding their nerve with a hunter in sight.

## 2026-09-08T09:27:09

At tick 1870 the world held 0 grazers and 5 hunters, with GRAZERS EXTINCT in nearly every tick since 1813 - and the reason the hunters weren't extinct too was that they were eating each other: with no prey on the grid, the only deaths were hunter deaths, and each one dropped a 30-energy carcass that another hunter scavenged, a closed cannibal loop that let five predators coast indefinitely with no food source and killed every migrating grazer on arrival. Carcasses now remember whose body they are (`Carrion.species`) and only a grazer's is edible (`SCAVENGEABLE_CARRION`), so hunters neither walk toward nor gain anything from their own dead - which restores the negative feedback carrion's own comment always claimed it had (no grazers means no carrion means the hunters really do starve out, which is exactly the window a re-migrating grazer needs) without touching predation, energy values, or any gene. `viewer/index.html` draws a grazer's carcass as the familiar bone-grey ring with a crossbar and a hunter's remains as a dotted rust ring struck through with an X, and the stats line splits "carcasses" (the food supply) from "hunter remains" (predators that starved, now a dead end).

## 2026-09-08T11:09:17

Terrain has been decorative since it was built, and with GRAZERS EXTINCT in nearly every tick since 1813 there was nowhere on 1600 identical tiles for a re-migrating grazer to be safer than anywhere else - so forest canopy now subtracts 1.5 from a hunter's effective sense_range when it looks at a grazer standing under it (the same number camouflage and herd cover pull on, with acuity as the existing counter), a fleeing grazer breaks for the best cover it can reach instead of running in a straight line, and resources are placed by biome fertility so the safest ground is also the emptiest: cover and food are in different places, and a grazer has to leave the trees to eat. Total food is unchanged - RESOURCE_SPAWN_RATE still decides whether a resource appears, fertility only decides where it lands - and `viewer/index.html` stipples forest tiles with a canopy texture, fades a grazer standing under it the way camouflage already does, and counts "under canopy" in the stats line. Also corrected goals.md's terrain bullet, which claimed creatures ignore the terrain completely; that is no longer true, and the "don't regenerate or redesign the map" rule is kept.
