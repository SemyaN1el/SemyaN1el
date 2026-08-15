import re
from pathlib import Path
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


PROFILE_URL = "https://steamcommunity.com/id/SemyaNiEl/"
OUTPUT_FILE = Path("assets/steam.svg")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract(pattern: str, text: str, field: str, default=None):
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        if default is not None:
            return default

        raise RuntimeError(
            f"Could not find '{field}' in Steam profile"
        )

    return match.group(1)


def fetch_steam_stats() -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1200,
            }
        )

        print("Opening Steam profile...")

        page.goto(
            PROFILE_URL,
            wait_until="domcontentloaded",
            timeout=120_000,
        )

        page.wait_for_function(
            """
            () => {
                const text = document.body.innerText
                    .replace(/\\s+/g, " ");

                return (
                    /Level\\s+\\d+/i.test(text) &&
                    /Games\\s+\\d+/i.test(text)
                );
            }
            """,
            timeout=90_000,
        )

        page.wait_for_timeout(2000)

        text = page.locator("body").inner_text()

        browser.close()

    text = normalize_text(text)

    print("Steam profile loaded.")

    level = int(
        extract(
            r"\bLevel\s+(\d+)",
            text,
            "level",
        )
    )

    games = int(
        extract(
            r"\bGames\s+(\d+)",
            text,
            "games",
        )
    )

    badges = int(
        extract(
            r"\bBadges\s+(\d+)",
            text,
            "badges",
            "0",
        )
    )

    perfect_games = int(
        extract(
            r"(\d+)\s+Perfect Games",
            text,
            "perfect games",
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
        r"([\d.]+)\s+hours past 2 weeks",
        text,
        "recent hours",
        "0",
    )

    # На Steam этот блок выглядит примерно:
    # Achievement Showcase 4,256 Achievements
    achievements_raw = extract(
        r"Achievement Showcase\s+([\d,]+)\s+Achievements",
        text,
        "achievements",
        "0",
    )

    achievements = int(
        achievements_raw.replace(",", "")
    )

    if "Currently Online" in text:
        status = "Online"
    elif "Currently In-Game" in text:
        status = "In Game"
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

    return f"""
<svg
    width="520"
    height="200"
    viewBox="0 0 520 200"
    xmlns="http://www.w3.org/2000/svg"
>
    <style>
        .title {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 21px;
            font-weight: 600;
            fill: #f0f6fc;
        }}

        .big {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 28px;
            font-weight: 700;
            fill: #f0f6fc;
        }}

        .label {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 13px;
            font-weight: 500;
            fill: #8b949e;
        }}

        .value {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 14px;
            font-weight: 600;
            fill: #f0f6fc;
        }}

        .footer {{
            font-family: -apple-system, BlinkMacSystemFont,
                         "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 10px;
            fill: #484f58;
        }}
    </style>

    <!-- Background -->

    <rect
        x="0.5"
        y="0.5"
        width="519"
        height="199"
        rx="8"
        fill="#000000"
        stroke="#30363d"
    />

    <!-- Header -->

    <text
        x="24"
        y="35"
        class="title"
    >
        Steam Stats
    </text>

    <text
        x="496"
        y="34"
        text-anchor="end"
        class="label"
    >
        {status}
    </text>

    <!-- Level -->

    <text
        x="24"
        y="82"
        class="big"
    >
        {level}
    </text>

    <text
        x="24"
        y="102"
        class="label"
    >
        Level
    </text>

    <!-- Games -->

    <text
        x="135"
        y="82"
        class="big"
    >
        {games}
    </text>

    <text
        x="135"
        y="102"
        class="label"
    >
        Games
    </text>

    <!-- Achievements -->

    <text
        x="275"
        y="82"
        class="big"
    >
        {achievements:,}
    </text>

    <text
        x="275"
        y="102"
        class="label"
    >
        Achievements
    </text>

    <!-- Stats row -->

    <circle
        cx="27"
        cy="136"
        r="4"
        fill="#66c0f4"
    />

    <text
        x="39"
        y="141"
        class="label"
    >
        Badges
    </text>

    <text
        x="92"
        y="141"
        class="value"
    >
        {badges}
    </text>


    <circle
        cx="145"
        cy="136"
        r="4"
        fill="#66c0f4"
    />

    <text
        x="157"
        y="141"
        class="label"
    >
        Perfect
    </text>

    <text
        x="211"
        y="141"
        class="value"
    >
        {perfect_games}
    </text>


    <circle
        cx="266"
        cy="136"
        r="4"
        fill="#66c0f4"
    />

    <text
        x="278"
        y="141"
        class="label"
    >
        Completion
    </text>

    <text
        x="351"
        y="141"
        class="value"
    >
        {completion_rate}%
    </text>


    <circle
        cx="404"
        cy="136"
        r="4"
        fill="#66c0f4"
    />

    <text
        x="416"
        y="141"
        class="label"
    >
        2 weeks
    </text>

    <text
        x="467"
        y="141"
        class="value"
    >
        {recent_hours}h
    </text>

    <!-- Footer -->

    <text
        x="24"
        y="179"
        class="footer"
    >
        Updated automatically
    </text>

    <text
        x="496"
        y="179"
        text-anchor="end"
        class="footer"
    >
        {updated_at}
    </text>
</svg>
""".strip()


def main():
    print("=" * 50)
    print("Updating Steam statistics")
    print("=" * 50)

    stats = fetch_steam_stats()

    print()
    print("Steam stats:")
    print(f"  Level:       {stats['level']}")
    print(f"  Games:       {stats['games']}")
    print(f"  Badges:      {stats['badges']}")
    print(f"  Perfect:     {stats['perfect_games']}")
    print(f"  Achievements:{stats['achievements']}")
    print(f"  Completion:  {stats['completion_rate']}%")
    print(f"  Last 2 weeks:{stats['recent_hours']}h")
    print(f"  Status:      {stats['status']}")
    print()

    svg = generate_svg(stats)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        svg,
        encoding="utf-8",
    )

    print(f"SVG saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
