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

`https://api.innebandy.se/v2/api/calendars/team/117199` — ICS feed for team
117199 (AIK IBF, boys 2012/2013 squads). Fetched fresh on every run of
`generate.py`; there is no caching or server component.

## How events are parsed

Each `VEVENT`'s `SUMMARY` has the form `Home - Away (League)`. `split_teams()`
pulls the trailing `(...)` off the end as the league name, then splits the
remainder on ` - ` into home/away. Team name suffixes like `(A)`/`(B)`/`(C)`
(squad letters) are part of the team name itself and are left alone.

"Our" team is matched with `is_our_team()` via an **exact**, case-insensitive
comparison against `OUR_TEAM = "AIK IBF"` — not a substring match. This
matters because opponents like "Väsby AIK" and "Älvsjö AIK IBF" both contain
the substring "AIK IBF"/"AIK" and were previously highlighted incorrectly.

## League colors

Three known leagues get fixed, explicit colors (not assigned by sort order),
defined in `LEAGUE_COLORS` in `generate.py`:

- `Bäst i Stan Pojkar 14 - Grupp B` — blue
- `Pantamera Pojkar 2012 B Norra` — yellow
- `Pantamera Pojkar 2013 C Norra` — gray

Any future/unknown league falls back to `FALLBACK_PALETTE` (currently green,
then purple) so the page doesn't break if the feed adds a new group. Each
event's card gets a tinted background + colored left border in its league's
color, with separate light/dark-mode values for both.

## Page behavior (client-side JS, no server)

- "Hide past matches" checkbox — sits on its own row above the league toggles.
- One checkbox per league (checked by default) — sits together on a single
  row, with a color swatch matching that league's card color.
- Both filters combine via `applyFilters()`; month headings auto-hide when
  every event under them is filtered out.
- Events are grouped under month headings and sorted chronologically.

## Known constraints / things to watch if the feed changes

- The parser assumes datetimes are always `TZID=Europe/Stockholm` (or
  `VALUE=DATE`) and does not do timezone conversion — it just reads the
  local wall-clock time as-is, which is correct as long as the feed keeps
  using Stockholm time throughout.
- If IBIS renames a league string exactly, update `LEAGUE_COLORS` to match —
  the lookup is an exact string match, not fuzzy.
