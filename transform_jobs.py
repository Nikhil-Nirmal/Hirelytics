
import csv
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

RAW_DIR = Path("data/raw")
OUTPUT_FILE = Path("data/processed/silver_jobs.csv")


class HTMLTextExtractor(HTMLParser):
    """Extract readable text from an HTML description."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def clean_html(value):
    if not isinstance(value, str):
        return ""

    parser = HTMLTextExtractor()
    parser.feed(value)
    parser.close()

    return re.sub(r"\s+", " ", parser.get_text()).strip()


def find_latest_json():
    files = list(RAW_DIR.glob("*/jobs.json"))

    if not files:
        raise FileNotFoundError(
            "No raw snapshots found. Run fetch_jobs.py first."
        )

    return max(files, key=lambda file: file.stat().st_mtime)


def clean_job(job):
    required = ["id", "title", "company_name", "url", "publication_date"]

    for field in required:
        value = job.get(field)

        if value is None or (
            isinstance(value, str) and not value.strip()
        ):
            raise ValueError(f"Missing required field: {field}")

    source_job_id = str(job["id"]).strip()

    if not source_job_id:
        raise ValueError("Empty job ID")

    published_at = datetime.fromisoformat(
        job["publication_date"].replace("Z", "+00:00")
    )

    # Make timestamps consistent and timezone-aware.
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    published_at = published_at.astimezone(timezone.utc)

    tags = job.get("tags")
    if not isinstance(tags, list):
        tags = []

    tags = [
        str(tag).strip()
        for tag in tags
        if tag is not None and str(tag).strip()
    ]

    job_type = job.get("job_type")
    job_type = (
        job_type.strip().replace("_", " ").title()
        if isinstance(job_type, str) and job_type.strip()
        else None
    )

    return {
        "source_name": "remotive",
        "job_key": f"remotive:{source_job_id}",
        "source_job_id": source_job_id,
        "title": job["title"].strip(),
        "company_name": job["company_name"].strip(),
        "category": clean_text(job.get("category")),
        "job_type": job_type,
        "location_text": clean_text(
            job.get("candidate_required_location")
        ),
        "published_at": published_at.isoformat(),
        "salary_text": clean_text(job.get("salary")),
        "tags_json": json.dumps(tags, ensure_ascii=False),
        "description_text": clean_html(job.get("description")),
        "job_url": job["url"].strip(),
        "company_logo_url": clean_text(
            job.get("company_logo_url")
        ),
    }


def clean_text(value):
    return value.strip() if isinstance(value, str) else ""


def main():
    raw_file = find_latest_json()

    with raw_file.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    jobs = payload.get("jobs")

    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Raw snapshot contains no valid jobs list")

    cleaned_jobs = []
    rejected_jobs = []

    for index, job in enumerate(jobs):
        try:
            cleaned_jobs.append(clean_job(job))
        except (ValueError, TypeError, KeyError) as error:
            rejected_jobs.append({
                "record_index": index,
                "error": str(error),
            })

    # Prevent a partial dataset from being accepted silently.
    if rejected_jobs:
        print(f"Rejected records: {len(rejected_jobs)}")
        for record in rejected_jobs:
            print(record)

        raise ValueError(
            "Some records failed validation. "
            "Review them before publishing the Silver dataset."
        )

    keys = [job["job_key"] for job in cleaned_jobs]

    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate job keys detected")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(cleaned_jobs[0].keys())

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_jobs)

    print("Silver transformation successful!")
    print(f"Input records: {len(jobs)}")
    print(f"Clean records: {len(cleaned_jobs)}")
    print(f"Rejected records: {len(rejected_jobs)}")
    print(f"Unique job keys: {len(set(keys))}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
