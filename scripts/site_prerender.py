"""Serve the site locally and collect pre-rendered build-guide pictures.

    python scripts/site_prerender.py [--port 8765]

Then open http://127.0.0.1:<port>/fax-machine/?prerender=1 in any browser with
WebGL (or drive it with Playwright) and wait until <html data-prerendered="1">.
The page renders the hero still, the how-it-works callouts, the parts inventory
and every build step with the same renderer the live page uses, and POSTs each
PNG here. They land in site/img/render/ with an index.json that records the
parts.json hash they were made from: the live page uses them as-is when the hash
matches (and always when WebGL is missing), and re-renders when it doesn't.
Stop the server with Ctrl-C, then run scripts/build_site.py to stamp versions.
"""
from __future__ import annotations

import argparse
import base64
import http.server
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "img" / "render"
PREFIX = "/fax-machine"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def translate_path(self, path):
        if path.startswith(PREFIX):
            path = path[len(PREFIX):] or "/"
        return super().translate_path(path)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        if self.path.startswith("/__prerender/save"):
            name = self.path.split("name=", 1)[-1]
            if not re.fullmatch(r"[A-Za-z0-9_\-]+", name):
                return self.send_error(400)
            data = body.decode().split(",", 1)[-1]
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / f"{name}.png").write_bytes(base64.b64decode(data))
        elif self.path.startswith("/__prerender/index"):
            idx = json.loads(body)
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "index.json").write_text(json.dumps(idx, indent=1) + "\n")
            keep = {Path(v).name for v in idx.get("files", {}).values()}
            for f in OUT.glob("*.png"):      # drop pictures of parts or steps that no longer exist
                if f.name not in keep:
                    f.unlink()
            print("wrote index with", len(idx.get("files", {})), "pictures")
        else:
            return self.send_error(404)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    port = ap.parse_args().port
    print(f"http://127.0.0.1:{port}{PREFIX}/?prerender=1")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
