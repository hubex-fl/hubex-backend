#!/usr/bin/env bash
# HUBEX Roadmap Step Completion — Auto Test Suite
# Triggered by Claude Code PostToolUse hook after git commit commands.

PROJECT_ROOT="/c/Users/lange/Documents/vs_code/projects/backend/hubex/v0.1/hubex-backend"

# Only proceed if the tool input looks like a git commit command
if ! echo "$CLAUDE_TOOL_INPUT" | grep -qE "git commit"; then
  exit 0
fi

# Check last commit message for roadmap-step patterns
LAST_MSG=$(cd "$PROJECT_ROOT" && git log -1 --pretty=%s 2>/dev/null)
if ! echo "$LAST_MSG" | grep -qiE "feat\(phase-|roadmap|step complete"; then
  exit 0
fi

echo "========================================"
echo "HUBEX Roadmap Step Detected: $LAST_MSG"
echo "Running comprehensive test suite..."
echo "========================================"

FAILED=0

# --- Backend Tests ---
echo ""
echo ">>> [1/2] Backend pytest"
cd "$PROJECT_ROOT"
if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python"
fi

$PYTHON -m pytest tests/ -x -q 2>&1
BACKEND_RC=$?
if [ $BACKEND_RC -ne 0 ]; then
  echo ">>> BACKEND TESTS FAILED (exit code $BACKEND_RC)"
  FAILED=1
else
  echo ">>> Backend tests PASSED"
fi

# --- Frontend Type-check + Build ---
echo ""
echo ">>> [2/2] Frontend type-check & build"
cd "$PROJECT_ROOT/frontend"
if [ -d "node_modules" ]; then
  npx vue-tsc --noEmit 2>&1
  TSC_RC=$?
  if [ $TSC_RC -ne 0 ]; then
    echo ">>> FRONTEND TYPE-CHECK FAILED (exit code $TSC_RC)"
    FAILED=1
  else
    echo ">>> Frontend type-check PASSED"
  fi

  npx vite build 2>&1
  BUILD_RC=$?
  if [ $BUILD_RC -ne 0 ]; then
    echo ">>> FRONTEND BUILD FAILED (exit code $BUILD_RC)"
    FAILED=1
  else
    echo ">>> Frontend build PASSED"
  fi
else
  echo ">>> Skipping frontend checks (node_modules not installed)"
fi

# --- Summary ---
echo ""
echo "========================================"
if [ $FAILED -ne 0 ]; then
  echo "RESULT: Some checks FAILED - review output above."
else
  echo "RESULT: All checks PASSED for this roadmap step."
fi
echo "========================================"

exit 0
