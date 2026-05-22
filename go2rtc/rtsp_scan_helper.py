import yaml
import subprocess
import re
from pathlib import Path

# Configuration
NVR_HOST = "192.168.2.100"
USERNAME = "admin"
PASSWORD = "Indogas*19%23"
CHANNELS = [f"{i}02" for i in range(1, 33)]  # 102, 202, ..., 3202
GO2RTC_YAML_PATH = Path("go2rtc/go2rtc.yaml")
SCAN_RESULTS_PATH = Path("rtsp_scan_results.txt")
UPDATED_YAML_DRAFT_PATH = Path("go2rtc/go2rtc_updated_draft.yaml")

# Naming fallback prefix
FALLBACK_PREFIX = "sig-kendal-cam-"

def load_existing_streams():
    if not GO2RTC_YAML_PATH.exists():
        return {}
    with GO2RTC_YAML_PATH.open("r") as f:
        data = yaml.safe_load(f)
    streams = data.get("streams", {}) if data else {}
    return streams

def build_rtsp_url(channel):
    return f"rtsp://{USERNAME}:{PASSWORD}@{NVR_HOST}:554/Streaming/Channels/{channel}"

import socket

def check_rtsp_stream(url):
    # Check RTSP stream availability by attempting TCP connection to host:port
    try:
        # Extract host and port from URL
        # URL format: rtsp://username:password@host:port/...
        import re
        m = re.match(r"rtsp://(?:[^@]+@)?([^:/]+)(?::(\\d+))?", url)
        if not m:
            return False
        host = m.group(1)
        port = int(m.group(2)) if m.group(2) else 554
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False

def extract_channel_from_url(url):
    # Extract channel number from URL path
    m = re.search(r"Channels/(\\d+)", url)
    if m:
        return m.group(1)
    return None

def main():
    existing_streams = load_existing_streams()
    # Map channel to camera name if exists
    channel_to_name = {}
    for name, info in existing_streams.items():
        url = info.get("url", "")
        channel = extract_channel_from_url(url)
        if channel:
            channel_to_name[channel] = name

    online_channels = []
    offline_channels = []
    new_streams = {}

    fallback_index = 1

    for channel in CHANNELS:
        url = build_rtsp_url(channel)
        reachable = check_rtsp_stream(url)
        if reachable:
            online_channels.append(channel)
            if channel in channel_to_name:
                cam_name = channel_to_name[channel]
            else:
                # Assign fallback name
                while True:
                    cam_name = f"{FALLBACK_PREFIX}{fallback_index:02d}"
                    fallback_index += 1
                    if cam_name not in existing_streams and cam_name not in new_streams:
                        break
            new_streams[cam_name] = {"url": url}
        else:
            offline_channels.append(channel)

    # Merge existing streams with new streams (new streams override if same name)
    updated_streams = existing_streams.copy()
    updated_streams.update(new_streams)

    # Write scan results
    with SCAN_RESULTS_PATH.open("w") as f:
        f.write("RTSP Scan Results\\n")
        f.write("================\\n")
        f.write("ONLINE Channels:\\n")
        for ch in online_channels:
            f.write(f"{ch}\\n")
        f.write("\\nOFFLINE Channels:\\n")
        for ch in offline_channels:
            f.write(f"{ch}\\n")

    # Write updated go2rtc.yaml draft
    updated_yaml = {"streams": updated_streams}
    with UPDATED_YAML_DRAFT_PATH.open("w") as f:
        yaml.dump(updated_yaml, f, default_flow_style=False, sort_keys=False)

    # Print summary
    print(f"Online channels: {online_channels}")
    print(f"Offline channels: {offline_channels}")
    print(f"Scan results saved to {SCAN_RESULTS_PATH}")
    print(f"Updated go2rtc.yaml draft saved to {UPDATED_YAML_DRAFT_PATH}")

if __name__ == "__main__":
    main()