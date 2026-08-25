# JARVIS Gesture HUD — Apply Protocol

## 1. Purpose

This document defines how an AI coding agent or developer SHALL apply the specification.

The goal is controlled incremental evolution.

---

# 2. Absolute rule

DO NOT rewrite the project.

DO NOT replace working architecture merely because another architecture looks cleaner.

DO NOT implement all tasks in one pass.

DO NOT skip tests.

DO NOT mark a task complete because code "looks correct".

---

# 3. Before every task

The agent MUST:

1. Read `proposal.md`.
2. Read relevant sections of `spec.md`.
3. Read relevant sections of `design.md`.
4. Read the specific task.
5. Inspect current repository code.
6. Identify existing behavior affected.
7. Identify tests affected.

---

# 4. Task execution format

For every task:

```text
READ
 ↓
INSPECT
 ↓
PLAN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
VERIFY
 ↓
REPORT
```

---

# 5. READ

The agent MUST understand:

* task objective;
* dependencies;
* acceptance criteria;
* non-goals;
* existing implementation.

---

# 6. INSPECT

Before modifying a feature, locate:

```text
current implementation
current call sites
current configuration
current tests
```

Do not assume filenames.

---

# 7. PLAN

The agent MUST produce a concise implementation plan before changing code.

Example:

```text
1. Add GestureEvent.
2. Adapt current gesture output.
3. Preserve current action mapping.
4. Add unit tests.
5. Run regression.
```

---

# 8. IMPLEMENT

Implementation MUST be minimal.

Prefer:

```text
adapter
wrapper
interface
event
```

before:

```text
rewrite
move
rename
delete
```

---

# 9. TEST

Run the smallest relevant tests first.

Then run:

```text
unit tests
integration tests
lint
type checks
application startup
```

where supported by the repository.

---

# 10. Regression

After every migration task verify the old feature.

Example TASK-007:

```text
New:
CommandBus receives click

Old:
Pinch still clicks exactly as before
```

---

# 11. Performance

Before introducing expensive processing:

Measure baseline.

After implementation:

Measure again.

Do not optimize based only on assumptions.

---

# 12. No speculative dependencies

Do not add:

* cloud services;
* AI APIs;
* databases;
* WebSockets;
* heavy frameworks;

unless required by the current task.

---

# 13. No hidden behavior

New behavior MUST be:

* configurable;
* observable;
* testable.

Avoid magic constants.

---

# 14. Configuration migration

If the project already has configuration:

DO NOT create a second conflicting configuration system.

Instead:

```text
Existing config
       ↓
adapter
       ↓
new configuration model
```

Then migrate gradually.

---

# 15. Existing gestures

Never silently change existing gesture meanings.

If a gesture needs a new meaning:

1. Add a new gesture.
2. Add a profile override.
3. Or explicitly document a breaking change.

---

# 16. Safety

The following MUST be treated as sensitive:

```text
lock workstation
shutdown
restart
close applications
delete files
execute arbitrary commands
```

Do not bind these to a single low-confidence frame.

---

# 17. Error handling

Every external operation MUST be considered fallible.

Examples:

```text
OS API
TTS
camera
HUD
filesystem
process launch
```

Errors SHALL be converted into controlled results.

---

# 18. Telemetry

Telemetry MUST NEVER become a hard dependency for normal operation.

If telemetry fails:

```text
application continues
```

---

# 19. HUD

HUD code MUST NOT become the source of truth for business logic.

The HUD displays state.

The Core owns state.

---

# 20. Gesture engine

GestureEngine MUST NOT directly execute:

```text
pyautogui
OS APIs
process launches
filesystem operations
```

It emits events/intents.

---

# 21. Context engine

ContextEngine determines context.

It MUST NOT directly execute commands.

---

# 22. Intent engine

IntentEngine resolves meaning.

It MUST NOT directly execute OS operations.

---

# 23. Command bus

CommandBus is the execution boundary.

Every migrated action SHOULD eventually pass through it.

---

# 24. Rollback

Each task SHOULD be implemented in a way that allows rollback.

Preferred approach:

```text
one task
one logical commit
```

---

# 25. Commit conventions

Use:

```text
feat(core):
feat(gesture):
feat(hud):
feat(context):
feat(profile):
feat(telemetry):
feat(command):
refactor:
test:
docs:
```

---

# 26. Agent stopping rule

After completing one requested task:

STOP.

Do not continue to the next task unless explicitly requested.

Example:

User:

```text
Implement TASK-014
```

Agent:

```text
Implement TASK-014
→ tests
→ report
→ STOP
```

---

# 27. Reporting format

After every task report:

```text
TASK:
TASK-XXX

STATUS:
DONE / BLOCKED / PARTIAL

CHANGED:
- file
- file

IMPLEMENTED:
- item
- item

TESTS:
- test
- test

REGRESSION:
PASS / FAIL

PERFORMANCE:
measurement if available

NOTES:
limitations or decisions

NEXT:
TASK-XXX+1
```

Do not automatically implement NEXT.

---

# 28. Handling conflicts

If existing code conflicts with the specification:

DO NOT guess.

Report:

```text
Conflict:
...

Current behavior:
...

Specification:
...

Recommended resolution:
...
```

Then wait for user confirmation when the decision is architectural or potentially breaking.

---

# 29. Handling missing tests

If no test exists:

1. Add a regression test where practical.
2. Then implement the task.
3. Verify behavior.

---

# 30. Handling architecture improvements

If the agent discovers a better architecture:

Do NOT silently replace the specified design.

Instead report:

```text
Proposed improvement:
...

Reason:
...

Impact:
...

Migration:
...
```

Only apply it if explicitly authorized or clearly required to make the task work without violating the specification.

---

# 31. Final validation

Before declaring a task DONE:

```text
[ ] Code compiles/runs
[ ] Relevant tests pass
[ ] Existing feature still works
[ ] No unrelated files changed
[ ] No speculative dependencies added
[ ] Error handling exists
[ ] Acceptance criteria satisfied
```

---

# 32. Full migration order

The recommended execution order is:

```text
TASK-000
   ↓
001
002
003
004
005
   ↓
006–013
   ↓
014
015
016
017
018
   ↓
019
020
021
022
   ↓
023
024
025
   ↓
026
027
028
   ↓
029
030
031
032
033
   ↓
034
035
036
037
038
   ↓
039
040
041
042
043
   ↓
044
045
046
047
   ↓
048
049
   ↓
050
051
052
053
054
```

---

# 33. Final target

The completed system SHALL converge toward:

```text
             INPUTS
                │
      ┌─────────┼─────────┐
      │         │         │
   GESTURE    VOICE    KEYBOARD
      │         │         │
      └─────────┼─────────┘
                ▼
          INPUT PROVIDERS
                │
                ▼
          INTENT ENGINE
                │
                ▼
          CONTEXT ENGINE
                │
                ▼
           COMMAND BUS
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
      OS       APPS      HUD
       │        │        │
       └────────┼────────┘
                ▼
            FEEDBACK
                │
          ┌─────┴─────┐
          ▼           ▼
         HUD         TTS
```

The system SHALL remain useful even if voice, AI, or advanced vision are disabled.

The gesture-control functionality remains a first-class feature rather than becoming merely a legacy input method.
