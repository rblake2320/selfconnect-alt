# Runbook: selfconnect-alt vs Original Head-to-Head Benchmark

**Last Updated**: 2026-05-13
**Owner**: SelfConnect Team
**Severity**: P3 (routine) — decision gate for adopting alt as production SDK
**Estimated Duration**: 5 minutes
**Review Cycle**: Quarterly or after any major self_connect.py change

## Prerequisites
- [ ] Unit suite passes: `sc-alt-unit-test-suite.md`
- [ ] Integration test passes: `sc-alt-win32-integration-test.md`
- [ ] Both SDKs present (original + alt) — benchmark loads both in same process
- [ ] Windows Terminal open with at least one visible tab (target for benchmarks)
- [ ] Chrome open (for capture_window dxcam test)
- [ ] No other CPU-intensive processes running — benchmarks are timing-sensitive
- [ ] dxcam installed: `pip install dxcam`

## Steps

### Step 1: Navigate to selfconnect-alt (estimated: 5 sec)
```cmd
cd /d "C:\Users\techai\PKA testing\selfconnect-alt"
```

---

### Step 2: Run benchmark (estimated: 4 min)
```cmd
python bench_compare.py 2>&1
```
The benchmark runs 10 trials per operation and reports median latency.
It auto-selects a live Windows Terminal window as the test target.

**Expected output:**
```
Loading SDKs...
  Original: 0.10.0
  Alt:      0.10.0
Auto-selected target: hwnd=XXXXXXXX  title='...'
Running 10 trials per benchmark...

1/6  send_string (500 chars)...
     orig=X.XXms  alt=X.XXms  X.Xx
2/6  get_ui_tree (depth=5)...
     orig=X.XXms  alt=X.XXms  X.Xx
3/6  capture_window...
     orig=X.XXms  alt=X.XXms  X.Xx
4/6  get_text_uia...
     orig=X.XXms  alt=X.XXms  X.Xx
5/6  submit_claude_input...
     orig=X.XXms  alt=X.XXms  X.Xx
6/6  shared memory IPC roundtrip...
     alt=0.0ms  (no orig equivalent)

================================================================
  Results written to: bench_results.csv
  Operation           Orig       Alt     Speedup
  ------------------- --------   ------  -------
  get_ui_tree          51ms      19ms     2.6x
  capture_window       12ms       8ms     1.5x
  IPC roundtrip         N/A      0.0ms    N/A
================================================================
```

**If this fails with "No windows found":**
```cmd
python -c "import sys; sys.path.insert(0,'C:/Users/techai/PKA testing/selfconnect-alt'); from self_connect import list_windows; [print(w.hwnd, w.title) for w in list_windows()]"
```
Ensure a Windows Terminal window is visible and retry.

**If this fails with "SDK load error":**
```cmd
python -m py_compile self_connect.py
python -m py_compile "C:/Users/techai/PKA testing/selfconnect/self_connect.py"
```
Fix any syntax errors before retrying.

---

### Step 3: Verify key speedup targets met (estimated: 30 sec)
```cmd
python bench_compare.py 2>&1 | findstr /i "get_ui_tree\|capture_window\|IPC"
```
**Expected output (minimum acceptable):**
```
get_ui_tree (depth=5)         Xms    Yms    2.0x   <- must be >= 2.0x
capture_window                Xms    Yms    1.0x   <- must be >= 1.0x
IPC roundtrip (shared memory) N/A   0.0ms  N/A     <- must be present
```
**If get_ui_tree speedup < 2.0x:** CacheRequest may have silently fallen back to the slow path. Check for comtypes errors in the output.

**If capture_window speedup < 1.0x:** dxcam may be slower than PrintWindow on this GPU. This is acceptable — dxcam exists for GPU-composited windows where PrintWindow returns black.

---

### Step 4: Read saved CSV results (estimated: 10 sec)
```cmd
type bench_results.csv
```
**Expected output:** CSV with columns `operation,original_ms,alt_ms,speedup_factor`.
**If file missing:** The benchmark did not complete — check output from Step 2 for errors.

---

### Step 5: Archive results with datestamp (estimated: 10 sec)
```cmd
copy bench_results.csv bench_results_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%.csv
```
**Expected output:** `1 file(s) copied.`

---

## Performance Baseline (as of 2026-05-13, Windows 11, RTX 5090)

| Operation | Original (ms) | Alt (ms) | Speedup | Acceptable Regression |
|-----------|--------------|---------|---------|----------------------|
| `get_ui_tree (depth=5)` | 51 | 19 | 2.6x | >= 2.0x required |
| `capture_window` | 12 | 8 | 1.5x | >= 1.0x required |
| `get_text_uia` | 18 | 31 | 0.6x | Any (UIA path unchanged) |
| `send_string (500 chars)` | 6 | 15 | 0.4x | Any (WriteConsoleInput adds path resolution overhead) |
| `IPC roundtrip` | N/A | ~0.002 | new | Must be < 5ms |

**Note on "slower" results:**
- `send_string` alt is slower because WriteConsoleInput resolves the console PID first (psutil tree walk). This is expected — WriteConsoleInput exists to FIX Codex (which doesn't respond to WM_CHAR), not to replace WM_CHAR for speed.
- `get_text_uia` alt is slower because the CacheRequest path includes a comtypes check before falling back. UIA text extraction is not optimized in this fork.

## Verification
1. `bench_results.csv` exists and is non-empty
2. `get_ui_tree` speedup >= 2.0x
3. IPC roundtrip present with latency < 5ms
4. No `ERROR` lines in benchmark output

## Rollback
Read-only benchmark. No system state modified.

## Escalation
| Condition | Contact | Method |
|-----------|---------|--------|
| get_ui_tree speedup dropped below 2.0x | Repo owner | GitHub Issue |
| IPC latency > 10ms | Repo owner | GitHub Issue with hardware spec |
| bench_compare.py crashes | Repo owner | GitHub Issue with full traceback |

## Decision Gate
| Result | Action |
|--------|--------|
| All targets met | Alt is production-ready — merge or adopt |
| get_ui_tree < 2.0x | Investigate CacheRequest fallback before adopting |
| send_string slowdown only | Acceptable — document the tradeoff, proceed |
| Any crash | Block adoption until fixed |

## Post-Run
- [ ] Archive CSV: `bench_results_YYYY-MM-DD.csv`
- [ ] Update baseline table above if hardware changes
- [ ] If adopting alt: update `selfconnect/self_connect.py` with the winning engines
