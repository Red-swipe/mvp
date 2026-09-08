import json
import subprocess
import time
import sys

sys.path.insert(0, r'E:\A.G\casio_mvp')
from mvp_server import CONTROLLER, CONTROLLER_LOCK

# Reset controller
with CONTROLLER_LOCK:
    CONTROLLER.expression = ""
    CONTROLLER.cursor_position = 0
    CONTROLLER.last_result = None
    CONTROLLER.result_displayed = False
    CONTROLLER.state = "INPUT"
    CONTROLLER.ans = "0"
    CONTROLLER.shift = False
    CONTROLLER.alpha = False

proc = subprocess.Popen([sys.executable, 'mvp_server.py', '--port', '8080'], cwd=r'E:\A.G\casio_mvp', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2)

import urllib.request

def send_payload(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request('http://127.0.0.1:8080/api/key', data=data, headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read().decode())
    except Exception as e:
        return {'error': str(e)}

# Test pressing 1
result = send_payload({'key': '1'})
print('Press 1:', result)

# Test pressing +
result = send_payload({'key': 'plus'})
print('Press +:', result)

# Test pressing 1 again
result = send_payload({'key': '1'})
print('Press 1 again:', result)

# Test pressing =
result = send_payload({'key': 'equals', 'expression': '1+1'})
print('Press =:', result)

proc.terminate()
proc.wait()