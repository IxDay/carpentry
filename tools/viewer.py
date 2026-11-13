#!/usr/bin/env python3
"""Serve the joints site locally.

Builds the same site that is published on GitHub Pages (see ``build_site.py``)
into a temporary folder and serves it, so the local page and the published one
are identical.

    python3 tools/viewer.py                       # joints site, port 8080
    python3 tools/viewer.py --port 9000 --open
"""
import argparse
import functools
import os
import sys
import tempfile
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import build_site

HERE = os.path.dirname(os.path.abspath(__file__))


class SiteHandler(SimpleHTTPRequestHandler):
    """Static files of the built site, never cached so a rebuild shows up."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=os.path.join(HERE, "..", "joints"),
                    help="directory with baked GLBs and sources/ (default: joints)")
    ap.add_argument("--port", type=int, default=8080, help="port (default 8080)")
    ap.add_argument("--host", default="127.0.0.1",
                    help="bind address (default 127.0.0.1)")
    ap.add_argument("--open", action="store_true", help="open a browser")
    args = ap.parse_args()

    root = os.path.realpath(args.dir)
    if not os.path.isdir(os.path.join(root, "sources")):
        sys.exit("no joints sources under %s" % root)

    with tempfile.TemporaryDirectory(prefix="joints-site-") as out:
        build_site.build(root, out, "")
        handler = functools.partial(SiteHandler, directory=out)
        httpd = ThreadingHTTPServer((args.host, args.port), handler)
        httpd.daemon_threads = True
        url = "http://%s:%d/" % (args.host, args.port)
        print("Listening on %s" % url)
        if args.open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()


if __name__ == "__main__":
    main()
