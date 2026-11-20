import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


# Force Steam's English interface so that text labels are predictable.
PROFILE_URL = "https://steamcommunity.com/id/SemyaNiEl/?l=english"
OUTPUT_FILE = Path("assets/steam.svg")

# Public profile and Games tab use different labels/ordering.
# Source: Steam's "Completed" tab (formerly "Perfect Games").
GAMES_URL = "https://steamcommunity.com/id/SemyaNiEl/games/?tab=perfect&l=english"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract(pattern: str, text: str, field: str, default=None) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    if default is not None:
        print(f"WARNING: Steam field '{field}' not found; using {default!r}")
        return default
    raise RuntimeError(f"Could not find '{field}' in Steam profile")


def parse_number(raw: str) -> int:
    return int(re.sub(r"[^0-9]", "", raw))


def extract_completed_games(text: str, *, from_games_tab: bool = False):
    """Return a number only if Steam explicitly prints the relevant counter."""
    text = normalize_text(text)
    patterns = [
        r"\b([\d,]+)\s+(?:Completed|Perfect)\s+Games\b",
        r"\b(?:Completed|Perfect)\s+Games\s*[:(]?\s*([\d,]+)\b",
        r"\b([\d,]+)\s+Games\s+Completed\b",
        r"\bGames\s+Completed\s*[:(]?\s*([\d,]+)\b",
    ]
    if from_games_tab:
        # Current/legacy Steam games-tab labels may be simply "Completed (12)".
        patterns.extend([
            r"\bCompleted\s*\(\s*([\d,]+)\s*\)",
            r"\bPerfect\s*\(\s*([\d,]+)\s*\)",
        ])

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_number(match.group(1))
    return None


def games_tab_count(page):
    """Cross-check against the public Games > Completed tab, not a showcase."""
    print(f"Checking Steam completed-games tab: {GAMES_URL}")
    try:
        response = page.goto(GAMES_URL, wait_until="domcontentloaded", timeout=60_000)
        if response and response.status >= 400:
            print(f"WARNING: Games tab returned HTTP {response.status}")
            return None
        page.wait_for_timeout(3000)

        # The navigation link is more specific than the full text on the page.
        # Restrict the bare 'Completed (N)' expression to that navigation area.
        tabs = page.locator(
            'a[href*="tab=perfect"], a[href*="tab=completed"], '
            '[data-tab="perfect"], [data-tab="completed"]'
        )
        for index in range(min(tabs.count(), 12)):
            tab = tabs.nth(index)
            snippets = [tab.inner_text(timeout=3000), tab.get_attribute("title") or ""]
            for snippet in snippets:
                number = extract_completed_games(snippet, from_games_tab=True)
                if number is not None:
                    print(f"Games tab navigation shows {number} completed games")
                    return number

        body_text = page.locator("body").inner_text(timeout=30_000)
        number = extract_completed_games(body_text, from_games_tab=True)
        if number is not None:
            print(f"Games tab body shows {number} completed games")
            return number
        print("WARNING: No completed-games counter in Games tab.")
        print("Games tab text sample:", normalize_text(body_text)[:1200])
        return None
    except Exception as exc:
        print(f"WARNING: Games tab could not be parsed: {exc}")
        return None


def fetch_steam_stats() -> dict:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                viewport={"width": 1440, "height": 1200}, locale="en-US"
            )
            print(f"Opening Steam profile: {PROFILE_URL}")
            response = page.goto(
                PROFILE_URL, wait_until="domcontentloaded", timeout=120_000
            )
            if response and response.status >= 400:
                raise RuntimeError(f"Steam profile returned HTTP {response.status}")
            page.wait_for_function(
                r"""() => {
                    const text = document.body.innerText.replace(/\s+/g, ' ');
                    return /\bLevel\s+[\d,]+/i.test(text)
                        && /\bGames\s+[\d,]+/i.test(text);
                }""",
                timeout=90_000,
            )
            page.wait_for_timeout(2000)
            profile_text = normalize_text(page.locator("body").inner_text())
            profile_count = extract_completed_games(profile_text)
            print(f"Completed games (profile showcase): {profile_count}")

            # Even when the showcase is absent or displays zero, the Games tab
            # may expose the correct counter.
            tab_count = games_tab_count(page) if not profile_count else None
        finally:
            browser.close()

    print("Steam profile loaded.")
    level = parse_number(extract(r"\bLevel\s+([\d,]+)", profile_text, "level"))
    games = parse_number(extract(r"\bGames\s+([\d,]+)", profile_text, "games"))

    perfect_games = profile_count if profile_count else tab_count
    if not perfect_games:
        print("Profile snippets around completed/perfect counters:")
        for match in list(re.finditer(r"completed|perfect", profile_text, re.I))[:8]:
            print(repr(profile_text[max(0, match.start()-65):match.end()+65]))
        raise RuntimeError(
            "No positive completed-games counter was found on the Steam profile "
            "or its Games tab. Refusing to overwrite assets/steam.svg with zero. "
            "Check the GitHub Actions log for the Steam page text sample."
        )

    badges = parse_number(extract(r"\bBadges\s+([\d,]+)", profile_text, "badges", "0"))
    completion_rate = int(extract(
        r"(\d+)%\s+Avg\.?\s+Game Completion Rate", profile_text,
        "completion rate", "0"
    ))
    recent_hours = extract(
        r"([\d,.]+)\s+hours past 2 weeks", profile_text,
        "recent hours", "0"
    )
    achievements = parse_number(extract(
        r"Achievement Showcase\s+([\d,]+)\s+Achievements", profile_text,
        "achievements", "0"
    ))

    if "Currently In-Game" in profile_text:
        status = "In Game"
    elif "Currently Online" in profile_text:
        status = "Online"
    else:
        status = "Offline"

    return {
        "level": level,
        "games": games,
        "badges": badges,
        "perfect_games": perfect_games,
        "completion_rate": completion_rate,
        "recent_hours": recent_hours,
        "achievements": achievements,
        "status": status,
    }


