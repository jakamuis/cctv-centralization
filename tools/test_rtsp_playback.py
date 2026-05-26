"""
Test RTSP across all channels with today's date to find active recordings.
"""
import socket, hashlib, re, sys

NVR  = "192.168.2.100"
PORT = 554
USER = sys.argv[1]
PASS = sys.argv[2]

# Today 2026-05-25, a few hours ago
TESTS = [
    # (track_id, start, end, label)
    (101, "20260525T050000Z", "20260525T060000Z", "ch1 today 05-06h"),
    (201, "20260525T050000Z", "20260525T060000Z", "ch2 today 05-06h"),
    (301, "20260525T050000Z", "20260525T060000Z", "ch3 today 05-06h"),
    (401, "20260525T050000Z", "20260525T060000Z", "ch4 today 05-06h"),
    (501, "20260525T050000Z", "20260525T060000Z", "ch5 today 05-06h"),
    (601, "20260525T050000Z", "20260525T060000Z", "ch6 today 05-06h"),
    # Also try channel 10 (what user was testing in iVMS)
    (1001, "20260525T050000Z", "20260525T060000Z", "ch10 today 05-06h"),
    # Try older date on ch1 in case retention is long
    (101,  "20260522T090000Z", "20260522T100000Z", "ch1 2026-05-22"),
]


def describe(track, start, end):
    uri = f"/Streaming/tracks/{track}?starttime={start}&endtime={end}"
    try:
        with socket.create_connection((NVR, PORT), timeout=5) as s:
            s.settimeout(5)
            # DESCRIBE without auth
            req = f"DESCRIBE rtsp://{NVR}:{PORT}{uri} RTSP/1.0\r\nCSeq: 1\r\nAccept: application/sdp\r\n\r\n"
            s.sendall(req.encode())
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = s.recv(4096)
                if not chunk: break
                data += chunk
            resp = data.decode(errors="replace")

            if "200 OK" in resp:
                return "200 OK - RECORDING EXISTS"
            if "401" in resp:
                # Try with auth
                realm = re.search(r'realm="([^"]+)"', resp)
                nonce = re.search(r'nonce="([^"]+)"', resp)
                if realm and nonce:
                    ha1 = hashlib.md5(f"{USER}:{realm.group(1)}:{PASS}".encode()).hexdigest()
                    ha2 = hashlib.md5(f"DESCRIBE:{uri}".encode()).hexdigest()
                    rsp = hashlib.md5(f"{ha1}:{nonce.group(1)}:{ha2}".encode()).hexdigest()
                    auth = (f'Digest username="{USER}", realm="{realm.group(1)}", '
                            f'nonce="{nonce.group(1)}", uri="{uri}", response="{rsp}"')
                    req2 = (f"DESCRIBE rtsp://{NVR}:{PORT}{uri} RTSP/1.0\r\n"
                            f"CSeq: 2\r\nAccept: application/sdp\r\n"
                            f"Authorization: {auth}\r\n\r\n")
                    s.sendall(req2.encode())
                    data2 = b""
                    while b"\r\n\r\n" not in data2:
                        chunk = s.recv(4096)
                        if not chunk: break
                        data2 += chunk
                    resp2 = data2.decode(errors="replace")
                    code = resp2.split(" ")[1] if " " in resp2 else "?"
                    snippet = resp2[:80].replace("\r\n", " ")
                    return f"HTTP {code} | {snippet}"
            code = resp.split(" ")[1] if " " in resp else "?"
            return f"RTSP {code}"
    except Exception as e:
        return f"ERROR: {e}"


print(f"{'Track':<6} {'Label':<30} {'Result'}")
print("-" * 80)
for track, start, end, label in TESTS:
    result = describe(track, start, end)
    print(f"  {track:<6} {label:<30} {result}")
