# Runbook: selfconnect-alt Real Win32 Integration Test

**Last Updated**: 2026-05-13
**Owner**: SelfConnect Team
**Severity**: P2 (pre-ship gate — must pass before merging to original SDK)
**Estimated Duration**: 3-5 minutes
**Review Cycle**: Quarterly

## Prerequisites
- [ ] Unit suite passes first (`sc-alt-unit-test-suite.md`)
- [ ] Windows Terminal (wt.exe) is open with at least one visible tab
- [ ] Google Chrome is open and visible (not minimized) — required for dxcam DXGI test
- [ ] Python 3.12+ with all deps: `pip install -e .[full]` plus `pip install dxcam pywin32`
- [ ] Running as normal user (NOT elevated/admin) — AttachConsole fails under elevation mismatch
- [ ] No screen saver, sleep mode, or display off — capture tests require a visible screen
- [ ] Original selfconnect SDK checked out at: `C:\Users\techai\PKA testing\selfconnect\`

## Environment Setup

### Step 1: Verify both SDKs are present (estimated: 15 sec)
```cmd
dir "C:\Users\techai\PKA testing\selfconnect\self_connect.py"
dir "C:\Users\techai\PKA testing\selfconnect-alt\self_connect.py"
```
**Expected output:** Both files found with non-zero size.
**If this fails:** Clone the missing repo before proceeding.

---

### Step 2: Verify Windows Terminal is visible (estimated: 10 sec)
```cmd
python -c "import sys; sys.path.insert(0,'C:/Users/techai/PKA testing/selfconnect-alt'); from self_connect import list_windows; wt=[w for w in list_windows() if 'windowsterminal' in w.exe_name.lower()]; print(f'WT windows: {len(wt)}')"
```
**Expected output:** `WT windows: 1` or higher.
**If output is 0:** Open Windows Terminal and try again.

---

### Step 3: Verify Chrome is visible (estimated: 10 sec)
```cmd
python -c "import sys; sys.path.insert(0,'C:/Users/techai/PKA testing/selfconnect-alt'); from self_connect import list_windows; ch=[w for w in list_windows() if 'chrome' in w.exe_name.lower()]; print(f'Chrome windows: {len(ch)}')"
```
**Expected output:** `Chrome windows: 1` or higher.
**If output is 0:** Open Chrome to any page — the test only needs a visible window.

---

## Running the Test

### Step 4: Navigate to selfconnect-alt (estimated: 5 sec)
```cmd
cd /d "C:\Users\techai\PKA testing\selfconnect-alt"
```

---

### Step 5: Run full integration test (estimated: 3-4 min)
```cmd
python real_integration_test.py 2>&1
```
**Expected output (final block):**
```
=================================================================
  FINAL RESULTS
=================================================================
  PASSED: 39
  FAILED: 0
```
Every row in the scorecard must show `PASS`.

**If FAILED > 0:**
- Note the failing label(s) from the scorecard
- See Known Failures section below for remediation

---

### Step 6: Confirm pass count exactly 39 (estimated: 5 sec)
```cmd
python real_integration_test.py 2>&1 | findstr "PASSED:"
```
**Expected output:** `  PASSED: 39`
**If PASSED is less than 39:** Environment prerequisite is missing — re-check Steps 1-3.

---

## Known Failures and Remediation

| Failure Label | Root Cause | Fix |
|---------------|-----------|-----|
| `orig.list_windows() returns windows` | WT not running | Open Windows Terminal |
| `alt get_ui_tree is faster (CacheRequest)` | comtypes gen not built | Run `python -c "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"` |
| `alt Chrome capture has real content` | Chrome minimized or off-screen | Move Chrome to foreground, not minimized |
| `WriteConsoleInput injection visible` | conhost not spawnable | Reboot clears stale console state |
| `spawn_agent_conpty(cmd.exe) succeeded` | Windows build < 17763 | Upgrade to Windows 10 1809+ |
| `SharedMemChannel median latency` | Named mmap collision | Change channel name in test or reboot |
| `_read_console_output returns text` | CREATE_NEW_CONSOLE blocked | Run as same user that owns the desktop session |

---

## Verification
1. `PASSED: 39` in final summary
2. `FAILED: 0` in final summary
3. CacheRequest speedup shows > 2x on `alt get_ui_tree is faster` line
4. SharedMemChannel latency shows < 10 microseconds

## Rollback
Read-only test — no system state is permanently modified.
The test spawns a temporary cmd.exe window and closes it automatically.

## Escalation
| Condition | Contact | Method |
|-----------|---------|--------|
| Pass count drops below 39 after fixing env | Repo owner | GitHub Issue with full output |
| New failure appears that was previously passing | Repo owner | GitHub Issue + git blame the last change |
| Test hangs > 10 minutes | Repo owner | Kill with Ctrl+C, file issue with which section hung |

## Post-Run
- [ ] If 39/39: run benchmark (`sc-alt-benchmark.md`)
- [ ] If any fail: do NOT ship the alt as production-ready
- [ ] Save the full output: `python real_integration_test.py > results_$(date +%Y%m%d).txt 2>&1`
