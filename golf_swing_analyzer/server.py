#!/usr/bin/env python3
"""
server.py  --  Opens the 3D viewer in your web browser.

Why do we need this? Web browsers refuse to load local files (like your
swing.json) directly for safety reasons. So we run a tiny local web server
that hands the viewer its files. Nothing leaves your computer.

Use:
    python server.py            # starts server + opens your browser
    python server.py --port 9000
    python server.py --no-open  # just start the server, don't open a browser

Then in the page you can pick any swing you've recorded, or drag-and-drop a
swing.json file straight onto the page.
"""

import argparse
import http.server
import json
import os
import socketserver
import webbrowser
from functools import partial

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves the viewer files, plus a small list of recorded swings."""

    def do_GET(self):
        if self.path == "/api/swings":
            return self._list_swings()
        return super().do_GET()

    def _list_swings(self):
        swings_dir = os.path.join(HERE, "swings")
        found = []
        if os.path.isdir(swings_dir):
            for name in sorted(os.listdir(swings_dir), reverse=True):
                p = os.path.join(swings_dir, name, "swing.json")
                if os.path.isfile(p):
                    found.append({
                        "name": name,
                        "url": f"/swings/{name}/swing.json",
                    })
        body = json.dumps(found).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep the terminal quiet


def main():
    ap = argparse.ArgumentParser(description="Serve the golf swing 3D viewer.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1",
                    help="Use 0.0.0.0 to reach it from another device on your network.")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    os.chdir(HERE)
    handler = partial(Handler, directory=HERE)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        url = f"http://{'localhost' if args.host in ('127.0.0.1','0.0.0.0') else args.host}:{args.port}/viewer/"
        print(f"Golf Swing viewer running at:  {url}")
        print("Press Ctrl+C to stop.")
        if not args.no_open:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
