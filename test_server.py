import subprocess
import os
import sys
import time
import urllib.request
import json

# Start the server in a subprocess
proc = subprocess.Popen(
    [sys.executable, 'mvp_server.py'],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
time.sleep(2)  # Wait for server to start

results = []

# Test 1: 1+1
try:
    body = json.dumps({'key': 'equals', 'expression': '1+1'}).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/key',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        result = json.loads(r.read())
    results.append(('1+1', result.get('result'), result.get('result') == '2'))
    print(f'1+1 test result: {result}')
except Exception as e:
    results.append(('1+1', 'ERROR', False))
    print(f'1+1 test error: {e}')

# Test 2: 2+3 (smoke test equivalent)
try:
    body = json.dumps({'key': 'equals', 'expression': '2+3'}).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/key',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        result = json.loads(r.read())
    results.append(('2+3', result.get('result'), result.get('result') == '5'))
    print(f'2+3 test result: {result}')
except Exception as e:
    results.append(('2+3', 'ERROR', False))
    print(f'2+3 test error: {e}')

# Terminate server
proc.terminate()
proc.wait()

print()
print('=== Results ===')
for name, result, passed in results:
    status = 'PASS' if passed else 'FAIL'
    print(f'{name}: result={result!r} [{status}]')
