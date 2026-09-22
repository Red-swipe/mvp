import json
import os
import subprocess
import threading
import time
import sys
import urllib.request

sys.path.insert(0, r'E:\A.G\casio_mvp')
from mvp_server import CONTROLLER, CONTROLLER_LOCK

def start_server():
    proc = subprocess.Popen(
        [sys.executable, 'mvp_server.py', '--port', '8080'],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    return proc

# Start server
proc = start_server()

# Reset controller state
with CONTROLLER_LOCK:
    CONTROLLER.expression = ""
    CONTROLLER.cursor_position = 0
    CONTROLLER.last_result = None
    CONTROLLER.result_displayed = False
    CONTROLLER.state = "INPUT"
    CONTROLLER.ans = "0"
    CONTROLLER.shift = False
    CONTROLLER.alpha = False

def send_payload(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request('http://127.0.0.1:8080/api/key', data=data, headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read().decode())
    except Exception as e:
        return {'error': str(e), 'ok': False}

# Test the full flow: press 1, +, 1, =
print("=== Testing full flow ===")

# Press 1
result = send_payload({'key': '1'})
print(f"Press 1: state={result.get('state')}, display={result.get('display')}, expr={result.get('expression')}")

# Press +
result = send_payload({'key': 'plus'})
print(f"Press +: state={result.get('state')}, display={result.get('display')}, expr={result.get('expression')}")

# Press 1 again
result = send_payload({'key': '1'})
print(f"Press 1 again: state={result.get('state')}, display={result.get('display')}, expr={result.get('expression')}")

# Press =
result = send_payload({'key': 'equals', 'expression': '1+1'})
print(f"Press =: state={result.get('state')}, display={result.get('display')}, result={result.get('result')}, ans={result.get('ans')}")

proc.terminate()
proc.wait()
print("\nDone!")
