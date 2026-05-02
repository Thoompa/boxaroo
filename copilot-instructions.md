# Boxaroo Agent Instructions

## Import Organization

All imports must occur at the top of a file, even if a module is only used in one location. Do not add imports inline within functions or conditional blocks. This applies to all Python files (production code, tests, and utilities).

**Rationale:** Keeping all imports at the top of files:
- Improves code readability and maintainability
- Makes dependencies immediately visible
- Follows PEP 8 conventions
- Simplifies static analysis and dependency tracking
