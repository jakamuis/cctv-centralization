#!/usr/bin/env python3
"""
Read an ACTi SNVR stream (multipart/x-mixed-replace with H264 parts)
and write clean H264 Annex B to stdout for go2rtc exec: source.

Usage (live):     python3 acti_pipe.py <host> <channel> <user> <pass> [port]
Usage (playback): python3 acti_pipe.py <host> <path> <user> <pass> [port]

  <channel> is a digit → live URL /virtualcamera/channel{N}?media&streamid=0
  <path> starts with / → used verbatim as the HTTP request path

go2rtc go2rtc.yaml entries:
  live:     "exec:python3 /scripts/acti_pipe.py 192.168.x.x 1 admin pass#video=h264"
  playback: "exec:python3 /scripts/acti_pipe.py 192.168.x.x /playback/?cmd=1&channel=1&sec=1234567890&usec=0&mode=0&i_only=0 admin pass#video=h264"
"""
import sys
import socket
import base64
import re

def main():
    host           = sys.argv[1]
    channel_or_path = sys.argv[2]
    user    = sys.argv[3]
    pwd     = sys.argv[4]
    port    = int(sys.argv[5]) if len(sys.argv) > 5 else 80

    if channel_or_path.isdigit():
        path = f'/virtualcamera/channel{channel_or_path}?media&streamid=0'
    else:
        path = channel_or_path

    b64 = base64.b64encode(f'{user}:{pwd}'.encode()).decode()
    req = (
        f'GET {path} HTTP/1.0\r\n'
        f'Host: {host}\r\n'
        f'Authorization: Basic {b64}\r\n'
        f'Connection: keep-alive\r\n'
        f'\r\n'
    ).encode()

    s = socket.create_connection((host, port), timeout=30)
    s.sendall(req)

    buf = b''
    # Skip outer HTTP response headers
    while b'\r\n\r\n' not in buf:
        chunk = s.recv(4096)
        if not chunk:
            return
        buf += chunk
    buf = buf[buf.index(b'\r\n\r\n') + 4:]

    stdout = sys.stdout.buffer

    while True:
        # Accumulate until we have a full multipart sub-header block
        while b'\r\n\r\n' not in buf:
            chunk = s.recv(65536)
            if not chunk:
                return
            buf += chunk

        hdr_end = buf.index(b'\r\n\r\n') + 4
        headers = buf[:hdr_end].decode('ascii', errors='replace')
        buf = buf[hdr_end:]

        m = re.search(r'Content-Length:\s*(\d+)', headers, re.IGNORECASE)
        if not m:
            # No content-length — skip to next boundary
            continue
        content_length = int(m.group(1))

        # Read exactly content_length bytes
        while len(buf) < content_length:
            chunk = s.recv(65536)
            if not chunk:
                return
            buf += chunk

        data = buf[:content_length]
        buf  = buf[content_length:]

        # ACTi prepends a proprietary NAL before SPS. Skip to first SPS
        # (00 00 00 01 67) so decoders see clean Annex B.
        sps = data.find(b'\x00\x00\x00\x01\x67')
        if sps > 0:
            data = data[sps:]
        elif sps < 0:
            # No SPS — still pass the data, decoder will skip unknown NALs
            pass

        stdout.write(data)
        stdout.flush()


if __name__ == '__main__':
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
