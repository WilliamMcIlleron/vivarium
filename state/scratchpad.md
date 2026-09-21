# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-21, tick 11499 - the blind predator

**The brood gate worked, tentatively.** History reads 4, 2, 19 (tick 11281),
8 (now). The previous boom went to 45 and then to 2 in ~200 ticks; this one
topped at 19 and has come down to 8 over 218 ticks. Not proof, but that is the
shape the gate was built to produce. Leave BROOD_LARDER_SHARE at 1.0 and watch
the next boom. Two data points beat one.

**Every body is at the floor.** Snapshot: speed 1.0 and sense 5.0 in ALL eight
grazers - speed 1 is the hard minimum and sense 5 is the species default.
Traits: camo 0.562, acuity 0.5 (inert), greg 0.0, nerve 0.188, provisioning
0.125. So the entire price structure six runs built - MOVE_COST, FREE_SPEED,
FREE_SENSE_RANGE, _birth_weight, _parent_keep, _breeding_bar - is now charging
NOTHING, because every animal is inside every free allowance and every floor.
Upkeep 1, birth weight 20, parent keep 20, bar 60: all three flat floors.
The metabolic machinery is a no-op at this genome. That is not a failure; it
means the question has moved from "what does a body cost" to "what does a body
DO" - and the answer here is nothing, because with no predators camouflage,
nerve, gregariousness and acuity are all inert or pure cost. Seven genes, not
one with a live payoff. Selection has nothing left to act on.

**Provisioning did not crash from the ordering bug.** It read 1.25 at 11141 and
0.125 now, but 8 x 0.125 = 1.0, i.e. ONE animal carrying 0.5. That is a
population turnover diluting it, not selection killing it. The ordering
inconsistency (gift taken AFTER the bar, voiding _parent_keep) is real but at
upkeep 1 it costs a parent 7 of its 20 and is not fatal. Still queued, still
not urgent.

## The hunters cannot hunt. Work this through before changing anything else.

Grazer sense 5, camo 0.56. Hunter sense 5, acuity 0, speed 2, upkeep 2.

- Hunter's reach for live prey: 5 - 0.56 - herd - canopy - dark = **~4.4 at
  best, under 3 in a herd or at night.**
- Grazer's view of a hunter: a flat **5**, nothing subtracted, ever.
- Grazer's panic radius vs a speed-2 hunter: 2 x (3.0 - nerve) = **~5.6**,
  which is WIDER than its own eyes, so it bolts the instant it sees.

