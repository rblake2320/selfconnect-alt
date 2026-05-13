"""Stress 3: SharedMemChannel IPC — 10,000 roundtrips, measure latency distribution"""
import sys, time, statistics
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import SharedMemChannel

ch_w = SharedMemChannel("SC_STRESS_IPC_001", size=65536)
ch_r = SharedMemChannel("SC_STRESS_IPC_001", size=65536)

N = 10000; latencies = []
payloads = [b"X"*sz for sz in [8,64,512,4096]]
print(f"IPC stress: {N} roundtrips across 4 payload sizes\n")

for i in range(N):
    payload = payloads[i % len(payloads)]
    t = time.monotonic()
    ch_w.send(payload)
    data = ch_r.recv(timeout=1.0)
    latencies.append((time.monotonic()-t)*1e6)
    if i % 2000 == 0 and i > 0:
        window = latencies[-2000:]
        print(f"  [{i:5d}] med={statistics.median(window):.2f}us  p99={sorted(window)[int(len(window)*.99)]:.2f}us  max={max(window):.2f}us")

ch_w.close(); ch_r.close()
print(f"\nDONE {N} roundtrips")
print(f"  median={statistics.median(latencies):.2f}us")
print(f"  p95   ={sorted(latencies)[int(N*.95)]:.2f}us")
print(f"  p99   ={sorted(latencies)[int(N*.99)]:.2f}us")
print(f"  max   ={max(latencies):.2f}us")
