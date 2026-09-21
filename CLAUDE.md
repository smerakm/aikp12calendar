# AIK Calendar Subs

Static HTML match-schedule page for AIK IBF (floorball), generated from
public ICS calendar feeds published by the Swedish Floorball Federation (IBIS).

**This file documents mechanisms and the reasoning behind them, not the
current data.** Which feeds exist, which league gets which color and which
leagues can clash all live in named constants at the top of `generate.py` —
read those for current values. Adding or removing a feed, league, color or
conflict pair is a code-only change and should not require an edit here; only
a change in *how* something works does.

## Files

- `generate.py` — fetches the ICS feeds, parses events, and writes `index.html`.
  No external dependencies (stdlib only). Re-run any time to refresh:
  ```
  python3 generate.py
  ```
- `index.html` — generated output. Do not edit by hand; edit `generate.py`
  and regenerate instead.
- `update.sh` — runs `generate.py`, then commits and pushes `index.html` if
  it changed meaningfully. Run any time to refresh and publish:
  ```
  ./update.sh
  ```
  Before diffing, it strips the `Generated <timestamp> from
  api.innebandy.se` line (via `strip_generated_line`) from both the newly
  generated `index.html` and the last committed version, so a re-run that
  only changes the timestamp is skipped — no commit/push. Otherwise it
  commits with message `update <YYYY-MM-DD>` and pushes to the remote. It
  commits only `index.html`; changes to `generate.py` or this file are left
  for you to commit.

## Data source

The ICS feeds are the `CALENDARS` list in `generate.py`, as
`(calendar_id, url, group_label)` tuples — one per IBIS team calendar, where
`calendar_id` is the team id that ends the URL and `group_label` is the
nickname shown on that feed's toggle on the page. Feeds are fetched fresh on
every run; there is no caching and no server component.

Events from every feed are merged into one list, and each event is stamped
with `event["calendar"]` (its calendar_id) so the page can group leagues by
which feed they came from.

**To add a team:** append a tuple to `CALENDARS`, then fetch the feed once and
read its `SUMMARY` lines to see which league strings it carries. Give each of
those leagues a `LEAGUE_COLORS` entry, add a `CONFLICT_PAIRS` entry for any
league whose games can clash with another team's, and add our squad's name to
`OUR_TEAM` if this feed spells it in a way not already listed. Nothing else is
wired per-feed — the group toggle, the filter rows and the month grouping all
derive from `CALENDARS` and the parsed events.

## How events are parsed

Each `VEVENT`'s `SUMMARY` has the form `Home - Away (League)`. `split_teams()`
pulls the trailing `(...)` off the end as the league name, then splits the
remainder on ` - ` into home/away. Team name suffixes like `(A)`/`(B)`/`(C)`
(squad letters) are part of the team name itself and are left alone.

"Our" team is matched with `is_our_team()` via an **exact**, case-insensitive
comparison against the `OUR_TEAM` set — the exact strings the feeds use for
our squads — not a substring match. This matters because opponents like
"Väsby AIK" and "Älvsjö AIK IBF" both contain the substring "AIK IBF"/"AIK"
and were previously highlighted incorrectly.

## League colors

Every known league gets a fixed, explicit color from `LEAGUE_COLORS`, keyed by
the exact league string. Explicit rather than assigned by sort order, so a
feed adding or dropping a league doesn't re-tint every other league on the
page.

The palette is organized by feed — blue/yellow/gray for one, a family of
greens (`COLOR_GREEN_1`–`COLOR_GREEN_4`) for another, orange for a third — so
one team's leagues read as related and distinct from another team's. That
correspondence drifts as IBIS renames leagues and moves them between feeds,
and re-tinting the whole page each time isn't worth it: treat feed ↔ color
family as the original intent, not an invariant to maintain.

Two leagues may deliberately share a color when they are the same team in the
same competition — a group stage and its `Slutspel` (playoff), for instance.

A league with no `LEAGUE_COLORS` entry falls back to `FALLBACK_PALETTE`, which
cycles the greens, so an unexpected league never breaks the page. Because the
greens are normally all claimed by explicit leagues, a fallback league shows up
as a visible duplicate of one of them — that is a prompt to give it its own
entry, not a working steady state.

Each event's card gets a tinted background + colored left border in its
league's color, with separate light/dark-mode values for both.

## Conflict badges

