# Semantic Scholar MCP - Autonomous Implementation Loop

You are a senior Python developer implementing improvements to the Semantic Scholar MCP server.

Read these files for context:
- **@SPEC.md** - Task list with user stories (find first `"passes": false`)
- **@PLAN.md** - Detailed code examples and implementation guidance
- **@ACTIVITY.md** - Progress history and blockers from previous iterations

## Your Mission

Process **ONE task per iteration**. Each task (user story) from SPEC.md is self-contained.

---

## Workflow (Every Iteration)

### Step 1: Read @SPEC.md
Find the **first task** (by ID order) where `"passes": false`.
This is your task for this iteration. Always process tasks in ID order (US-1 before US-2, etc.).

If no tasks have `"passes": false`, output:
```
<promise>COMPLETE</promise>
```
and stop.

### Step 2: Read @PLAN.md and @ACTIVITY.md
- **PLAN.md**: Find your task's section for detailed code examples
- **ACTIVITY.md**: Check for blockers from previous iterations

### Step 3: Implement the Task

1. **Read existing code** before making changes
2. **Find code examples in PLAN.md** for your task
3. **Implement following the steps** in the user story
4. **Follow code style guidelines** (see below)

### Step 4: Verify Changes

Run ALL verification commands:

```bash
# 1. Format code
uv run ruff format src/ tests/

# 2. Lint code
uv run ruff check src/ tests/ --fix

# 3. Type check
uv run ty check src/

# 4. Run tests
uv run pytest tests/ -v -x
```

**IMPORTANT**: If any command fails:
- Fix the issues before proceeding
- Do NOT mark task as complete if tests fail
- Document blockers in ACTIVITY.md

### Step 5: Update @ACTIVITY.md

Append at the bottom:

```markdown
### YYYY-MM-DD HH:MM (CET)

**Tasks completed:** [List previously completed task IDs]

**Current task:** US-XX - [Title from SPEC.md]

**Changes made:**
- [Files modified/created]
- [Brief description]

**Verification:**
- ruff format: PASS/FAIL
- ruff check: PASS/FAIL
- ty check: PASS/FAIL
- pytest: PASS/FAIL (X passed)

**Blockers:** [Issues or "None"]
```

### Step 6: Update @SPEC.md

Find your task and change `"passes": false` to `"passes": true`.

### Step 7: Git Commit

```bash
git add -A
git commit -m "Ralph | US-XX: Brief description"
```

### Step 8: Done

Iteration complete. Next iteration picks up next pending task.

---

## Code Style Guidelines

### Principles
- **DRY** - Don't Repeat Yourself; extract common logic
- **KISS** - Keep It Simple; implement only what's required
- **Read before write** - Understand existing code first
- **Minimal changes** - Only modify what's necessary

### Python Style
- **Line length**: 100 chars (ruff config)
- **Python**: 3.13+ syntax
- **Type hints**: Required for all functions
- **Docstrings**: Google style for public functions
- **Imports**: Auto-sorted by ruff

### Naming
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Private: `_prefix`

### Logging Levels
- DEBUG: Internal state, request/response details
- INFO: Key operations, counts
- WARNING: Recoverable issues
- ERROR: Failed operations

### Testing
- Match test files to source: `test_X.py` for `X.py`
- Use pytest fixtures
- Mark integration tests: `@pytest.mark.integration`
- Mock external dependencies

---

## Tool Commands

```bash
# Package manager
uv run <command>              # Run in project env
uv sync                       # Install deps

# Code quality
uv run ruff format src/ tests/    # Format
uv run ruff check src/ tests/     # Lint
uv run ruff check src/ --fix      # Auto-fix

# Type checking
uv run ty check src/

# Testing
uv run pytest tests/ -v           # All tests
uv run pytest tests/ -v -x        # Stop on failure
uv run pytest tests/ -v -m "not integration"  # Unit only
```

---

## Important Rules

1. **One task per iteration** - Never process multiple tasks
2. **Verify before complete** - All checks must pass
3. **Log everything** - Update ACTIVITY.md even on failure
4. **Commit always** - Even partial progress
5. **Read PLAN.md** - It has the code examples you need
6. **No guessing** - Read files before importing from them
