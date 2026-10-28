"""Portable launcher for the calculator server."""
import argparse
import os
import sys
import threading
import urllib.request
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))


def start_server():
    import mvp_server
    mvp_server.run_startup_selftest()
    server = None
    for port in range(8000, 8050):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), mvp_server.MvpHandler)
            break
        except OSError:
            continue
    if server is None:
        raise RuntimeError("Ports 8000-8049 are occupied. Close another calculator and try again.")
    url = f"http://127.0.0.1:{server.server_port}/"
    thread = threading.Thread(target=server.serve_forever, name="calculator-http", daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"Server health check returned HTTP {response.status}")
            response.read(1)
        return server, url
    except Exception:
        server.shutdown()
        server.server_close()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    parser.add_argument("--smoke-test", action="store_true", help="start, request the app, then stop")
    args = parser.parse_args()
    server = None
    try:
        server, url = start_server()
        print(f"Calculator server OK: {url}", flush=True)
        if args.smoke_test:
            return 0
        if not args.no_browser:
            webbrowser.open(url)
        print("Close this window or press Ctrl+C to stop the calculator.", flush=True)
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"ERROR: Calculator could not start: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        print(f"Details: {APP_DIR / 'calculator_log.txt'}", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
