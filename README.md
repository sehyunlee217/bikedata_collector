# Bike Share Toronto data collector

Collects live station data from the [Bike Share Toronto API](https://open.toronto.ca/dataset/bike-share-toronto/), running on a Raspberry Pi and the snapshots uploaded to Hugging Face.

The collector saves a compressed JSON snapshot every five minutes. Files are grouped by year, month, and day in UTC:

```text
bike_data/2026/11/19/20261119T214127.123456Z.json.gz
```

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the project folder:

```bash
uv sync --locked
uv run hf auth login
```

`uv sync` creates the local `.venv`. Commit `pyproject.toml` and `uv.lock` so the Pi can install the same dependency versions.

Use a Hugging Face token with write access to your dataset. The current destination is the private dataset `sehyunlee217/bikedata_stream`.

## Collect data

```bash
uv run python hf/upload_data_hf.py
```

Snapshots are saved locally in `bike_data/` and uploaded every five minutes to `data/station_status/` in the dataset. Local files are kept after uploading.

Change these settings in `hf/upload_data_hf.py` as needed:

- `HF_REPO_ID`: destination dataset.
- `OUTPUT_DIR`: local storage folder. Use an absolute SSD path on the Pi.
- `POLL_SECONDS`: time between collection attempts, in seconds.
- `UPLOAD_MINUTES`: time between uploads, in minutes.

I use systemd to keep the collector running on the Pi and restart it after a reboot.

## Convert snapshots to CSV

`data_processing/download_as_csv.py` reads local `.json.gz` files. 

```bash
uv run python data_processing/download_as_csv.py \
  --source bike_data \
  --start 2026-11-19 \
  --end 2026-11-20 \
  --freq 15min \
  --output dataset/bikeshare/nov19.csv
```

The available frequencies are `5min`, `15min`, and `1h`. The script takes the first available snapshot in each UTC interval and skips the rest. It does not average values or fill missing intervals.

The start time is included; the end time is excluded. Each station gets one row per selected snapshot:

```csv
date,station_id,num_bikes_available,num_docks_available,mechanical,ebike
```

`date` is the collection time from the snapshot filename. `mechanical` and `ebike` are the available bike counts by type. The CSV is saved locally, and running the command again replaces the output file.
