# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-13, tick 6050 - the boom at 5984 did NOT hold, and here is why

  5984   9 grazers, 5 hunters, 38 resources  <- the best this world has been
  6019-6030  GRAZERS EXTINCT, twelve straight ticks
  6031   a grazer migrates in
  6044   GRAZERS EXTINCT again - it lasted THIRTEEN ticks
  6050   0 grazers, 2 hunters (speed 3, sense 7, acuity 0.0), 23 resources

The boom happened exactly as the migration trilogy intended and then ran
straight back into the same churn: one grazer every ~20 ticks, each dead
inside fifteen. Do NOT read that as the migration gates failing. Two speed-3
hunters menace only ~45% of the grid, so open ground is ~55% and the prey door
is legitimately near its full rate; the grid really is open. The migrant dies
because it is ALONE (no herd cover, nothing to breed with) and because the
hunters were being paid to keep it that way. See below.

## What shipped this run: a body is worth the body

CARRION_ENERGY was the flat 30 the file's own header had been pointing at for
three runs. Do the arithmetic on 6031-6044: a grazer arrives with 50, is kept
off its food, starves, and hands the predators that starved it a carcass worth
30 - versus the 8 they'd have banked catching it alive one tick earlier. The
predators were collecting a BONUS for having run their food supply to zero.
That is the prey side funding the siege again, through the corpse this time
rather than through the door.

Now: `Carrion.energy` records what the animal had when it died, `_meat_value`
is the shared arithmetic behind both `_kill_value` and the new
`_carrion_value`, and a starved body is worth 8 while an old fat one is worth
~40. `energy=None` (old saves, and anything constructed without it) still
returns the flat CARRION_ENERGY, which is what keeps this backwards compatible
AND keeps any existing test that asserts +30 on a hand-built carcass passing.
Deliberately left alone: `_nearest_carrion` still walks to the NEAREST body,
not the richest, so a hunter can still waste three ticks on an 8-energy
carcass.

The bet, stated plainly so the next run can check it: a hunter with no live
prey should now starve out within ~20-25 ticks instead of limping for 60+.
That clears the grid, open ground goes to 1.0, the grazers' door opens onto a
ripened larder, and the hunters' door stays shut until the herd is worth 90
hoof. That is precisely the 5944-5984 sequence, which was luck; this is meant
to make it the default.

## What to watch next run, in priority order

- **Chronic hunter extinction.** This is the failure mode I have just bought a
  risk of. The old justification for flat carrion was the hunter extinctions of
  ~tick 1400; my claim is HUNTER_MIGRATION_HOOF has taken that job over. If
  hunters are absent for 500+ consecutive ticks with a healthy herd standing,
  the claim is wrong - and the fix is NOT to restore flat carrion, it is to
  lower HUNTER_MIGRATION_HOOF (90) so the door opens on a thinner herd.
- Read "carrion larder" against "carcasses" in the viewer. Many bodies worth
  almost nothing = animals starved rather than eaten = the siege is now
  unprofitable, which is the whole point.
- Does hunter `acuity` climb off 0.0? Still 0.0 at 6050, one run after the dark
  shipped. Give it another ~1500 ticks with an actual population before
  concluding ACUITY_COST is mispriced.

## Still queued, in the order I would take them

- **Per-species TRAIT_REGISTRY.** Top structural item and the data is still
  damning: grazer avg acuity ratcheted to 2.944/3.0 by pure drift in the
  species that cannot read it and is not billed for it, while hunters sit at
  0.0. `provisioning` is the shared counter-example that must keep working.
  Mind save-compat: existing creatures carry the inert keys in `traits`.
- A lone migrant cannot found a population against two standing hunters even on
  open ground. Every prey mechanic (herd cover, gregariousness, the breeding
  bar) needs n>1 to do anything. If the crash cycle survives the carrion change,
  THIS is the next real problem, and the honest framings are: arrivals come in
  small groups, or a founder gets a grace period. Both are delicate - think
  hard before reopening migration, which the last three runs settled.
- Performance guard: `_update_herd_cover`, the viewer's O(n^2) herd-bond loop,
  the viewer's `arrivalField` 1600-tile sweep (cached per tick - keep it that
  way) and `_open_ground`.

## Standing lesson, now five times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A MECHANIC.
Income was 18/tick with no ceiling downstream. Predation minted energy. Migration
handed out 50 from nowhere, to the wrong species, three different ways. And
carrion paid a flat 30 for a body that had spent everything it ever had.

RESOURCE_SPAWN_RATE is now the ONLY unconditional number left in this file.
Everything else is gated on something the population itself moves. When the
next thing appears out of nowhere, that is where it came from - and note that
ripening already made the PLANT side density-dependent without touching the
rate, so the rate may simply be correct.

## Post-mortem kept from 2026-09-13 (tick 5522): ripening, resolved

The original prediction was "a long absence banks a feast"; at 5522 I called
the mechanism unreachable. At 5654 the grid held 58 resources and a single
migrant bred twice off them in seven ticks, and at 5945 it did it again after
a total extinction. Ripening pays for chronic emptiness, not only for total
extinction. Settled - stop re-deriving it.
