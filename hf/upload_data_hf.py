"""
    [Joe]
    - Script to fetch and upload data to HF Dataset Repo
    - Running on Raspberry Pi atm
"""


import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from huggingface_hub import CommitScheduler
import httpx
import gzip

STATION_STATUS_URL = (
    "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_status"
)


HF_REPO_ID = "sehyunlee217/bikedata_stream"
OUTPUT_DIR = Path("bike_data").resolve()
POLL_SECONDS = 60*5 # Collect every 5 minutes
UPLOAD_MINUTES = 5 # Upload every 5 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def fetch_json(client, url):
    response = client.get(url)
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")

    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("stations"), list):
        raise ValueError("Response is missing data.stations")

    if not data["stations"]:
        raise ValueError("Response contains no stations")

    return payload


def save_snapshot(payload):
    collected_at = datetime.now(timezone.utc)

    day_dir = OUTPUT_DIR / collected_at.strftime("%Y/%m/%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    filename = collected_at.strftime("%Y%m%dT%H%M%S.%fZ.json.gz")
    destination = day_dir / filename
    temporary = destination.with_suffix(".tmp")

    # save as json.gz
    with gzip.open(
        temporary,
        "wt",
        encoding="utf-8",
        compresslevel=6,
    ) as file:
        json.dump(payload, file, separators=(",", ":"))

    temporary.replace(destination)

    return destination


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with CommitScheduler(
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        private=True,
        folder_path=OUTPUT_DIR,
        path_in_repo="data/station_status",
        every=UPLOAD_MINUTES,
        allow_patterns=["*.json", "*.json.gz"],
    ) as scheduler:
        with httpx.Client(timeout=20) as client:
            while True:
                try:
                    payload = fetch_json(client, STATION_STATUS_URL)

                    with scheduler.lock:
                        path = save_snapshot(payload)

                    logging.info(
                        "Saved %s stations to %s",
                        len(payload["data"]["stations"]),
                        path,
                    )
                except (httpx.HTTPError, ValueError):
                    logging.exception("API collection failed")

                time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()