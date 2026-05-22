# Import Cameras from go2rtc.yaml Script

## Overview
This script imports camera registry data from the `go2rtc/go2rtc.yaml` file into the PostgreSQL database used by the CCTV Centralization backend. It aligns with the current architecture by preserving existing cameras, skipping duplicates, and auto-creating the branch "SIG Kendal" if it does not exist.

## Usage

1. Ensure your Python environment has the required dependencies installed, including `PyYAML` and SQLAlchemy.

2. Run the import script from the project root directory:

```bash
python backend/scripts/import_cameras_from_go2rtc.py
```

3. The script will:
   - Read `go2rtc/go2rtc.yaml`
   - Parse camera streams for `stream_name` and `rtsp_channel`
   - Create cameras in the database under branch "SIG Kendal" if missing
   - Skip duplicates and preserve existing cameras
   - Print a summary of imported and skipped cameras

## Notes
- The script does NOT overwrite existing camera records.
- Cameras without an `rtsp_channel` field in the YAML are skipped.
- The camera name is inferred directly from the stream name.
- The branch "SIG Kendal" is created automatically if it does not exist.

## Example Output

```
Import complete: 5 cameras imported, 3 duplicates skipped.
```

This indicates 5 new cameras were added and 3 existing cameras were detected and skipped.

## Troubleshooting

- Ensure the database connection is properly configured in the backend.
- Verify the `go2rtc/go2rtc.yaml` file exists and is correctly formatted.
- Run the script with appropriate permissions to access the database.