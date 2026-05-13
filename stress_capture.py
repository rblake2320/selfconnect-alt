"""Stress 4: capture_window loop — 100 captures, check none are black, measure fps"""
import sys, time, statistics
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows, capture_window

wins = [w for w in list_windows() if 'windowsterminal' in w.exe_name.lower()]
if not wins: print("NO WT"); sys.exit(1)
hwnd = wins[0].hwnd
print(f"Capture stress: 100 frames from hwnd={hwnd}\n")

times=[]; blacks=0; sizes=set()
for i in range(100):
    t = time.monotonic()
    img = capture_window(hwnd)
    elapsed = (time.monotonic()-t)*1000
    times.append(elapsed)
    if img:
        sizes.add(img.size)
        hist = img.convert('L').histogram()
        non_zero = sum(1 for v in hist if v > 0)
        if non_zero < 5: blacks += 1
    else:
        blacks += 1
    if i % 20 == 0:
        print(f"  [{i:3d}] {elapsed:.1f}ms  black={blacks}  sizes={sizes}")

print(f"\nDONE: 100 captures")
print(f"  median={statistics.median(times):.1f}ms")
print(f"  p99   ={sorted(times)[98]:.1f}ms")
print(f"  black_frames={blacks}/100")
print(f"  sizes={sizes}")
print("PASS" if blacks == 0 else f"WARN: {blacks} black frames")
