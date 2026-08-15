import re
from pathlib import Path
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


PROFILE_URL = (
    "https://www.deep-ml.com/profile/"
    "1sQ5Fm3ANdfzi3dJHL8MprBzCtu1"
)

OUTPUT = Path("assets/deepml.svg")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract(pattern: str, text: str, name: str) -> int:
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        raise RuntimeError(
            f"Could not find {name} in Deep-ML page"
        )

    return int(match.group(1))


def fetch_stats():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1400,
                "height": 1200,
            }
        )

        print("Opening Deep-ML profile...")

        page.goto(
            PROFILE_URL,
            wait_until="domcontentloaded",
            timeout=120_000,
        )

        # Ждём, пока JavaScript отрисует статистику.
        page.wait_for_function(
            """
            () => {
                const text =
                    document.body.innerText
                        .replace(/\\s+/g, " ");

                return (
                    /Solved\\s+\\d+/i.test(text) &&
                    /Easy\\s+\\d+/i.test(text) &&
                    /Medium\\s+\\d+/i.test(text) &&
                    /Hard\\s+\\d+/i.test(text)
                );
            }
            """,
            timeout=90_000,
        )

        text = page.locator("body").inner_text()

        browser.close()

    text = normalize(text)

    print("Deep-ML page loaded.")

    easy = extract(
    r"\bEasy\s+(\d+)",
    text,
    "easy"
    )
    
    medium = extract(
        r"\bMedium\s+(\d+)",
        text,
        "medium"
    )
    
    hard = extract(
        r"\bHard\s+(\d+)",
        text,
        "hard"
    )

# Надёжнее считать total из difficulty
solved = easy + medium + hard

    level = extract(
        r"\b(?:LV|Level)\.?\s*(\d+)",
        text,
        "level"
    )

    rank = extract(
        r"\bRank\s*#?\s*(\d+)",
        text,
        "rank"
    )

    return {
        "solved": solved,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "level": level,
        "rank": rank,
    }


def generate_svg(stats):
    solved = stats["solved"]
    easy = stats["easy"]
    medium = stats["medium"]
    hard = stats["hard"]
    level = stats["level"]
    rank = stats["rank"]

    total = max(solved, 1)

    easy_percent = round(easy / total * 100)
    medium_percent = round(medium / total * 100)
    hard_percent = round(hard / total * 100)

    updated = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<svg
    width="520"
    height="200"
    viewBox="0 0 520 200"
    fill="none"
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

<!-- Title -->
<text
    x="24"
    y="35"
    class="title"
>
    Deep-ML Stats
</text>

<!-- Rank -->
<text
    x="496"
    y="34"
    text-anchor="end"
    class="label"
>
    Rank #{rank}
</text>

<!-- Main solved number -->
<text
    x="24"
    y="82"
    class="big"
>
    {solved}
</text>

<text
    x="24"
    y="102"
    class="label"
>
    Problems Solved
</text>

<!-- Level -->
<text
    x="180"
    y="82"
    class="big"
>
    {level}
</text>

<text
    x="180"
    y="102"
    class="label"
>
    Level
</text>

<!-- Difficulty labels -->

<circle
    cx="27"
    cy="133"
    r="4"
    fill="#2ecc71"
/>

<text
    x="39"
    y="138"
    class="label"
>
    Easy
</text>

<text
    x="90"
    y="138"
    class="value"
>
    {easy}
</text>

<text
    x="117"
    y="138"
    class="label"
>
    {easy_percent}%
</text>


<circle
    cx="184"
    cy="133"
    r="4"
    fill="#f1c40f"
/>

<text
    x="196"
    y="138"
    class="label"
>
    Medium
</text>

<text
    x="265"
    y="138"
    class="value"
>
    {medium}
</text>

<text
    x="292"
    y="138"
    class="label"
>
    {medium_percent}%
</text>


<circle
    cx="367"
    cy="133"
    r="4"
    fill="#e74c3c"
/>

<text
    x="379"
    y="138"
    class="label"
>
    Hard
</text>

<text
    x="425"
    y="138"
    class="value"
>
    {hard}
</text>

<text
    x="450"
    y="138"
    class="label"
>
    {hard_percent}%
</text>

<!-- Footer -->
<text
    x="24"
    y="178"
    class="footer"
>
    Updated automatically
</text>

<text
    x="496"
    y="178"
    text-anchor="end"
    class="footer"
>
    {updated}
</text>

</svg>
"""


def main():
    stats = fetch_stats()

    print()
    print("Deep-ML stats:")
    print(f"  solved: {stats['solved']}")
    print(f"  easy:   {stats['easy']}")
    print(f"  medium: {stats['medium']}")
    print(f"  hard:   {stats['hard']}")
    print(f"  level:  {stats['level']}")
    print(f"  rank:   {stats['rank']}")

    svg = generate_svg(stats)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT.write_text(
        svg,
        encoding="utf-8"
    )

    print()
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
