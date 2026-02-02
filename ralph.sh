#!/bin/bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Configuration
PROMPT_FILE="ralph/PROMPT.md"
PLAN_FILE="ralph/PLAN.md"
SETTINGS_FILE=".claude/settings.local.json"

usage() {
  echo "Usage: $0 <iterations>"
  echo ""
  echo "Runs Claude autonomously to complete tasks defined in PLAN.md."
  echo "Each iteration completes one task until all are done or max iterations reached."
  echo ""
  echo "Prerequisites:"
  echo "  - claude CLI installed and in PATH"
  echo "  - jq installed (for context usage display)"
  echo "  - $PROMPT_FILE in current directory"
  echo "  - $PLAN_FILE with task definitions"
  echo "  - $SETTINGS_FILE with required permissions (recommended)"
  exit 1
}

# Format seconds to human readable
format_duration() {
  local seconds=$1
  if [ "$seconds" -lt 60 ]; then
    echo "${seconds}s"
  else
    local minutes=$((seconds / 60))
    local remaining_seconds=$((seconds % 60))
    echo "${minutes}m ${remaining_seconds}s"
  fi
}

# Get current timestamp
timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

# Require iteration count
if [ -z "${1:-}" ]; then
  usage
fi

# Validate iteration count is a positive integer
if ! [[ "$1" =~ ^[0-9]+$ ]] || [ "$1" -lt 1 ]; then
  echo -e "${RED}Error: iterations must be a positive integer${NC}"
  exit 1
fi

ITERATIONS=$1

# Check for claude CLI
if ! command -v claude &> /dev/null; then
  echo -e "${RED}Error: claude CLI not found in PATH${NC}"
  echo "Install it from: https://claude.ai/code"
  exit 1
fi

# Check for jq (optional but recommended)
if ! command -v jq &> /dev/null; then
  echo -e "${YELLOW}Warning: jq not found - context usage display will be unavailable${NC}"
  echo -e "${YELLOW}Install jq for token usage statistics: brew install jq${NC}"
  echo ""
fi

# Check for PROMPT.md
if [ ! -f "$PROMPT_FILE" ]; then
  echo -e "${RED}Error: $PROMPT_FILE not found in current directory${NC}"
  exit 1
fi

# Check for PLAN.md and count incomplete tasks
if [ ! -f "$PLAN_FILE" ]; then
  echo -e "${YELLOW}Warning: $PLAN_FILE not found - cannot verify task count${NC}"
  INCOMPLETE_TASKS=0
else
  # Count tasks where "passes": false
  INCOMPLETE_TASKS=$(grep -c '"passes": false' "$PLAN_FILE" 2>/dev/null || echo "0")

  if [ "$INCOMPLETE_TASKS" -gt 0 ] && [ "$ITERATIONS" -lt "$INCOMPLETE_TASKS" ]; then
    echo -e "${YELLOW}Warning: $INCOMPLETE_TASKS incomplete task(s) in $PLAN_FILE, but only $ITERATIONS iteration(s) requested${NC}"
    echo -e "${YELLOW}Not all tasks will be completed.${NC}"
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi
fi

# Warn if settings file is missing (permissions may block autonomous execution)
if [ ! -f "$SETTINGS_FILE" ]; then
  echo -e "${YELLOW}Warning: $SETTINGS_FILE not found${NC}"
  echo -e "${YELLOW}Claude may prompt for permissions and block autonomous execution.${NC}"
  echo -e "${YELLOW}Consider creating $SETTINGS_FILE with required permissions.${NC}"
  echo ""
  read -p "Continue anyway? [y/N] " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

echo -e "${BOLD}Starting Ralph autonomous agent${NC}"
echo "════════════════════════════════════════════════════════════════"
echo -e "  ${CYAN}Started:${NC}          $(timestamp)"
echo -e "  ${CYAN}Max iterations:${NC}   $ITERATIONS"
echo -e "  ${CYAN}Incomplete tasks:${NC} $INCOMPLETE_TASKS"
echo -e "  ${CYAN}Prompt file:${NC}      $PROMPT_FILE"
echo -e "  ${CYAN}Plan file:${NC}        $PLAN_FILE"
echo "════════════════════════════════════════════════════════════════"
echo ""

