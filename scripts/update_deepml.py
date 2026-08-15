import re
from pathlib import Path
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


PROFILE_URL = (
    "https://www.deep-ml.com/profile/"
    "1sQ5Fm3ANdfzi3dJHL8MprBzCtu1"
)

OUTPUT_FILE = Path("assets/deepml.svg")


def normalize_text(text: str) -> str:
    """Убирает лишние переносы строк и пробелы."""
    return re.sub(r"\s+", " ", text).strip()


def extract_int(pattern: str, text: str, field_name: str) -> int:
    """Находит целое число по regex."""
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        raise RuntimeError(
            f"Could not find '{field_name}' in Deep-ML profile."
        )

    return int(match.group(1))


def fetch_deepml_stats() -> dict:
    """Открывает профиль Deep-ML и получает статистику."""

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

        print("Opening Deep-ML profile...")

        page.goto(
            PROFILE_URL,
            wait_until="domcontentloaded",
            timeout=120_000,
        )

        # Ждём, пока JS на Deep-ML загрузит статистику.
        page.wait_for_function(
            """
            () => {
                const text = document.body.innerText
                    .replace(/\\s+/g, " ");

                return (
                    /Easy\\s+\\d+/i.test(text) &&
                    /Medium\\s+\\d+/i.test(text) &&
                    /Hard\\s+\\d+/i.test(text)
                );
            }
            """,
            timeout=90_000,
        )

        # Небольшая дополнительная пауза,
        # чтобы остальные данные профиля успели отрисоваться.
        page.wait_for_timeout(2000)

        text = page.locator("body").inner_text()

        browser.close()

    text = normalize_text(text)

    print("Deep-ML profile loaded.")

    # -------------------------
    # Difficulty statistics
    # -------------------------

    easy = extract_int(
        r"\bEasy\s+(\d+)",
        text,
        "easy",
    )

    medium = extract_int(
        r"\bMedium\s+(\d+)",
        text,
        "medium",
    )

    hard = extract_int(
        r"\bHard\s+(\d+)",
        text,
        "hard",
    )

    # Не парсим Solved напрямую:
    # Deep-ML может содержать рядом другие числа.
    # Считаем его надёжно из difficulty.
    solved = easy + medium + hard

    # -------------------------
    # Level
    # -------------------------

    level = extract_int(
        r"\b(?:LV|Level)\.?\s*(\d+)",
        text,
        "level",
    )

    # -------------------------
    # Rank
    # -------------------------

    rank = extract_int(
        r"\bRank\s*#?\s*(\d+)",
        text,
        "rank",
    )

    return {
        "solved": solved,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "level": level,
        "rank": rank,
    }


def generate_svg(stats: dict) -> str:
    """Генерирует SVG-карточку."""

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

    updated_at = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

    svg = f"""
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
        Deep-ML Stats
    </text>

    <text
        x="496"
        y="34"
        text-anchor="end"
        class="label"
    >
        Rank #{rank}
    </text>

    <!-- Solved -->

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
        x="190"
        y="82"
        class="big"
    >
        {level}
    </text>

    <text
        x="190"
        y="102"
        class="label"
    >
        Level
    </text>

    <!-- Easy -->

    <circle
        cx="27"
        cy="137"
        r="4"
        fill="#2ecc71"
    />

    <text
        x="39"
        y="142"
        class="label"
    >
        Easy
    </text>

    <text
        x="82"
        y="142"
        class="value"
    >
        {easy}
    </text>

    <text
        x="110"
        y="142"
        class="label"
    >
        {easy_percent}%
    </text>

    <!-- Medium -->

    <circle
        cx="178"
        cy="137"
        r="4"
        fill="#f1c40f"
    />

    <text
        x="190"
        y="142"
        class="label"
    >
        Medium
    </text>

    <text
        x="253"
        y="142"
        class="value"
    >
        {medium}
    </text>

    <text
        x="281"
        y="142"
        class="label"
    >
        {medium_percent}%
    </text>

    <!-- Hard -->

    <circle
        cx="363"
        cy="137"
        r="4"
        fill="#e74c3c"
    />

    <text
        x="375"
        y="142"
        class="label"
    >
        Hard
    </text>

    <text
        x="418"
        y="142"
        class="value"
    >
        {hard}
    </text>

    <text
        x="443"
        y="142"
        class="label"
    >
        {hard_percent}%
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

    return svg


def main():
    print("=" * 50)
    print("Updating Deep-ML statistics")
    print("=" * 50)

    stats = fetch_deepml_stats()

    print()
    print("Stats found:")
    print(f"  Solved: {stats['solved']}")
    print(f"  Easy:   {stats['easy']}")
    print(f"  Medium: {stats['medium']}")
    print(f"  Hard:   {stats['hard']}")
    print(f"  Level:  {stats['level']}")
    print(f"  Rank:   #{stats['rank']}")
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
    print("Done.")


if __name__ == "__main__":
    main()
