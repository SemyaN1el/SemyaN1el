
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


PROFILE_URL = "https://steamcommunity.com/id/SemyaNiEl/?l=english"
OUTPUT_FILE = Path("assets/steam.svg")

# Steam renamed "Perfect Games" to "Completed Games".
COMPLETED_GAMES_PATTERNS = (
    r"\b([\d,]+)\s+Completed\s+Games\b",
    r"\b([\d,]+)\s+Perfect\s+Games\b",
    r"\bCompleted\s+Games\s*:?\s*([\d,]+)\b",
    r"\bPerfect\s+Games\s*:?\s*([\d,]+)\b",
)


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
    return int(raw.replace(",", ""))


def extract_completed_games(text: str) -> int:
    """
    Extract completed games from Steam.
    Never silently replace a missing counter with zero.
    """
    for pattern in COMPLETED_GAMES_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            return parse_number(match.group(1))

    raise RuntimeError(
        "Could not find 'Completed Games' (formerly 'Perfect Games') "
        "on the Steam profile. Check that the public profile has a "
        "Completionist Showcase with the Completed Games counter. "
        "The SVG was NOT overwritten."
    )


def fetch_steam_stats() -> dict:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        try:
            page = browser.new_page(
                viewport={"width": 1440, "height": 1200},
                locale="en-US",
            )

            print(f"Opening Steam profile: {PROFILE_URL}")

            response = page.goto(
                PROFILE_URL,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

            if response and response.status >= 400:
                raise RuntimeError(
                    f"Steam returned HTTP {response.status}"
                )

            page.wait_for_function(
                r"""() => {
                    const text = document.body.innerText.replace(/\s+/g, ' ');
                    return /\bLevel\s+\d+/i.test(text)
                        && /\bGames\s+[\d,]+/i.test(text);
                }""",
                timeout=90_000,
            )

            # Wait for the achievement showcase to load.
            try:
                page.wait_for_function(
                    r"""() => {
                        const text = document.body.innerText.replace(/\s+/g, ' ');
                        return /\b[\d,]+\s+(?:Completed|Perfect)\s+Games\b/i.test(text)
                            || /\b(?:Completed|Perfect)\s+Games\s*:?\s*[\d,]+\b/i.test(text);
                    }""",
                    timeout=20_000,
                )
            except PlaywrightTimeoutError:
                print(
                    "WARNING: Completed Games did not appear "
                    "within 20 seconds"
                )

            text = normalize_text(
                page.locator("body").inner_text()
            )

        finally:
            browser.close()

    print("Steam profile loaded.")

    level = parse_number(
        extract(
            r"\bLevel\s+([\d,]+)",
            text,
            "level",
        )
    )

    games = parse_number(
        extract(
            r"\bGames\s+([\d,]+)",
            text,
            "games",
        )
    )

    perfect_games = extract_completed_games(text)

    badges = parse_number(
        extract(
            r"\bBadges\s+([\d,]+)",
            text,
            "badges",
            "0",
        )
    )

    completion_rate = int(
        extract(
            r"(\d+)%\s+Avg\.?\s+Game Completion Rate",
            text,
            "completion rate",
            "0",
        )
    )

    recent_hours = extract(
        r"([\d,.]+)\s+hours past 2 weeks",
        text,
        "recent hours",
        "0",
    )

    achievements = parse_number(
        extract(
            r"Achievement Showcase\s+([\d,]+)\s+Achievements",
            text,
            "achievements",
            "0",
        )
    )

    if "Currently In-Game" in text:
        status = "In Game"
    elif "Currently Online" in text:
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

    updated_at = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

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

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        generate_svg(stats),
        encoding="utf-8",
    )

    print(f"SVG saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