def generate_svg(stats: dict) -> str:
    level = stats["level"]
    games = stats["games"]
    badges = stats["badges"]
    perfect_games = stats["perfect_games"]
    completion_rate = stats["completion_rate"]
    recent_hours = stats["recent_hours"]
    achievements = stats["achievements"]
    status = stats["status"]
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Original 520 x 200 card layout preserved.
    return f"""<svg width="520" height="200" viewBox="0 0 520 200"
    xmlns="http://www.w3.org/2000/svg">
    <style>
        .title {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 21px; font-weight: 600; fill: #f0f6fc;
        }}
        .big {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 28px; font-weight: 700; fill: #f0f6fc;
        }}
        .label {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 13px; font-weight: 500; fill: #8b949e;
        }}
        .value {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 14px; font-weight: 600; fill: #f0f6fc;
        }}
        .footer {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 10px; fill: #484f58;
        }}
    </style>

    <!-- Background -->
    <rect x="0.5" y="0.5" width="519" height="199" rx="8"
          fill="#000000" stroke="#30363d"/>

    <!-- Header -->
    <text x="24" y="35" class="title">Steam Stats</text>
    <text x="496" y="34" text-anchor="end" class="label">{status}</text>

    <!-- Main counters -->
    <text x="24" y="82" class="big">{level}</text>
    <text x="24" y="102" class="label">Level</text>

    <text x="135" y="82" class="big">{games}</text>
    <text x="135" y="102" class="label">Games</text>

    <text x="275" y="82" class="big">{achievements:,}</text>
    <text x="275" y="102" class="label">Achievements</text>

    <!-- Detail counters -->
    <circle cx="27" cy="136" r="4" fill="#66c0f4"/>
    <text x="39" y="141" class="label">Badges</text>
    <text x="92" y="141" class="value">{badges}</text>

    <circle cx="145" cy="136" r="4" fill="#66c0f4"/>
    <text x="157" y="141" class="label">Perfect</text>
    <text x="211" y="141" class="value">{perfect_games}</text>

    <circle cx="266" cy="136" r="4" fill="#66c0f4"/>
    <text x="278" y="141" class="label">Completion</text>
    <text x="351" y="141" class="value">{completion_rate}%</text>

    <circle cx="404" cy="136" r="4" fill="#66c0f4"/>
    <text x="416" y="141" class="label">2 weeks</text>
    <text x="467" y="141" class="value">{recent_hours}h</text>

    <!-- Footer -->
    <text x="24" y="179" class="footer">Updated automatically</text>
    <text x="496" y="179" text-anchor="end" class="footer">{updated_at}</text>
</svg>"""


def main() -> None:
    print("=" * 50)
    print("Updating Steam statistics")
    print("=" * 50)

    stats = fetch_steam_stats()
    print("\nSteam stats:")
    print(f"  Level:        {stats['level']}")
    print(f"  Games:        {stats['games']}")
    print(f"  Badges:       {stats['badges']}")
    print(f"  Completed:    {stats['perfect_games']}")
    print(f"  Achievements: {stats['achievements']}")
    print(f"  Completion:   {stats['completion_rate']}%")
    print(f"  Last 2 weeks: {stats['recent_hours']}h")
    print(f"  Status:       {stats['status']}\n")

    # Render only after all required stats have been parsed successfully.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(generate_svg(stats), encoding="utf-8")
    print(f"SVG saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
