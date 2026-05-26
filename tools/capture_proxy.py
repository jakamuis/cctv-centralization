"""
tools/capture_proxy.py

Threaded HTTP proxy that intercepts iVMS-4200 <-> NVR traffic.
- Captures and prints POST /ISAPI/ContentMgmt/search request XML
- Logs response bodies for key diagnostic paths
"""

import http.server
import http.client
import socketserver
import threading
import sys

NVR_HOST = "192.168.2.100"
NVR_PORT = 80
LISTEN_PORT = 8080
CAPTURE_LOCK = threading.Lock()

# Paths whose REQUEST body we want to capture
CAPTURE_REQUEST = {"/ISAPI/ContentMgmt/search"}

# Paths whose RESPONSE body we want to log (for diagnostics)
LOG_RESPONSE = {
    "/ISAPI/ContentMgmt/search/capabilities",
    "/ISAPI/ContentMgmt/search",
    "/ISAPI/ContentMgmt/record/tracks",
    "/ISAPI/ContentMgmt/Storage/hdd",
}

# Paths the NVR does not understand — return empty 200 so iVMS doesn't stall
_STUB_PREFIXES = ("/4200/",)


class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def _forward(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        # Capture the search request XML
        if self.command == "POST" and self.path in CAPTURE_REQUEST and body:
            with CAPTURE_LOCK:
                print("\n" + "=" * 70, flush=True)
                print(f"*** CAPTURED REQUEST: {self.command} {self.path} ***", flush=True)
                print("=" * 70, flush=True)
                try:
                    print(body.decode("utf-8"), flush=True)
                except Exception:
                    print(repr(body), flush=True)
                print("=" * 70 + "\n", flush=True)

        # Stub out cloud paths the NVR doesn't know about
        if any(self.path.startswith(p) for p in _STUB_PREFIXES):
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return

        # Forward to NVR — force Connection: close so each request is independent
        fwd_headers = {}
        for k, v in self.headers.items():
            kl = k.lower()
            if kl in ("host", "connection", "proxy-connection",
                      "keep-alive", "transfer-encoding"):
                continue
            fwd_headers[k] = v
        fwd_headers["Connection"] = "close"
        if body:
            fwd_headers["Content-Length"] = str(len(body))

        try:
            conn = http.client.HTTPConnection(NVR_HOST, NVR_PORT, timeout=30)
            conn.request(self.command, self.path, body=body or None,
                         headers=fwd_headers)
            resp = conn.getresponse()
            resp_body = resp.read()
            conn.close()
        except Exception as exc:
            self.send_error(502, f"NVR unreachable: {exc}")
            return

        # Log response for diagnostic paths
        base_path = self.path.split("?")[0]
        if base_path in LOG_RESPONSE:
            with CAPTURE_LOCK:
                print(f"\n--- RESPONSE [{resp.status}] {self.command} {self.path} ---", flush=True)
                try:
                    print(resp_body.decode("utf-8")[:2000], flush=True)
                except Exception:
                    print(repr(resp_body[:500]), flush=True)
                print("---\n", flush=True)

        # Send response back to iVMS
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() in ("transfer-encoding", "connection",
                              "keep-alive", "content-length"):
                continue
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(resp_body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(resp_body)

    def do_GET(self):    self._forward()
    def do_POST(self):   self._forward()
    def do_PUT(self):    self._forward()
    def do_DELETE(self): self._forward()
    def do_HEAD(self):   self._forward()

    def log_message(self, fmt, *args):
        try:
            print(f"[proxy] {self.command} {self.path}", flush=True)
        except Exception:
            pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    server = ThreadedHTTPServer(("0.0.0.0", LISTEN_PORT), ProxyHandler)
    print(f"Proxy listening on 0.0.0.0:{LISTEN_PORT}  ->  {NVR_HOST}:{NVR_PORT}", flush=True)
    print(f"In iVMS-4200: NVR IP=127.0.0.1  Port={LISTEN_PORT}", flush=True)
    print("Waiting for playback search ...\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nProxy stopped.")
        sys.exit(0)
