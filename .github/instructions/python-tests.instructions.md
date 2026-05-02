---
applyTo: "Tests/**/*.py"
description: "Use when writing or editing Python tests in Tests/. Enforce GIVEN/WHEN/THEN DDD comments, with WHEN written in passive voice, prefer the Dummy prefix for test doubles, and reuse/extend shared helpers from Tests/test_helpers.py instead of creating local Dummy/Fake classes."
---
# Python Test Conventions

For all files under `Tests/`:

- Keep DDD structure in each test using comments:
  - `# GIVEN: ...`
  - `# WHEN: ...` written in passive voice, for example `# WHEN: the object is acted upon`
  - `# THEN: ...`
  - Write GIVEN/WHEN/THEN statements to describe user-facing use cases and scenarios, not test implementation details. For example, prefer "the output directory cannot be created due to insufficient permissions" over "os.makedirs is patched to raise an OSError".
- Check `Tests/test_helpers.py` before introducing any test doubles.
- Prefer the `Dummy` prefix for test-double class names over `Fake`, `Mock`, or other alternatives.
- Reuse existing helper classes from `Tests/test_helpers.py` whenever possible.
- If needed, create a small subclass of an existing helper class instead of introducing unrelated ad-hoc classes.
- If a new helper is broadly useful, add it to `Tests/test_helpers.py` rather than defining it repeatedly in individual test files.
- Avoid local `Dummy*`, `Fake*`, and `Mock*` definitions unless no helper extension can reasonably cover the scenario.
- Place **all** auxiliary test functions, classes, and factory helpers in `Tests/test_helpers.py` instead of defining them locally inside a test module. Prefer extending or reusing an existing helper over writing a bespoke standalone function.