TOTAL_START_TIME=$(date +%s)
COMPLETED_ITERATIONS=0

for ((i=1; i<=ITERATIONS; i++)); do
  ITER_START_TIME=$(date +%s)

  echo -e "${BOLD}${GREEN}▶ Iteration $i of $ITERATIONS${NC}"
  echo -e "${DIM}────────────────────────────────────────────────────────────────${NC}"
  echo -e "  ${BLUE}Started:${NC} $(timestamp)"

  # Show current incomplete task count
  if [ -f "$PLAN_FILE" ]; then
    CURRENT_INCOMPLETE=$(grep -c '"passes": false' "$PLAN_FILE" 2>/dev/null || echo "0")
    echo -e "  ${BLUE}Remaining tasks:${NC} $CURRENT_INCOMPLETE"
  fi
  echo ""

  # Run Claude with permission skip for autonomous operation
  set +e
  result_json=$(claude -p "$(cat "$PROMPT_FILE")" --output-format json --dangerously-skip-permissions 2>&1)
  exit_code=$?
  set -e

  # Parse JSON output to extract result and usage
  if command -v jq &> /dev/null && echo "$result_json" | jq -e . &> /dev/null; then
    result=$(echo "$result_json" | jq -r '.result // empty')
    INPUT_TOKENS=$(echo "$result_json" | jq -r '.input_tokens // 0')
    OUTPUT_TOKENS=$(echo "$result_json" | jq -r '.output_tokens // 0')
    TOTAL_TOKENS=$((INPUT_TOKENS + OUTPUT_TOKENS))
  else
    # Fallback if not valid JSON (e.g., error message)
    result="$result_json"
    INPUT_TOKENS=0
    OUTPUT_TOKENS=0
    TOTAL_TOKENS=0
  fi

  ITER_END_TIME=$(date +%s)
  ITER_DURATION=$((ITER_END_TIME - ITER_START_TIME))

  # Calculate response stats
  RESPONSE_LINES=$(echo "$result" | wc -l | tr -d ' ')
  RESPONSE_CHARS=$(echo "$result" | wc -c | tr -d ' ')

  echo -e "${DIM}─── Claude Response ───${NC}"
  echo "$result"
  echo -e "${DIM}─── End Response ───${NC}"
  echo ""

  # Iteration summary
  echo -e "  ${BLUE}Finished:${NC} $(timestamp)"
  echo -e "  ${BLUE}Duration:${NC} $(format_duration $ITER_DURATION)"
  echo -e "  ${BLUE}Response:${NC} $RESPONSE_LINES lines, $RESPONSE_CHARS chars"
  echo -e "  ${BLUE}Exit code:${NC} $exit_code"

  # Context usage display
  if [ "$TOTAL_TOKENS" -gt 0 ]; then
    echo ""
    echo -e "  ${BOLD}Context Usage${NC}"

    # Calculate percentages (assuming 200k context window)
    CONTEXT_WINDOW=200000
    USAGE_PERCENT=$((TOTAL_TOKENS * 100 / CONTEXT_WINDOW))
    INPUT_PERCENT=$((INPUT_TOKENS * 100 / CONTEXT_WINDOW))
    OUTPUT_PERCENT=$((OUTPUT_TOKENS * 100 / CONTEXT_WINDOW))

    # Format token counts (k notation for thousands)
    if [ "$INPUT_TOKENS" -ge 1000 ]; then
      INPUT_DISPLAY="$((INPUT_TOKENS / 1000)).$((INPUT_TOKENS % 1000 / 100))k"
    else
      INPUT_DISPLAY="$INPUT_TOKENS"
    fi
    if [ "$OUTPUT_TOKENS" -ge 1000 ]; then
      OUTPUT_DISPLAY="$((OUTPUT_TOKENS / 1000)).$((OUTPUT_TOKENS % 1000 / 100))k"
    else
      OUTPUT_DISPLAY="$OUTPUT_TOKENS"
    fi
    if [ "$TOTAL_TOKENS" -ge 1000 ]; then
      TOTAL_DISPLAY="$((TOTAL_TOKENS / 1000)).$((TOTAL_TOKENS % 1000 / 100))k"
    else
      TOTAL_DISPLAY="$TOTAL_TOKENS"
    fi

    # Build visual bar (10 segments)
    FILLED_SEGMENTS=$((USAGE_PERCENT / 10))
    if [ "$FILLED_SEGMENTS" -gt 10 ]; then FILLED_SEGMENTS=10; fi
    EMPTY_SEGMENTS=$((10 - FILLED_SEGMENTS))

    BAR=""
    for ((s=0; s<FILLED_SEGMENTS; s++)); do BAR+="⛁ "; done
    for ((s=0; s<EMPTY_SEGMENTS; s++)); do BAR+="⛶ "; done

    echo -e "  ${DIM}$BAR${NC}  ${TOTAL_DISPLAY}/200k tokens (${USAGE_PERCENT}%)"
    echo -e "  ${DIM}⛁${NC} Input:  ${INPUT_DISPLAY} tokens (${INPUT_PERCENT}%)"
    echo -e "  ${DIM}⛁${NC} Output: ${OUTPUT_DISPLAY} tokens (${OUTPUT_PERCENT}%)"
  fi

  # Check for completion signal
  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    COMPLETED_ITERATIONS=$i
    TOTAL_END_TIME=$(date +%s)
    TOTAL_DURATION=$((TOTAL_END_TIME - TOTAL_START_TIME))

    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}✓ ALL TASKS COMPLETE${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "  ${CYAN}Finished:${NC}    $(timestamp)"
    echo -e "  ${CYAN}Iterations:${NC}  $i of $ITERATIONS"
    echo -e "  ${CYAN}Total time:${NC}  $(format_duration $TOTAL_DURATION)"
    exit 0
  fi

  # Warn if Claude exited with error
  if [ $exit_code -ne 0 ]; then
    echo -e "  ${YELLOW}⚠ Warning: Claude exited with non-zero code${NC}"
  fi

  # Check if task was likely completed (look for commit message in output)
  if [[ "$result" == *"git commit"* ]] || [[ "$result" == *"[ankapetanovic-refactoring"* ]]; then
    echo -e "  ${GREEN}✓ Task appears to have been committed${NC}"
  fi

  COMPLETED_ITERATIONS=$i

  echo ""
  echo -e "${DIM}════════════════════════════════════════════════════════════════${NC}"
  echo ""

  # Small delay between iterations to avoid rate limiting
  if [ $i -lt $ITERATIONS ]; then
    echo -e "${DIM}Waiting 1s before next iteration...${NC}"
    sleep 1
    echo ""
  fi
done

TOTAL_END_TIME=$(date +%s)
TOTAL_DURATION=$((TOTAL_END_TIME - TOTAL_START_TIME))

# Final status
if [ -f "$PLAN_FILE" ]; then
  FINAL_INCOMPLETE=$(grep -c '"passes": false' "$PLAN_FILE" 2>/dev/null || echo "0")
  TASKS_COMPLETED=$((INCOMPLETE_TASKS - FINAL_INCOMPLETE))
else
  FINAL_INCOMPLETE="?"
  TASKS_COMPLETED="?"
fi

echo -e "${BOLD}${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${YELLOW}⚠ REACHED MAX ITERATIONS${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo -e "  ${CYAN}Finished:${NC}         $(timestamp)"
echo -e "  ${CYAN}Iterations run:${NC}   $COMPLETED_ITERATIONS of $ITERATIONS"
echo -e "  ${CYAN}Total time:${NC}       $(format_duration $TOTAL_DURATION)"
echo -e "  ${CYAN}Tasks completed:${NC}  $TASKS_COMPLETED"
echo -e "  ${CYAN}Tasks remaining:${NC}  $FINAL_INCOMPLETE"
echo ""
echo -e "Run ${BOLD}./ralph.sh $FINAL_INCOMPLETE${NC} to complete remaining tasks."
exit 1
