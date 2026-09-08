import sys
sys.path.insert(0, r'E:\A.G\casio_mvp')

from mvp_server import safe_evaluate_expression

# Test 1: simple 1 + 1
try:
    result = safe_evaluate_expression('1 + 1')
    print(f'Test 1 - 1 + 1 = {result}')
except Exception as e:
    print(f'Test 1 - ERROR: {e}')

# Test 2: with Ans
try:
    result = safe_evaluate_expression('1 + 1', ans_val=0)
    print(f'Test 2 - 1 + 1 (with ans) = {result}')
except Exception as e:
    print(f'Test 2 - ERROR: {e}')

# Test 3: with pi
try:
    result = safe_evaluate_expression('1 + pi')
    print(f'Test 3 - 1 + pi = {result}')
except Exception as e:
    print(f'Test 3 - ERROR: {e}')