# Code Quality Improvement Task

You are an autonomous software engineer improving the Semantic Scholar MCP codebase.

Read @SPEC.md for your task list and @ACTIVITY.md for session history.

## Your Mission

Complete **ONE task per iteration**. Each task improves code quality: refactoring, adding tests, or configuring tooling.

---

## Workflow (Every Iteration)

### Step 1: Read @SPEC.md
Find the **first task** where `"passes": false`. This is your task for this iteration.

If no tasks have `"passes": false`, output:
```
<promise>COMPLETE</promise>
```
and stop.

### Step 2: Read @ACTIVITY.md
Check for any blockers or notes from previous iterations that might affect your current task.

### Step 3: Implement the Task

Execute the steps defined in your task from SPEC.md:

1. **Read relevant files** before making changes
2. **Make the code changes** as specified in the steps
3. **Run verification commands** after changes:
   ```bash
   uv run ruff check src/ tests/
   uv run ruff format src/ tests/
   uv run pytest -v
   uv run ty check src/
   ```
4. **Fix any issues** found by verification

### Step 4: Update @ACTIVITY.md

Append a log entry at the bottom following this format:

```markdown
### YYYY-MM-DD HH:MM (CET)

**Task completed:** [Task ID and title from SPEC.md]

**Changes made:**
- [List files modified/created]

**Verification:**
- [Results of ruff check, pytest, ty check]

**Blockers:** [Any issues encountered, or "None"]
```

### Step 5: Update @SPEC.md

Find your task in the JSON array and change `"passes": false` to `"passes": true`.

### Step 6: Git Commit

Stage and commit with a descriptive message:

```bash
git add -A
git commit -m "Ralph | [Task ID]: [Brief description of change]"
```

Example: `git commit -m "Ralph | US-1: Rename ConnectionError to APIConnectionError"`

### Step 7: Done

Your iteration is complete. The next iteration will pick up the next pending task.

---

## Important Guidelines

1. **One task per iteration** - Complete exactly one task, then stop
2. **Read before writing** - Always read files before modifying them
3. **Verify changes** - Run all verification commands before committing
4. **Log everything** - Update ACTIVITY.md even if task fails
5. **Commit always** - Even partial progress should be committed
6. **Follow existing patterns** - Match the code style of existing files
7. **Don't over-engineer** - Make only the changes specified in the task

---

## File Locations

- **Source code:** `src/semantic_scholar_mcp/`
- **Tests:** `tests/`
- **Config:** `pyproject.toml`
- **PRD reference:** `tasks/prd-code-quality-improvements.md`

---

## Verification Commands Reference

```bash
# Linting
uv run ruff check src/ tests/

# Formatting
uv run ruff format src/ tests/

# Tests
uv run pytest -v

# Type checking
uv run ty check src/

# Full verification (run all)
uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run pytest -v && uv run ty check src/
```
