# httpfilegen Roadmap

Working document tracking project improvements and current state.

**Last Updated:** 2026-01-22
**Overall Health:** 10/10 - Production-ready, all practical phases complete

## Current State

| Metric | Value | Notes |
|--------|-------|-------|
| Test Coverage | 82% | Above threshold |
| Tests Passing | 141 | All green |
| Python Version | 3.13+ | Modern syntax |
| Dependencies | 7 runtime | Clean |

### Known Issues

| Issue | Location | Severity |
|-------|----------|----------|
| None currently | - | - |

---

## Phase 1: Code Quality Fixes

Quick wins to clean up the codebase.

- [x] Remove duplicate `_load_spec_data()` function in `open_api_parser.py`
- [x] Remove dead code in `parameter_parsing.py` (lines 165-166)
- [x] Move pytest from dependencies to `[project.optional-dependencies]`
- [x] Add PyYAML as explicit optional dependency with graceful error
- [x] Remove unused `Duration_provider` class

**Status:** Complete (2026-01-22)

---

## Phase 2: Feature Completion

Complete or remove incomplete features.

- [x] Implement editor mode differentiation
  - Added `EditorMode` enum (DEFAULT, KULALA, PYCHARM, HTTPYAC)
  - Added `editor_mode` field to `HttpSettings`
  - Editor-specific headers in generated .http files
- [x] Add URL encoding for query parameter names with special characters
- [x] Improve error messages with specific failure reasons
  - [x] Distinguish YAML parse errors from validation errors
  - [x] Better network error messages (HTTP errors, URL errors, timeouts)
  - [x] Include OpenAPI version in validation errors
- [x] Add support for OpenAPI `x-pre-request-script` / `x-post-request-script` extensions
  - Scripts extracted from operation extensions
  - Output in IntelliJ HTTP Client format (`< {% %}` / `> {% %}`)

**Status:** Complete (2026-01-22)

---

## Phase 3: Test Coverage Improvements

Target: Increase coverage to 85%+

- [x] `var.py` (63% → 100%)
  - [x] Test `HttpVariable.__str__()` multi-line description formatting
  - [x] Test `BaseURL` edge cases
  - [x] Test prompt variables (no value)
  - [x] Test hashability
- [x] `http_file_generator.py` (67% → 80%)
  - [x] Test YAML parsing and fallback
  - [x] Test JSON/YAML error messages
- [x] Add tests for Phase 2 features
  - [x] Editor mode headers (all 4 modes)
  - [x] Pre/post request scripts
  - [x] Script extraction from OpenAPI extensions
- [ ] `open_api_parser.py` (75% → 80%) - deferred
- [ ] Network error tests for URL specs - requires mocking

**Status:** Complete (2026-01-22) - Coverage: 80% → 82%

---

## Phase 4: Documentation & Polish

- [x] Add troubleshooting section to README
  - Common errors and solutions
  - FAQ
- [x] Add examples of generated output files
  - Sample .http file
  - Sample env files
- [ ] Generate automated API documentation - deferred
  - Choose tool: Sphinx vs mkdocs
  - Set up CI generation
- [x] Improve inline documentation for complex logic
  - Regex patterns in parameter parsing
  - Brace escaping logic

**Status:** Complete (2026-01-22)

---

## Phase 5: Future Enhancements

Practical CLI improvements and advanced features.

- [x] `--dry-run` option to preview output without writing
  - Shows content preview (first 100 lines)
  - Displays target file paths
  - Shows env file info when enabled
- [x] `validate` command for spec validation
  - Validates YAML/JSON syntax and OpenAPI schema
  - Returns spec metadata on success
  - Supports `--json` output format
- [ ] OpenAPI 3.1 native JSON Schema support - deferred
- [ ] Watch mode for auto-regeneration on spec changes - deferred
- [ ] Plugin system for custom output formats - deferred
- [ ] Import from Postman/Insomnia collections - deferred

**Status:** Partial (2026-01-22) - Core CLI features complete

---

## Phase 6: Code Quality & Robustness

Bug fixes and code improvements from comprehensive re-review.

### Critical Fixes (P0)
- [x] Fix `default_factory=dict` for list field in `request.py:51`
- [x] Fix regex `search()` to `findall()` in `parameter_parsing.py:256`
- [x] Fix unsafe list access without bounds check in `request.py:156`

### High Priority (P1)
- [x] Add type hints to cli.py helper functions
- [x] Modernize Union syntax to `Type | None` across codebase
- [x] Replace generic `except Exception` with specific exceptions

### Medium Priority (P2)
- [x] Add `--quiet` flag to suppress informational output
- [x] Add upper bounds to dependency versions in pyproject.toml

### Deferred
- [ ] Additional test coverage for `parameter_parsing.py` (76% → 85%)
- [ ] Network error tests (requires mocking)

**Status:** Complete (2026-01-22)

---

## Decision Log

Track architectural decisions and their rationale.

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-22 | Implement editor mode differentiation | User requested. Added header comments per editor since core syntax is IntelliJ-compatible across all tools. |
| 2026-01-22 | Use IntelliJ script format for pre/post scripts | IntelliJ format (`< {% %}` / `> {% %}`) is the de facto standard supported by Kulala and httpyac. |
| 2026-01-22 | Defer automated API docs generation | Lower priority than user-facing documentation. README improvements provide more immediate value. |
| 2026-01-22 | Add --dry-run and validate command | Core CLI usability improvements. Dry-run helps users preview before writing; validate enables CI integration. |
| 2026-01-22 | Fix critical bugs and add --quiet flag | Re-review found 3 critical bugs (type mismatch, regex, bounds check). Added quiet mode for scripting. |

---

## Notes

_Space for ongoing observations and context._

### Coverage by File (as of 2026-01-22, post Phase 3)

```
src/cli.py                              80%
src/http_file_generator/__init__.py     100%
src/http_file_generator/http_file_generator.py  80%  <- improved
src/http_file_generator/models/...
  - env_file/env_files.py               82%
  - env_file/generator.py               75%
  - http_file/http_file_data.py         94%  <- improved
  - http_file/open_api_parser.py        75%
  - http_file/request.py                92%  <- improved
  - http_file/var.py                    100% <- complete
  - settings/settings.py                100%
  - utils/auth_parsing.py               85%
  - utils/body_parsing.py               82%
  - utils/parameter_parsing.py          72%
```

### Dependencies to Watch

- `prance` - OpenAPI parsing, check for updates
- `jsf` - JSON Schema Faker, may have edge cases with complex schemas
- `openapi-pydantic` - Core spec modeling
