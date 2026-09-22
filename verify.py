import sys, re
sys.stdout.reconfigure(encoding='utf-8')
html = open('frontend.html', encoding='utf-8').read()
calls = re.findall(r'updateScrollIndicators\(([^)]+)\)', html)
print(f'Total calls: {len(calls)}')
for i, c in enumerate(calls):
    print(f'  Call {i+1}: {c}')
print()
for oid in ['scrollIndUp', 'scrollIndDown', 'scrollIndLeft', 'scrollIndRight']:
    matches = re.findall('id="' + oid + '"', html)
    print(f'LEGACY {oid}: {"STILL EXISTS" if matches else "CLEAN"}')
print()
for prefix in ['calc', 'menu', 'setup']:
    up = prefix+'ScrollIndUp' in html
    down = prefix+'ScrollIndDown' in html
    left = prefix+'ScrollIndLeft' in html
    right = prefix+'ScrollIndRight' in html
    print(f'{prefix}: up={up} down={down} left={left} right={right}')
