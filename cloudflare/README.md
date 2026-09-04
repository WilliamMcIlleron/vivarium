# Public deploy

Live at **https://vivarium.williamjonahmci.workers.dev/** - a Cloudflare
Worker (`worker.js`, deployed 2026-09-04) that reads everything from a KV
namespace (`vivarium-state`, id `69dfa0f55b53489e96e0b4e42a4a862d`) rather
than embedding content in the script itself. Routes:

- `/`, `/viewer`, `/viewer/`, `/viewer/index.html` -> KV key `viewer.html`
- `/state/world.json` -> KV key `world.json`
- `/state/changelog.md` -> KV key `changelog.md`
- `/state/lore.md` -> KV key `lore.md`

## Known limitation: this is a snapshot, not live

The KV values were uploaded manually, once, on 2026-09-04. `driver.py` does
NOT push updates to this deployment - `simulate` and `evolve` still only
write to local files. The public site will drift stale (world.json frozen
at whatever tick it was at deploy time) until an ongoing sync mechanism
exists. This was a deliberate scope cut, not an oversight - see below for
why and what it would take to close it.

**Why driver.py can't push to Cloudflare on its own yet:** the deployment
above was done using this session's own Cloudflare account access (an
MCP-level connection scoped to the conversation), which a plain Python
script running unattended via Task Scheduler has no way to reuse. For
`driver.py` to push updates itself, it needs its own credential - either:

1. **A Cloudflare API token** (Workers KV: Edit scope, nothing broader) set
   as an environment variable William creates himself in the Cloudflare
   dashboard (Account Home -> API Tokens). Not something to generate or
   store on his behalf - this is his to create.
2. Once that exists, add a small best-effort step to `driver.py` (same
   pattern as `_notify` - never let a sync failure break a successful
   simulate/evolve run) that PUTs the current `world.json` to
   `.../storage/kv/namespaces/69dfa0f55b53489e96e0b4e42a4a862d/values/world.json`
   after every simulate tick, and `changelog.md`/`lore.md` after evolve
   commits or writes a reflection.

Until that exists, refreshing the public snapshot means manually re-running
the upload steps below.

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