A circular `!` badge on the right edge of a card marks a fixture that clashes
with another team's fixture **on the same calendar day**. Its color says how
tight the clash is, measured as the idle time between the earlier game's end
and the later game's start (`gap_between()`, negative when the two overlap):

- **red** — less than `CONFLICT_GAP` of slack, or overlapping
- **black** — at least `CONFLICT_GAP` between the two games, so both are
  makeable

A card carrying several clashes is colored by its **tightest** one. Two cards
in one clash can therefore differ in color: each is scored against its own
worst partner, so a game comfortably clear of its only partner stays black
while that partner goes red over a third game.

The badge is a `<button>` wrapped in `.conflict-wrap`, followed by a
`.conflict-pop` panel listing every clashing fixture — league, home vs away,
time range and the gap to this card's own game — sorted by start time. The
league leads each block, bold and prefixed with a swatch in that league's card
color (the same `accent` the filter row uses); teams, time and gap sit under
it in muted secondary text, because the league is what identifies the clash. The
panel opens on hover (inside `@media (hover: hover)`, so touch screens don't
get a stuck hover state) or on keyboard focus via `:focus-within`, and a
click/tap pins it open by setting `.open` on the wrapper, which is how it
works on mobile. Clicking elsewhere or pressing Escape closes it; only one
panel is open at a time. The button keeps an `aria-label` with the same
one-line summary the old `title` tooltip had.

Which leagues can clash is an explicit whitelist, `CONFLICT_PAIRS` in
`generate.py` — the league combinations whose games actually compete for the
same person's time. A whitelist rather than flagging every same-day overlap,
because most pairs of leagues are simply unrelated and would drown the page in
badges. The list is expanded into the undirected lookup `CONFLICTS` so both
sides of a pair get flagged.

Any combination not listed never conflicts, and a league never conflicts with
itself. Badges are computed at generation time from all events, so they do
**not** react to the league/group checkboxes — a badge can point at a fixture
that is currently filtered out of view.

## Page behavior (client-side JS, no server)

- "Hide past matches" checkbox — sits on its own row above the group/league
  toggles.
- One group toggle per calendar feed, labeled with that feed's `group_label`
  from `CALENDARS`. They sit on their own row above the per-league toggles.
  Checking/unchecking one checks/unchecks every league belonging to that feed
  (matched via each league checkbox's `data-group` attribute, set from
  `event["calendar"]`). A group toggle shows an indeterminate (dash) state
  when only some of its leagues are checked.
- One checkbox per league (checked by default) — sits together on a single
  row, with a color swatch matching that league's card color.
- All filters combine via `applyFilters()`; month headings auto-hide when
  every event under them is filtered out. `syncGroupToggle()` keeps each
  group toggle's checked/indeterminate state in sync when an individual
  league checkbox changes.
- Events are grouped under month headings and sorted chronologically.
- Filter choices persist per browser via `localStorage` under the key
  `aik-ibf-schedule-filters-v1` — `saveFilters()` on every toggle,
  `restoreFilters()` on load, then a `syncGroupToggle()` pass and
  `applyFilters()`. `localStorage`, not cookies: the page is static on GitHub
  Pages, so nothing server-side would ever read a cookie. The key is
  namespaced because `<user>.github.io` serves every one of that user's Pages
  sites from a single origin, which shares one `localStorage`.
- What gets stored is the list of leagues switched **off** (`hiddenLeagues`),
  not the ones switched on, so a league that appears in the feed later shows
  up by default instead of being silently hidden by an older saved state. A
  stored slug that no longer exists is simply ignored. Group toggles are not
  stored — they are re-derived from the league checkboxes on load.
- Reads and writes are wrapped in try/catch, so private mode or storage-
  blocked browsers just lose persistence rather than breaking the page.

## Known constraints / things to watch if the feed changes

- The parser assumes datetimes are always `TZID=Europe/Stockholm` (or
  `VALUE=DATE`) and does not do timezone conversion — it just reads the
  local wall-clock time as-is, which is correct as long as the feed keeps
  using Stockholm time throughout.
- Every league lookup (`LEAGUE_COLORS`, `CONFLICT_PAIRS`) is an exact string
  match, not fuzzy. If IBIS renames a league, both go stale silently: the
  league drops to a fallback color and quietly stops producing conflict
  badges. Rename the keys to match rather than adding the new spelling
  alongside the old.
