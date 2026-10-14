
from datetime import datetime
from urllib.parse import urlparse
import json
from pathlib import Path
from collections import Counter

RAW_DIR = Path("data/raw")


def find_latest_json():
    files = list(RAW_DIR.glob("*/jobs.json"))

    if not files:
        raise FileNotFoundError(
            "No raw JSON files found. Run fetch_jobs.py first."
        )

    return max(files, key=lambda file: file.stat().st_mtime)


def main():
    file_path = find_latest_json()

    with file_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    print("=" * 60)
    print("JOBPULSE: RAW DATA PROFILE")
    print("=" * 60)
    print(f"File: {file_path}")
    print(f"Top-level keys: {list(payload.keys())}")

    jobs = payload.get("jobs")

    if not isinstance(jobs, list):
        raise ValueError("Expected a list in the 'jobs' field")

    print(f"\nTotal records: {len(jobs)}")

    if not jobs:
        print("No jobs available to inspect.")
        return

    # 1. Inspect the first record's fields and data types
    first_job = jobs[0]

    print("\n--- FIRST JOB: SCHEMA ---")
    for field, value in first_job.items():
        print(
            f"{field:35} "
            f"type={type(value).__name__:10} "
            f"sample={str(value)[:80]!r}"
        )

    # 2. Inspect the fields across all records
    all_fields = set()

    for job in jobs:
        all_fields.update(job.keys())

    print("\n--- FIELD COMPLETENESS ---")

    for field in sorted(all_fields):
        missing = sum(
            field not in job or job[field] is None
            for job in jobs
        )

        blank = sum(
            isinstance(job.get(field), str)
            and not job[field].strip()
            for job in jobs
        )

        print(
            f"{field:35} "
            f"missing/null={missing:5} "
            f"blank={blank:5}"
        )

    # 3. Check top-level value types across records
    print("\n--- VALUE TYPE DISTRIBUTION ---")

    for field in sorted(all_fields):
        types = Counter(
            type(job[field]).__name__
            for job in jobs
            if field in job and job[field] is not None
        )

        print(f"{field:35} {dict(types)}")

    # 4. Check job IDs
    ids = [job.get("id") for job in jobs]
    non_null_ids = [job_id for job_id in ids if job_id is not None]

    print("\n--- IDENTIFIER CHECK ---")
    print(f"Records with IDs: {len(non_null_ids)}")
    print(f"Missing IDs: {len(ids) - len(non_null_ids)}")
    print(f"Unique non-null IDs: {len(set(non_null_ids))}")
    print(f"Duplicate ID occurrences: {len(non_null_ids) - len(set(non_null_ids))}")

    # 5. Check the key fields needed for analysis
    for field in ["title", "company_name", "url"]:
        invalid = sum(
            not isinstance(job.get(field), str)
            or not job[field].strip()
            for job in jobs
        )

        print(f"Invalid {field}: {invalid}")

    
    # 6. Validate publication dates
    print("\n--- PUBLICATION DATE CHECK ---")

    date_field = "publication_date"
    invalid_dates = 0

    for job in jobs:
        value = job.get(date_field)

        if not isinstance(value, str) or not value.strip():
            invalid_dates += 1
            continue

        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            invalid_dates += 1

    print(f"Invalid or missing publication dates: {invalid_dates}")

    # 7. Validate URL format
    print("\n--- URL CHECK ---")

    invalid_urls = 0

    for job in jobs:
        value = job.get("url")

        if not isinstance(value, str) or not value.strip():
            invalid_urls += 1
            continue

        parsed = urlparse(value)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            invalid_urls += 1

    print(f"Invalid or missing URLs: {invalid_urls}")


    print("\nProfiling complete.")


if __name__ == "__main__":
    main()
