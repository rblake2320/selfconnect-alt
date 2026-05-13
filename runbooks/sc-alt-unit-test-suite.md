# Runbook: selfconnect-alt Unit Test Suite

**Last Updated**: 2026-05-13
**Owner**: SelfConnect Team
**Severity**: P3 (routine verification) / P2 (pre-merge gate)
**Estimated Duration**: 3 minutes
**Review Cycle**: Quarterly

## Prerequisites
- [ ] Python 3.12+ installed: `python --version`
- [ ] selfconnect-alt repo checked out: `C:\Users\techai\PKA testing\selfconnect-alt\`
- [ ] Dependencies installed: `pip install -e .[full]`
- [ ] pytest installed: `python -m pytest --version`
- [ ] No other test run currently executing in the same directory

## Steps

### Step 1: Navigate to repo root (estimated: 10 sec)
```cmd
cd /d "C:\Users\techai\PKA testing\selfconnect-alt"
```
**Expected output:** Prompt changes to `C:\Users\techai\PKA testing\selfconnect-alt>`
**If this fails:** Check the directory exists — repo may need to be cloned first.

---

### Step 2: Confirm test discovery (estimated: 10 sec)
```cmd
python -m pytest tests/ --collect-only --ignore=tests/test_antigravity_controller.py -q 2>&1 | findstr "test session"
```
**Expected output:**
```
========= test session starts =========
```
and a line showing `170 tests` collected.

**If this fails:** A test file has a syntax error or import is broken. Run `python -m py_compile tests/<failing>.py` to identify.

---

### Step 3: Run full unit suite (estimated: 2 min)
```cmd
python -m pytest tests/ -v --ignore=tests/test_antigravity_controller.py --tb=short 2>&1
```
**Expected output (final lines):**
```
============================================================
170 passed, 3 warnings in 1.xx s
============================================================
```
All individual test lines must show `PASSED`. No `FAILED` or `ERROR` lines.

**If this fails:**
- Note the exact failing test name(s)
- Run isolated: `python -m pytest tests/<file>.py::TestClass::test_name -v`
- Check if a Win32 API import is missing (install `pywin32`, `comtypes`)
- Check if `self_connect.py` has a syntax error: `python -m py_compile self_connect.py`

---

### Step 4: Confirm zero failures (estimated: 5 sec)
```cmd
python -m pytest tests/ -q --ignore=tests/test_antigravity_controller.py 2>&1 | findstr "passed"
```
**Expected output:**
```
170 passed, 3 warnings in 1.xxs
```
**If output shows any `failed`:** Do NOT merge or ship. Fix failures before proceeding.

---

## Verification
1. Final pytest summary line shows `170 passed` with zero `failed`
2. Only known acceptable warnings: FastAPI `on_event` deprecation, pywinauto STA threading mode
3. No `ERROR` lines anywhere in output

## Rollback
This is a read-only test run. No rollback required.
If tests broke something unexpectedly: `git stash` to revert uncommitted changes.

## Escalation
| Condition | Contact | Method |
|-----------|---------|--------|
| Persistent import error after dependency reinstall | Repo owner | GitHub Issue |
| Test count drops below 170 | Repo owner | Direct message |
| New `ERROR` (not `FAILED`) appears | SelfConnect Team | Slack / GitHub Issue |

## Post-Run
- [ ] If all pass: proceed to `sc-alt-win32-integration-test.md`
- [ ] If any fail: file a GitHub issue with the exact error and failing test name
- [ ] Note the wall-clock time — should be under 5 seconds total