So the prey always sees first and always runs first, and the predator is a
blind man chasing a sighted one. The only kill available is a lucky 2-tile
blind step from distance 6 (outside the grazer's sight) to distance 4 (inside
the hunter's) - maybe 3 chances in 25 when it happens to be at exactly 6.
A migrant hunter has 50 energy at upkeep 2 = 25 ticks. It dies.

And it is SELF-SEALING: lineage records breeders, a hunter that cannot eat
cannot breed, so the memory never updates, and acuity - the one gene that would
fix it - needs two mutation steps and gets one per arrival at 10%.

Note also how binary this is, and do not forget it: D_grazer > D_hunter means
escape is certain, D_grazer < D_hunter means death is certain, because a speed-1
grazer cannot outrun a speed-2 hunter and cannot reach cover in the 3 ticks it
has. **Do not nerf grazer perception directly.** Any head-down / vigilance
penalty flips the knife edge wholesale and every grazer dies before speed can
re-evolve. I costed that out this run and backed off.

## Shipped this run

`World.foundings` + `FOUNDING_REFUSALS` (3) / `FOUNDING_WILD_STEP` (2) /
`WILD_DRAW_MAX_ROUNDS` (18) / `_wild_rounds`. Every re-founding migrant
increments a per-species tally; `remember()` clears it. At 3 refusals the
re-founding door stops drawing on lineage entirely and hands out a
`_wild_creature` instead, walked 6 + 2*(refusals-2) rounds of ordinary mutation,
capped at 18. Default `refusals=0` everywhere, so tests/ and every old call site
are bit-for-bit unchanged.

The point: `_founding_reset_chance` asks if the range can AFFORD a body. A blind
hunter is cheap, so that gate reads 0% forever. This asks whether the body has
ever made a living here, which is the question the hunters have been failing.

## What to watch next run

- **`refused hunter` in the stats line.** It should climb 1, 2, 3... A hunter
  arrives roughly every 50 ticks while hoof value is over 180 (it is - 8 grazers
  at ~30 energy is ~230), so expect 3 refusals inside ~200 ticks and wild draws
  after that. If it is stuck at 0 or 1 the hunters are not even migrating and the
  hoof gate is what to read instead.
- **Does a wild hunter ever land viable?** It needs acuity >= 1.0 or sense >= 7
  to out-see a grazer. From 6 rounds that is maybe 1 draw in 10; at 12-18 rounds
  it should be common. So the first viable predator in thousands of ticks is
  probably 300-800 ticks out. Deliberately slow - I do not want a hunter boom.
- **If a hunter DOES establish: watch the grazers for 200 ticks.** Speed 1 prey
  is defenceless. The affordable adaptation is speed 2 (upkeep 2, halves
  capacity to ~9) or camouflage/gregariousness (herd cover). If grazers go fully
  extinct twice in a row after a viable hunter, raise FOUNDING_REFUSALS or drop
  WILD_DRAW_MAX_ROUNDS - do not gut the hunters again.
- **`crowded out` and `food per mouth`** - still the brood gate's readout, still
  worth a glance.

## Still queued, in the order I would take it

- **Provisioning vs `_parent_keep`.** Fold `_provision`'s gift into
  `_breeding_bar` so a generous parent saves for its generosity instead of
  paying for it out of the runway the bar promised it. Honest, energy-neutral,
  small.
- **Unify the two fresh-stock rules.** Flat `GRAZER_TRICKLE_FRESH_SHARE` (0.3)
  versus computed `_founding_reset_chance`. Trickle should call the computed one
  and the constant should go. Now that refusals exist there are three of these;
  consider folding all three into one "how much do I trust the memory" number.
- `remember()` de-duplication (don't append a genome identical to one already
  in the window).
- `FREE_SENSE_RANGE` is 6, the default is 5, and 5/6/7 all cost exactly 0. So
  there is no price signal on sense_range at all in the band the animals live
  in, which is why it sits at a suspiciously round 5.0 in all eight. Not broken,
  just inert.
- Per-species TRAIT_REGISTRY: still not worth the refactor risk.
- Performance guard: `_brood_room`, `_open_ground`, `_forage_assignment` and the
  viewer's 1600-tile sweep are all O(n^2)-ish. Fine at n=8, fine at n=45.

## Standing lessons

1. CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A
   MECHANIC. Fourteen times confirmed.
2. A memory that only records successes cannot correct itself once the only
   remaining success is a failure by another name.
3. A price is not the only kind of cause.
4. Read the snapshot for what it IS, not for what it trends toward. Look for
   suspiciously round numbers.
5. Check what a function does when its optional argument is absent.
6. Read the population HISTORY, not just the head count.
7. A mechanic that reads only the actor's own state cannot be density-dependent.
8. **New: a gate built to test one property will sit at zero forever on a
   failure of a different property, and its zero reads exactly like success.**
   `_founding_reset_chance` has been reporting "hunter 0%" for thousands of
   ticks - the memory is affordable! - while the animal it kept waving through
   could not see its own food. Before trusting a gate's output, ask which
   question it asks, and then ask what ELSE could be killing the thing.
9. **And: check whether a contest is binary before tuning it.** Prey detection
   vs predator detection here has no middle: whoever sees first wins outright,
   because the speed gap makes every chase and every escape certain. A
   half-tile nudge is not a nudge, it is a switch.
