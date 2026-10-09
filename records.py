import json
import math
from pathlib import Path

import requests


SOURCE_URL = "https://api.tvmaze.com/shows?page=0"
OUTPUT = Path("summary.json")


def fetch_records(url):
    """Download and validate a list of at least 50 show records."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    records = response.json()

    if not isinstance(records, list):
        raise ValueError("The API did not return a list of records.")

    if len(records) < 50:
        raise ValueError("The API returned fewer than 50 records.")

    if any(not isinstance(record, dict) for record in records):
        raise ValueError("The API returned a malformed show record.")

    return records


def valid_genres(record):
    """Return unique valid genre labels for one show."""
    genres = record.get("genres")

    if not isinstance(genres, list):
        return set()

    return {
        genre.strip()
        for genre in genres
        if isinstance(genre, str) and genre.strip()
    }


def shows_per_genre(records):
    """Count each show once in each of its valid genres."""
    counts = {}
    without_genres = 0

    for record in records:
        genres = valid_genres(record)

        if not genres:
            without_genres += 1

        for genre in genres:
            counts[genre] = counts.get(genre, 0) + 1

    return {
        "counts": dict(sorted(counts.items())),
        "shows_without_valid_genres": without_genres,
    }


def average_rating_by_language(records):
    """Average valid ratings by language and report excluded shows."""
    groups = {}
    missing_language = 0
    missing_rating = 0

    for record in records:
        language = record.get("language")
        rating_data = record.get("rating")
        rating = (
            rating_data.get("average")
            if isinstance(rating_data, dict)
            else None
        )

        language_ok = isinstance(language, str) and bool(language.strip())
        rating_ok = (
            isinstance(rating, (int, float))
            and not isinstance(rating, bool)
            and math.isfinite(rating)
            and 0 <= rating <= 10
        )

        if not language_ok:
            missing_language += 1

        if not rating_ok:
            missing_rating += 1

        if not language_ok or not rating_ok:
            continue

        language = language.strip()

        if language not in groups:
            groups[language] = []

        groups[language].append(rating)

    averages = {
        language: {
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "rated_shows": len(ratings),
        }
        for language, ratings in sorted(groups.items())
    }

    return {
        "languages": averages,
        "shows_without_valid_language": missing_language,
        "shows_without_valid_rating": missing_rating,
        "shows_included": sum(len(ratings) for ratings in groups.values()),
    }


def build_summary(records):
    """Combine the source information and both aggregations."""
    return {
        "source_url": SOURCE_URL,
        "records_processed": len(records),
        "shows_per_genre": shows_per_genre(records),
        "average_rating_by_language": average_rating_by_language(records),
    }


def write_summary(summary, path):
    """Write the summary as formatted UTF-8 JSON."""
    with path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    """Download shows, summarize them, and save the results."""
    try:
        records = fetch_records(SOURCE_URL)
    except (requests.RequestException, ValueError) as error:
        print(f"Download failed: {error}")
        return 1

    summary = build_summary(records)

    try:
        write_summary(summary, OUTPUT)
    except OSError as error:
        print(f"Could not save the summary: {error}")
        return 1

    print(f"Processed {len(records)} shows.")
    print(f"Summary saved to {OUTPUT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())