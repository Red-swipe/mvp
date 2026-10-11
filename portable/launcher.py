"""Portable launcher for the calculator. Finds a free port, starts the server, opens the browser."""
import os
import sys
import socket
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))
LOG = APP_DIR / "calculator_log.txt"


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def free_port(start=8000, tries=50):
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found between 8000 and 8049")


def report_startup_failure(exc):
    """Make an engine-import failure obvious instead of hiding it in a log file.

    The embeddable CPython distribution runs isolated, so `python312._pth` alone
    decides sys.path. If the application directory is missing from it, neither
    `engine` nor `mvp_server` is importable and the whole calculator is dead --
    with nothing on screen but a generic "could not start" message.
    """
    import importlib

    print("")
    print("[SELFTEST] Python executable: " + sys.executable)
    print("[SELFTEST] Python version: " + sys.version.split()[0])
    print("[SELFTEST] App directory: " + str(APP_DIR))
    print("[SELFTEST] Isolated mode (site not loaded): "
          + ("YES" if "site" not in sys.modules else "NO"))
    print("[SELFTEST] sys.path:")
    for entry in sys.path:
        print("[SELFTEST]   " + entry)
    try:
        importlib.import_module("engine")
        print("[SELFTEST] Engine import: OK")
    except Exception as eng_exc:  # noqa: BLE001 - report whatever went wrong
        print("[SELFTEST] Engine import: FAILED -> "
              + type(eng_exc).__name__ + ": " + str(eng_exc))
    print("[SELFTEST] FAILED to import mvp_server -> "
          + type(exc).__name__ + ": " + str(exc))
    print("[SELFTEST] The application folder must be on sys.path. Check that")
    print("[SELFTEST] python\\python312._pth contains a '..' line (the app folder).")
    print("[SELFTEST] Re-run BUILD_ON_MY_PC.bat to regenerate a correct build.")
    print("")


def main():
    try:
        from http.server import ThreadingHTTPServer
        try:
            import mvp_server
        except Exception as exc:  # noqa: BLE001 - startup diagnostics
            report_startup_failure(exc)
            log(traceback.format_exc())
            input("Press Enter to close...")
            return
        print("")
        mvp_server.run_startup_selftest()
        print("")
        port = free_port()
        server = ThreadingHTTPServer(("127.0.0.1", port), mvp_server.MvpHandler)
        url = f"http://127.0.0.1:{port}/"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        for _ in range(100):
            try:
                urllib.request.urlopen(url, timeout=1).read(1)
                break
            except Exception:
                time.sleep(0.1)
        print("")
        print("  Calculator is running at " + url)
        print("  Your browser should open by itself.")
        print("  If it does not, copy the address above into Chrome or Edge.")
        print("  CLOSE THIS WINDOW to stop the calculator.")
        print("")
        webbrowser.open(url)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception:
        log(traceback.format_exc())
        print("The calculator could not start. Details were saved in calculator_log.txt")
        input("Press Enter to close...")


if __name__ == "__main__":
    main()
