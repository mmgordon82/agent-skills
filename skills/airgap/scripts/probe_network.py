#!/usr/bin/env python3
"""Check that this environment has loopback but no outside network. Run it inside the isolated
environment, before the program under test. Exit 0 = isolated, 1 = not isolated. Stdlib only, so it
runs in any image with python3."""

import http.server
import json
import socket
import sys
import threading
import urllib.error
import urllib.request

results: dict[str, str | list[str]] = {}
isolated = True


class Ok(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"loopback-ok")

    def log_message(self, *args):
        pass


server = http.server.HTTPServer(("127.0.0.1", 0), Ok)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    body = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=2).read()
    results["loopback"] = "ok" if body == b"loopback-ok" else f"unexpected reply {body!r}"
except OSError as e:
    results["loopback"] = f"FAILED: {e}"  # programs that talk to themselves won't work
    isolated = False
finally:
    server.shutdown()

# Informational: interface names. Some kernels add down, address-less tunnels (sit0, tunl0) to every
# namespace, so the connect checks below decide the verdict, not this list.
results["interfaces"] = sorted(name for _, name in socket.if_nameindex())

try:
    socket.create_connection(("1.1.1.1", 443), timeout=2).close()  # literal IP: no DNS involved
    results["public_tcp"] = "REACHABLE: not isolated"
    isolated = False
except OSError as e:
    results["public_tcp"] = f"blocked ({e})"

try:
    urllib.request.urlopen("https://example.com/", timeout=3)
    results["public_https"] = "REACHABLE: not isolated"
    isolated = False
except urllib.error.HTTPError as e:  # any HTTP status, even 403/404, means a server answered
    results["public_https"] = f"REACHABLE (HTTP {e.code}): not isolated"
    isolated = False
except OSError as e:
    results["public_https"] = f"blocked ({getattr(e, 'reason', e)})"

results["verdict"] = "isolated" if isolated else "NOT ISOLATED"
print(json.dumps(results, indent=2))
sys.exit(0 if isolated else 1)
