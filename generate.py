#!/usr/bin/env python3
"""Fetch the AIK IBF team calendar (ICS) and render it as a static HTML page.

Usage: python3 generate.py
Re-run any time to refresh index.html with the latest fixtures.
"""

import html
import re
import urllib.request
from datetime import datetime

CALENDARS = [
    ("117199", "https://api.innebandy.se/v2/api/calendars/team/117199", "AIK p12/13"),
    ("126811", "https://api.innebandy.se/v2/api/calendars/team/126811", "AIK Utveckling"),
]
OUTPUT_FILE = "index.html"
OUR_TEAM = {"AIK IBF", "AIK IBF (B)", "AIK IBF Utveckling"}

COLOR_YELLOW = {"bg": "#fff3c4", "bg_dark": "rgba(240,196,25,0.16)", "accent": "#8a6d00", "accent_dark": "#f0c419"}
COLOR_GRAY = {"bg": "#e2e4e8", "bg_dark": "rgba(255,255,255,0.07)", "accent": "#374151", "accent_dark": "#d1d5db"}
COLOR_BLUE = {"bg": "#dbe9fe", "bg_dark": "rgba(37,99,235,0.18)", "accent": "#1d4ed8", "accent_dark": "#60a5fa"}
COLOR_GREEN_1 = {"bg": "#dcf7e3", "bg_dark": "rgba(16,185,129,0.16)", "accent": "#047857", "accent_dark": "#34d399"}
COLOR_GREEN_2 = {"bg": "#e6f9d5", "bg_dark": "rgba(101,163,13,0.18)", "accent": "#3f6212", "accent_dark": "#a3e635"}
COLOR_GREEN_3 = {"bg": "#d3f5ec", "bg_dark": "rgba(13,148,136,0.18)", "accent": "#0f766e", "accent_dark": "#5eead4"}
COLOR_GREEN_4 = {"bg": "#e5f3d8", "bg_dark": "rgba(77,124,15,0.18)", "accent": "#4d7c0f", "accent_dark": "#bef264"}

# Explicit color per known league. Leagues not listed here fall back to FALLBACK_PALETTE, in order.
LEAGUE_COLORS = {
    "Bäst i Stan Pojkar 14 - Grupp B": COLOR_BLUE,
    "Pantamera Pojkar 2012 B Norra": COLOR_YELLOW,
    "Pantamera Pojkar 2013 C Norra": COLOR_GRAY,
    "Pantamera Pojkar 2010 B/C": COLOR_GREEN_1,
    "Bäst i Stan Pojkar 15 - Grupp C": COLOR_GREEN_2,
    "Pantamera Herrjuniorer Division 3 Norra": COLOR_GREEN_3,
    "Träningsmatcher Herr": COLOR_GREEN_4,
}
FALLBACK_PALETTE = [COLOR_GREEN_1, COLOR_GREEN_2, COLOR_GREEN_3, COLOR_GREEN_4]


def slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def fetch_ics(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def unfold_lines(raw: str) -> list[str]:
    lines = raw.replace("\r\n", "\n").split("\n")
    unfolded = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def parse_dt(value: str) -> datetime:
    value = value.strip()
    fmt = "%Y%m%dT%H%M%S" if "T" in value else "%Y%m%d"
    return datetime.strptime(value, fmt)


def parse_events(lines: list[str]) -> list[dict]:
    events = []
    current = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue
        key, _, value = line.partition(":")
        name = key.split(";")[0]
        if name == "DTSTART":
            current["start"] = parse_dt(value)
        elif name == "DTEND":
            current["end"] = parse_dt(value)
        elif name == "SUMMARY":
            current["summary"] = value.replace("\\,", ",").replace("\\;", ";")
        elif name == "LOCATION":
            current["location"] = value.replace("\\,", ",").replace("\\;", ";")
        elif name == "STATUS":
            current["status"] = value
        elif name == "UID":
            current["uid"] = value
    return events


def split_teams(summary: str) -> tuple[str, str, str]:
    """Split 'Home - Away (Group)' into (home, away, group)."""
    group = ""
    m = re.match(r"^(.*)\(([^()]*)\)\s*$", summary)
    body = summary
    if m:
        body, group = m.group(1).strip(), m.group(2).strip()
    if " - " in body:
        home, away = body.split(" - ", 1)
    else:
        home, away = body, ""
    return home.strip(), away.strip(), group


MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def is_our_team(name: str) -> bool:
    return name.strip().casefold() in {t.casefold() for t in OUR_TEAM}


def render_html(events: list[dict]) -> str:
    events = sorted(events, key=lambda e: e["start"])
    now = datetime.now()

    leagues = sorted({split_teams(e.get("summary", ""))[2] for e in events} - {""})
    league_style = {}
    fallback_i = 0
    for name in leagues:
        color = LEAGUE_COLORS.get(name)
        if color is None:
            color = FALLBACK_PALETTE[fallback_i % len(FALLBACK_PALETTE)]
            fallback_i += 1
        league_style[name] = {**color, "slug": slugify(name)}

    league_calendar = {}
    for e in events:
        group = split_teams(e.get("summary", ""))[2]
        if group and group not in league_calendar:
            league_calendar[group] = e.get("calendar", "")

    rows = []
    current_month = None
    for e in events:
        start = e["start"]
        end = e.get("end")
        home, away, group = split_teams(e.get("summary", ""))
        is_home = is_our_team(home)
        is_away = is_our_team(away)
        month_key = (start.year, start.month)
        if month_key != current_month:
            current_month = month_key
            rows.append(
                f'<h2 class="month">{MONTH_NAMES[start.month - 1]} {start.year}</h2>'
            )

        past_cls = " past" if end and end < now else ""
        venue_cls = "home" if is_home else "away" if is_away else ""
        league_slug = league_style.get(group, {}).get("slug", "")
        time_str = start.strftime("%H:%M")
        if end:
            time_str += f"–{end.strftime('%H:%M')}"

        rows.append(f'''
        <div class="event league-{league_slug}{past_cls}" data-league="{league_slug}">
          <div class="date">
            <span class="weekday">{WEEKDAY_NAMES[start.weekday()]}</span>
            <span class="day">{start.day}</span>
          </div>
          <div class="details">
            <div class="teams">
              <span class="team {"us" if is_home else ""}">{html.escape(home)}</span>
              <span class="sep">vs</span>
              <span class="team {"us" if is_away else ""}">{html.escape(away)}</span>
            </div>
            <div class="meta">
              <span class="time">{time_str}</span>
              <span class="dot">&middot;</span>
              <span class="venue {venue_cls}">{"Home" if is_home else "Away" if is_away else ""}</span>
              <span class="dot">&middot;</span>
              <span class="location">{html.escape(e.get("location", ""))}</span>
            </div>
            {f'<div class="group">{html.escape(group)}</div>' if group else ""}
          </div>
        </div>''')

    events_html = "\n".join(rows) if rows else '<p class="empty">No events found.</p>'
    generated_at = now.strftime("%Y-%m-%d %H:%M")

    league_css = "\n".join(f'''
  .event.league-{s["slug"]} {{ background: {s["bg"]}; border-left: 4px solid {s["accent"]}; }}
  @media (prefers-color-scheme: dark) {{
    .event.league-{s["slug"]} {{ background: {s["bg_dark"]}; border-left-color: {s["accent_dark"]}; }}
  }}''' for s in league_style.values())

    league_toggles = "\n".join(f'''
      <label class="toggle league-toggle-label">
        <input type="checkbox" class="league-toggle" data-league="{s["slug"]}" data-group="{league_calendar.get(name, "")}" checked>
        <span class="swatch" style="background:{s["accent"]}"></span>
        {html.escape(name)}
      </label>''' for name, s in league_style.items())

    group_toggles = "\n".join(f'''
      <label class="toggle group-toggle-label">
        <input type="checkbox" class="group-toggle" data-group="{cal_id}" checked>
        {html.escape(cal_label)}
      </label>''' for cal_id, _url, cal_label in CALENDARS)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIK IBF – Match Schedule</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #ffffff;
    --fg: #1a1a1a;
    --muted: #6b7280;
    --border: #e5e7eb;
    --card: #f9fafb;
    --accent: #d6001c;
    --accent-bg: #fdeaec;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #14161a;
      --fg: #f2f2f2;
      --muted: #9ca3af;
      --border: #2a2d33;
      --card: #1c1f24;
      --accent: #ff5468;
      --accent-bg: #3a1620;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 2rem 1rem 4rem;
    background: var(--bg);
    color: var(--fg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  header {{ margin-bottom: 2rem; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
  .sub {{ color: var(--muted); font-size: 0.9rem; }}
  .month {{
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin: 2rem 0 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border);
  }}
  .month:first-of-type {{ margin-top: 0; }}
  .event {{
    display: flex;
    gap: 1rem;
    padding: 0.9rem 0.9rem;
    margin-bottom: 0.5rem;
    border-radius: 8px;
  }}
  .event.past {{ opacity: 0.45; }}
  {league_css}
  .date {{
    flex: 0 0 3rem;
    text-align: center;
  }}
  .date .weekday {{
    display: block;
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .date .day {{
    display: block;
    font-size: 1.4rem;
    font-weight: 600;
  }}
  .details {{ flex: 1; min-width: 0; }}
  .teams {{ font-size: 1rem; font-weight: 500; }}
  .teams .team.us {{ color: var(--accent); font-weight: 700; }}
  .teams .sep {{ color: var(--muted); margin: 0 0.4em; font-weight: 400; font-size: 0.85em; }}
  .meta {{
    margin-top: 0.2rem;
    font-size: 0.82rem;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 0.4em;
    flex-wrap: wrap;
  }}
  .venue.home {{
    background: var(--accent-bg);
    color: var(--accent);
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    font-weight: 600;
  }}
  .venue.away {{ font-weight: 600; }}
  .group {{ margin-top: 0.2rem; font-size: 0.78rem; color: var(--muted); }}
  .empty {{ color: var(--muted); }}
  footer {{
    max-width: 720px;
    margin: 2rem auto 0;
    color: var(--muted);
    font-size: 0.75rem;
    text-align: center;
  }}
  .filters {{
    margin-top: 0.75rem;
  }}
  .filters .past-row {{
    margin-bottom: 0.5rem;
  }}
  .filters .group-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }}
  .filters .group-toggle-label {{
    font-weight: 600;
  }}
  .filters .league-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
  }}
  label.toggle {{
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
    font-size: 0.85rem;
    color: var(--muted);
    cursor: pointer;
  }}
  .swatch {{
    display: inline-block;
    width: 0.7em;
    height: 0.7em;
    border-radius: 3px;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>AIK IBF – Match Schedule</h1>
      <div class="sub">Generated {generated_at} from api.innebandy.se</div>
      <div class="filters">
        <div class="past-row">
          <label class="toggle">
            <input type="checkbox" id="hidePast">
            Hide past matches
          </label>
        </div>
        <div class="group-row">
          {group_toggles}
        </div>
        <div class="league-row">
          {league_toggles}
        </div>
      </div>
    </header>
    <div id="events">
      {events_html}
    </div>
  </div>
  <footer>Data source: Svenska Innebandyförbundet (IBIS) calendar feed</footer>
  <script>
    function applyFilters() {{
      const hidePast = document.getElementById('hidePast').checked;
      const activeLeagues = new Set(
        [...document.querySelectorAll('.league-toggle:checked')].map(cb => cb.dataset.league)
      );
      document.querySelectorAll('.event').forEach(el => {{
        const show = (!hidePast || !el.classList.contains('past')) && activeLeagues.has(el.dataset.league);
        el.style.display = show ? '' : 'none';
      }});
      document.querySelectorAll('.month').forEach(h => {{
        let sib = h.nextElementSibling;
        let anyVisible = false;
        while (sib && !sib.classList.contains('month')) {{
          if (sib.classList.contains('event') && sib.style.display !== 'none') anyVisible = true;
          sib = sib.nextElementSibling;
        }}
        h.style.display = anyVisible ? '' : 'none';
      }});
    }}
    function syncGroupToggle(groupCb) {{
      const children = [...document.querySelectorAll('.league-toggle')].filter(cb => cb.dataset.group === groupCb.dataset.group);
      const checkedCount = children.filter(cb => cb.checked).length;
      groupCb.checked = checkedCount === children.length;
      groupCb.indeterminate = checkedCount > 0 && checkedCount < children.length;
    }}
    document.getElementById('hidePast').addEventListener('change', applyFilters);
    document.querySelectorAll('.league-toggle').forEach(cb => cb.addEventListener('change', () => {{
      document.querySelectorAll('.group-toggle').forEach(syncGroupToggle);
      applyFilters();
    }}));
    document.querySelectorAll('.group-toggle').forEach(groupCb => groupCb.addEventListener('change', () => {{
      document.querySelectorAll('.league-toggle').forEach(cb => {{
        if (cb.dataset.group === groupCb.dataset.group) cb.checked = groupCb.checked;
      }});
      groupCb.indeterminate = false;
      applyFilters();
    }}));
  </script>
</body>
</html>
"""


def main():
    events = []
    for cal_id, url, _label in CALENDARS:
        raw = fetch_ics(url)
        lines = unfold_lines(raw)
        cal_events = parse_events(lines)
        for e in cal_events:
            e["calendar"] = cal_id
        events.extend(cal_events)
    out = render_html(events)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {len(events)} events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
