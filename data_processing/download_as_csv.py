"""
    [Joe]
    - Script to download JSON.gz compressed data from the HF Dataset Repo.
    - Select the first snapshot per 5min, 15min, or 1 hour UTC.
"""

import argparse
import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

INTERVALS = {"5min": 300, "15min": 900, "1h": 3600}
FIELDS = ["date", "station_id", "num_bikes_available", "num_docks_available",
          "mechanical", "ebike"]


def utc_time(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def prepare(args):
    start, end = utc_time(args.start), utc_time(args.end)
    if start >= end:
        raise ValueError("End must be after start!")
    if not args.source.is_dir():
        raise ValueError(f"Snapshot folder not found at {args.source}")

    snapshots = []
    for path in args.source.rglob("*.json.gz"):
        if not path.is_file():
            continue
        name = path.name.removesuffix(".json.gz")
        try:
            stamp = datetime.strptime(name, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue  
        if start <= stamp < end:
            snapshots.append((stamp, path))
    if not snapshots:
        raise ValueError("No snapshots found!")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    previous_interval = None
    snapshot_count = row_count = 0
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for stamp, path in sorted(snapshots):
            interval = int(stamp.timestamp()) // INTERVALS[args.freq]
            if interval == previous_interval:
                continue

            with gzip.open(path, "rt", encoding="utf-8") as source:
                payload = json.load(source)
            for station in payload["data"]["stations"]:
                types = station.get("num_bikes_available_types") or {}
                writer.writerow({
                    "date": stamp.isoformat(),
                    "station_id": station["station_id"],
                    "num_bikes_available": station.get("num_bikes_available"),
                    "num_docks_available": station.get("num_docks_available"),
                    "mechanical": types.get("mechanical"),
                    "ebike": types.get("ebike"),
                })
                row_count += 1
            previous_interval = interval
            snapshot_count += 1
    print(f"Saved {snapshot_count:,} snapshots ({row_count:,} station rows) to {args.output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("bike_data"))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--freq", choices=INTERVALS, default="15min")
    parser.add_argument("--output", type=Path, default=Path("dataset/bikeshare/prepared.csv"))
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
