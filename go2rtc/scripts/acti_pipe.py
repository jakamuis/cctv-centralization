#!/usr/bin/env python3
"""
Read an ACTi SNVR stream (multipart/x-mixed-replace with H264 parts)
and write clean H264 Annex B to stdout for go2rtc exec: source.

Usage (live):
  python3 acti_pipe.py <host> <channel> <user> <pass> [port]

Usage (playback):
  python3 acti_pipe.py --playback <host> <channel> <unix_sec> <user> <pass> [port]

go2rtc go2rtc.yaml entries:
  live:     "exec:python3 /scripts/acti_pipe.py 192.168.x.x 1 admin pass#video=h264"
  playback: "exec:python3 /scripts/acti_pipe.py --playback 192.168.x.x 1 1748217600 admin pass#video=h264"
"""
import sys
import socket
import base64
import re

def main():
    args = sys.argv[1:]

    if args and args[0] == '--playback':
        # playback mode: --playback <host> <channel> <unix_sec> <user> <pass> [port]
        host    = args[1]
        channel = args[2]
        sec     = args[3]
        user    = args[4]
        pwd     = args[5]
        port    = int(args[6]) if len(args) > 6 else 80
        path    = f'/playback/?cmd=1&channel={channel}&sec={sec}&usec=0&mode=0&i_only=0'
    else:
        # live mode: <host> <channel> <user> <pass> [port]
        host    = args[0]
        channel = args[1]
        user    = args[2]
        pwd     = args[3]
        port    = int(args[4]) if len(args) > 4 else 80
        path    = f'/virtualcamera/channel{channel}?media&streamid=0'

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
