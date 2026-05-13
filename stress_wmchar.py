"""Stress 1: WM_CHAR flood — inject 1000 keystrokes/sec into a live WT window"""
import sys, time
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows, send_string

wins = [w for w in list_windows() if 'windowsterminal' in w.exe_name.lower()]
if not wins: print("NO WT WINDOW FOUND"); sys.exit(1)
target = wins[0]
print(f"Target: hwnd={target.hwnd} title={target.title!r}")

count = 0; errors = 0; t0 = time.monotonic()
for i in range(500):
    try:
        send_string(target, f"echo SC_STRESS_{i}\r", mode="turbo")
        count += 1
    except Exception as e:
        errors += 1
    if i % 50 == 0:
        elapsed = time.monotonic() - t0
        rate = count / elapsed if elapsed > 0 else 0
        print(f"  [{i:4d}] sent={count}  errors={errors}  rate={rate:.0f}/s  elapsed={elapsed:.1f}s")

elapsed = time.monotonic() - t0
print(f"\nDONE: {count} injections, {errors} errors, {count/elapsed:.0f}/s avg over {elapsed:.1f}s")
