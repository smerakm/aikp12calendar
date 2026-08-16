# AIK Calendar Subs

Static HTML match-schedule page for AIK IBF (floorball), generated from a
public ICS calendar feed published by the Swedish Floorball Federation (IBIS).

## Files

- `generate.py` — fetches the ICS feed, parses events, and writes `index.html`.
  No external dependencies (stdlib only). Re-run any time to refresh:
  ```
  python3 generate.py
  ```
- `index.html` — generated output. Do not edit by hand; edit `generate.py`
  and regenerate instead.

## Data source

Two ICS feeds, both defined in the `CALENDARS` list in `generate.py`
(`(calendar_id, url, group_label)` tuples), fetched fresh on every run —
there is no caching or server component:

- `https://api.innebandy.se/v2/api/calendars/team/117199` — team 117199
  ("AIK p12/13", boys 2012/2013 squads)
- `https://api.innebandy.se/v2/api/calendars/team/126811` — team 126811
  ("AIK Utveckling", the "AIK IBF (B)" and "AIK IBF Utveckling" squads)

Events from both feeds are merged into one list; each event is stamped with
`event["calendar"]` (the calendar_id) so the page can group leagues by
which feed they came from.

## How events are parsed

Each `VEVENT`'s `SUMMARY` has the form `Home - Away (League)`. `split_teams()`
pulls the trailing `(...)` off the end as the league name, then splits the
remainder on ` - ` into home/away. Team name suffixes like `(A)`/`(B)`/`(C)`
(squad letters) are part of the team name itself and are left alone.

"Our" team is matched with `is_our_team()` via an **exact**, case-insensitive
comparison against the `OUR_TEAM` set — `{"AIK IBF", "AIK IBF (B)", "AIK IBF
Utveckling"}` — not a substring match. This matters because opponents like
"Väsby AIK" and "Älvsjö AIK IBF" both contain the substring "AIK IBF"/"AIK"
and were previously highlighted incorrectly.

## League colors

Known leagues get fixed, explicit colors (not assigned by sort order),
defined in `LEAGUE_COLORS` in `generate.py`:

- `Bäst i Stan Pojkar 14 - Grupp B` — blue
- `Pantamera Pojkar 2012 B Norra` — yellow
- `Pantamera Pojkar 2013 C Norra` — gray
- `Pantamera Pojkar 2010 B/C` — green (shade 1)
- `Bäst i Stan Pojkar 15 - Grupp C` — green (shade 2)
- `Pantamera Herrjuniorer Division 3 Norra` — green (shade 3)
- `Träningsmatcher Herr` — green (shade 4)

The four leagues from the 126811 feed all use distinct shades of green
(`COLOR_GREEN_1`–`COLOR_GREEN_4`) so they read as a family, distinct from
the 117199 feed's blue/yellow/gray. Any future/unknown league falls back to
`FALLBACK_PALETTE` (cycles through the same four greens) so the page
doesn't break if a feed adds a new group. Each event's card gets a tinted
background + colored left border in its league's color, with separate
light/dark-mode values for both.

## Page behavior (client-side JS, no server)

- "Hide past matches" checkbox — sits on its own row above the group/league
  toggles.
- Two group toggles ("AIK p12/13", "AIK Utveckling") — one per calendar
  feed, sit on their own row above the per-league toggles. Checking/
  unchecking one checks/unchecks every league belonging to that feed
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

## Known constraints / things to watch if the feed changes

- The parser assumes datetimes are always `TZID=Europe/Stockholm` (or
  `VALUE=DATE`) and does not do timezone conversion — it just reads the
  local wall-clock time as-is, which is correct as long as the feed keeps
  using Stockholm time throughout.
- If IBIS renames a league string exactly, update `LEAGUE_COLORS` to match —
  the lookup is an exact string match, not fuzzy.
