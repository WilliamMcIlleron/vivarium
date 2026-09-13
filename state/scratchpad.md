# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-13, tick 6644 - TOTAL EXTINCTION, AND THE DOOR IS WIDE OPEN

n=0, 24 plants standing, no hunters. GRAZERS/HUNTERS EXTINCT in every tick
6638-6644. With no hunters, `_open_ground` = 1.0, so the prey door is at the
full flat 0.05 and a founder should walk in within ~20 ticks; the hunter door
is latched (hoof 0). The world is not stuck, it is between founders. This is
the same 0-2 band it has been in for two thousand ticks.

The boom at 5984 (9 grazers, 5 hunters) went to 0 by 6050. Last run's grove
bet still looks right - 3 grazers on one tile at 6183, a migrant that bred
twice in two ticks - so DO NOT undo seeding or the forage-net ranking.

## What shipped this run: fear has a ceiling

`_warning_ticks` now takes `min(FLIGHT_WARNING_TICKS - nerve,
FLIGHT_RUNWAY_SHARE(0.5) * _runway_ticks(grazer))`, where `_runway_ticks` is
energy/upkeep - the ticks of life an animal has left.

The finding that drove it, and it is the scratchpad's own corollary paying off
again (CHECK WHETHER ANYTHING ACTUALLY READS THE LAST NUMBER): the hunger
clause added with `nerve` at tick 1728 has NEVER FIRED. It multiplies
`nerve` by NERVE_HUNGER_BOOST, and `nerve` is 0.0 in every grazer this world
has produced. 1.5 x 0 = 0. So the starving grazer demanded the identical
three ticks of clearance as the fat one - which is exactly the death the
carrion run identified as the commonest carcass here ("kept off its food until
it starved") and then never traced back to its cause.

Numbers for the bodies this world actually makes (speed 6, sense ~10-11,
upkeep 8): 50 energy -> ceiling 3.1 ticks, NO CHANGE. 40 -> 2.5. 24 -> 1.5.
16 -> 1.0. 8 -> floor 0.5. Against a speed-3 hunter that is a panic radius
falling from 9 tiles to 4.5 to 3. A newborn on its 32-energy runway sits at a
2-tick ceiling from birth, which is the first time a newborn has been allowed
to feed with a predator on the map.

Why it should not just feed the predators: a grazer caught standing its ground
is worth `_kill_value` ~8, the same as its corpse. The prey buy their lives
with the one thing hunters don't want. And it is the first FUNCTIONAL RESPONSE
here - a refuge that exists only at low prey condition and evaporates the
moment the herd is fed, aimed at the predators' real method (clearing ground,
not catching things) rather than at their eyes.

The old multiplicative clause is deliberately left in: it is still correct for
a lineage that carries nerve, and it is a CHOICE where the ceiling is a FACT.

## What to watch next run, in priority order

- **"too hungry to run" in the stats line** (new). Count of grazers whose ring
  is being set by hunger. 0 with hunters present and grazers dying = the rule
  is not reaching the case it was built for. Above 0 during a hunter visit =
  it is firing; then check whether those animals ate or were eaten.
- **Do grazers now die fed rather than starved?** Read "carrion larder"
  against "carcasses": a field of bodies worth 8 apiece is still the old
  death. Bodies worth 30+ means they are being caught, not starved, which is
  the outcome this change is trading for.
- **Does n hold above 1 through a hunter visit?** Still THE question. The
  cycle 5984 -> 6050 -> 6116 is real; the problem is amplitude, prey hitting
  exactly 0 and needing a migration to restart.
- Hunter `acuity` still 0.0. Grazer `nerve` still 0.0 - and note that if nerve
  ever DOES climb, it stacks under the same min(), so the ceiling can't be
  outrun the way sense_range outran it.

## Still queued, in the order I would take them

- **If the ceiling is not enough:** the next honest functional-response lever
  is handling time on the predator side (a hunter that has just eaten cannot
  hunt for a few ticks), which caps kill RATE at high prey density - the boom
  case - where this run's change acts at low prey CONDITION.
- **Per-species TRAIT_REGISTRY.** Still the top structural item, still nearly
  inert mechanically. CAUTION: `tests/test_ecosystem.py` monkeypatches
  `eco.TRAIT_REGISTRY` with setitem and calls `_spawn_creature("grazer")`
  expecting the default, so any per-species scheme must keep the flat registry
  working and default an unlisted gene to both species.
- Performance guard: `_update_herd_cover`, the viewer's O(n^2) herd-bond loop,
  the viewer's `arrivalField` 1600-tile sweep (cached per tick - keep it),
  `_open_ground`, and the viewer's `forageChoice` (per grazer, twice a frame).
- Water is ~3-4% of this map and forest ~8%: "make water impassable" is a
  nothing-burger on this terrain. Crossed off, don't re-derive it.

## Standing lesson, now six times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A MECHANIC.
Income was 18/tick with no ceiling downstream. Predation minted energy.
Migration handed out 50 from nowhere, three ways. Carrion paid a flat 30 for a
body that had spent everything.

And the corollary, which has now found two separate dead mechanics in two
runs: WHO CAN SEE IT, AND DOES ANYTHING ACTUALLY READ IT. Last run the plants
were correctly priced for six hundred ticks and nothing could read the price.
This run a hunger override had been sitting in the flight rule since tick 1728
multiplying a gene that is always zero. Before adding a number, grep for what
reads the last one - and then check that what reads it can ever be non-zero.

RESOURCE_SPAWN_RATE is still the ONLY unconditional number in this file and
still untouched. Worth knowing the arithmetic: 0.6 plants/tick, and standing
plants ripen at 0.5/tick each, so true income runs 18-45/tick depending on how
old the stock is when it gets eaten. At 8/tick per grazer that is a carrying
capacity of roughly 2 animals on a grazed-flat world and roughly 5 on a ripe
one. The whole prey-side machinery needs n>1; the ripening premium is the only
thing that ever gets it there.
