# Public deploy

Live at **https://vivarium.williamjonahmci.workers.dev/** - a Cloudflare
Worker (`worker.js`, deployed 2026-09-04) that reads everything from a KV
namespace (`vivarium-state`, id `69dfa0f55b53489e96e0b4e42a4a862d`) rather
than embedding content in the script itself. Routes:

- `/`, `/viewer`, `/viewer/`, `/viewer/index.html` -> KV key `viewer.html`
- `/state/world.json` -> KV key `world.json`
- `/state/changelog.md` -> KV key `changelog.md`
- `/state/lore.md` -> KV key `lore.md`

## Live sync (as of 2026-09-05)

`driver.py` pushes updates to this deployment itself now, via
`_sync_to_cloudflare()`: `world.json` after every `simulate` tick,
`changelog.md` after every evolve commit or reflection, `lore.md` after a
reflection, and `viewer.html` whenever an evolve commit touches
`viewer/index.html`. It authenticates with a Cloudflare API token (Workers
KV: Edit scope, nothing broader) that William created himself and set as
`CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID` environment variables - never
generated or handled on his behalf.

Same failure-handling shape as `_notify`: wrapped in try/except, a no-op if
the env vars aren't set, and a sync failure never breaks an otherwise-
successful simulate/evolve run. Unlike `_notify`, sync failures ARE logged
(to `logs/simulate.log` / `logs/evolve.log`) since a silently-stale public
site is worth being able to debug. Verified live 2026-09-05: a manually
triggered simulate tick showed up on the public site within seconds.

## How the initial deploy actually got built (read before repeating it)

Two real bugs surfaced doing this, both worth knowing before touching it
again:

1. **Anything containing template-literal-unsafe characters (backticks,
   `${`) breaks if embedded as an escaped JS string** - the viewer's own
   inline `<script>` uses template literals extensively, so embedding the
   raw HTML as a backtick-delimited string in a generated worker corrupts
   it. Fixed by JSON-encoding (or base64-encoding) any file content before
   embedding it as a plain quoted string.
2. **Large content (JSON-escaped or base64, doesn't matter which) reliably
   fails to transmit through this session's Cloudflare tool as one big
   literal** - tested up to ~16KB of non-repeating content failing with
   "Invalid or unexpected token" even when locally verified as valid
   syntax via `node --check`. A trivial repeated-character string of the
   same length worked fine, so it's specific to dense/varied content, not
   pure size. **Confirmed safe up to 5000 characters** in one call.

Working approach: base64-encode the file, split into ~4000-character
chunks, upload each chunk to its own temporary KV key (small individual
calls, proven reliable), then run ONE more small call that reads all the
chunks back via `cloudflare.request()`, concatenates them, `atob()`-decodes
the result, and writes the real key - the large blob only ever exists
inside the Cloudflare execution sandbox, never passing back through the
tool-call transport that kept failing. Delete the temporary chunk keys
after. The Worker script itself stays tiny (just routing logic, no
embedded content) specifically so it never needs this treatment.

To refresh the snapshot with this approach, script the same steps against
the four files (`viewer/index.html`, `state/world.json`,
`state/changelog.md`, `state/lore.md`) using the account ID and namespace ID
above.
