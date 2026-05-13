"""Stress 2: UIA tree hammer — call get_ui_tree in a tight loop, compare orig vs alt"""
import sys, time, statistics
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
import importlib.util

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod; spec.loader.exec_module(mod); return mod

orig = load(r'C:\Users\techai\PKA testing\selfconnect\self_connect.py', 'sc_orig')
alt  = load(r'C:\Users\techai\PKA testing\selfconnect-alt\self_connect.py', 'sc_alt')

wins = [w for w in alt.list_windows() if 'windowsterminal' in w.exe_name.lower()]
if not wins: print("NO WT"); sys.exit(1)
hwnd = wins[0].hwnd
print(f"Hammering get_ui_tree on hwnd={hwnd} — 200 iterations each\n")

orig_t=[]; alt_t=[]
for i in range(200):
    t=time.monotonic(); orig.get_ui_tree(hwnd); orig_t.append((time.monotonic()-t)*1000)
    t=time.monotonic(); alt.get_ui_tree(hwnd);  alt_t.append((time.monotonic()-t)*1000)
    if i % 40 == 0:
        print(f"  [{i:3d}] orig_med={statistics.median(orig_t[-40:] or orig_t):.1f}ms  alt_med={statistics.median(alt_t[-40:] or alt_t):.1f}ms")

print(f"\nFINAL: orig={statistics.median(orig_t):.1f}ms  alt={statistics.median(alt_t):.1f}ms  speedup={statistics.median(orig_t)/statistics.median(alt_t):.1f}x")
print(f"orig_p99={sorted(orig_t)[int(len(orig_t)*.99)]:.1f}ms  alt_p99={sorted(alt_t)[int(len(alt_t)*.99)]:.1f}ms")
