
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

# 1. Configuration
API_URL = "https://remotive.com/api/remote-jobs"
RAW_DIR = Path("data/raw")

# 2. Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# 3. Extract data from the API
def fetch_jobs():
    logger.info("Starting API request")

    response = requests.get(
        API_URL,
        params={"limit": 100},
        timeout=30
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("API response must be a JSON object")

    jobs = payload.get("jobs")

    if not isinstance(jobs, list):
        raise ValueError("API response does not contain a valid jobs list")

    if any(not isinstance(job, dict) for job in jobs):
        raise ValueError("API contains an invalid job record")

    if not jobs:
        raise ValueError("No jobs returned; investigate before saving")

    return payload, jobs


# 4. Save the raw response
def save_raw_data(payload, jobs):
    run_time = datetime.now(timezone.utc)
    run_id = run_time.strftime("%Y%m%dT%H%M%SZ")

    output_dir = RAW_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "jobs.json"

    output_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    logger.info("Records extracted: %s", len(jobs))
    logger.info("Raw data saved to: %s", output_file)

    return output_file


# 5. Main execution
def main():
    try:
        payload, jobs = fetch_jobs()
        output_file = save_raw_data(payload, jobs)

        print("\nJobPulse extraction successful!")
        print(f"Jobs received: {len(jobs)}")
        print(f"File created: {output_file}")

    except (requests.RequestException, ValueError, OSError) as error:
        logger.error("Extraction failed: %s", error)
        raise


if __name__ == "__main__":
    main()
