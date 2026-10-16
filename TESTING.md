# AUTH-088 Test Plan

Tests call endpoint functions and helpers directly with isolated in-memory TinyDB
storage. They assert account mutations, credentials, authorization, and token
lifecycle decisions, not HTTP serialization or framework routing.

## Planned Cases (Recorded Before Tests)

| Endpoint | Happy path | Edge case | Failure mode |
| --- | --- | --- | --- |
| POST /users | Create user and profile; hash password | Case-insensitive duplicate email; empty password; UTF-8 byte limit | Reject duplicate account and privileged registration |
| POST /auth/login | Issue signed token with subject and expiry | Mixed-case email; empty or oversized password | Wrong credentials, unknown or inactive user |
| GET /auth/me | Return current account and profile | Empty profile fields | Missing profile or invalid authentication |
| POST /auth/forgot-password | Store hashed reset token and queue email | Replace previous token; unknown address stays private | Delivery failure removes unusable token |
| POST /auth/reset-password | Change password and consume token | Expired token; replay; malformed expiry | Unknown token or deleted account |
| POST /auth/change-password | Change password and invalidate reset links | Reuse same password; empty new password | Incorrect current password leaves credentials unchanged |
| GET /users | Admin lists users | Empty database | Non-admin rejected |
| GET /users/{id} | Owner reads account | Admin reads another account | Non-owner or missing account rejected |
| PUT /users/{id} | Owner updates email/password | Empty update; normalized email | Role escalation, duplicate email, non-owner rejected |
| DELETE /users/{id} | Owner removes account and profile | Admin removes another account | Non-owner or missing account rejected |
| GET /profiles/me | Read own profile | Blank profile | Missing profile rejected |
| PUT /profiles/me | Update own profile | Empty update preserves fields | Missing profile rejected |

### JWT And Validation Helpers

Accept valid JWTs; reject expired, malformed, missing, incorrectly signed tokens,
missing required claims, mismatched identities, deleted users, and inactive users.
Validate password character and UTF-8 byte boundaries.

AI-assisted case selection identified UTF-8 passwords that satisfy a character
limit but exceed bcrypt's 72-byte limit, token replay, and identity-claim mismatch
as important cases beyond the basic happy paths.

### TypeScript Session Utilities

Test token retrieval, logout cleanup, authenticated/public requests, missing and
expired sessions, network failures, safe API error messages and field mapping,
empty responses, and unreadable responses. Mock storage, navigation, and fetch;
never contact a live service.

## Running

Requirements: Python 3.11 or newer, uv, and Node.js 22 or newer with npm.
Run these commands from the repository root:

```sh
uv sync --locked
uv run pytest
uv run pytest --cov
npm --prefix packages/shared ci
npm test -- --coverage
```

Run the TypeScript suite separately:

```sh
cd packages/shared
npm test -- --coverage
```

Run one Python endpoint suite during development:

```sh
uv run pytest services/api/tests/unit/test_login.py -q
```

Root pytest discovery targets `services/api/tests/unit/`. Modules cover
registration, login, JWT authentication, forgot/reset/change password, account
authorization/CRUD, and profiles/current account. Each endpoint has happy-path,
edge-case, and rejection/failure checks. Dependencies are passed directly;
async login is called with `asyncio.run` and a request double.

The shared package's `__tests__/session.test.ts` tests `getToken`, `endSession`,
`sessionFetch`, `apiRequest`, and `ApiError`. Jest runs in Node with mocked
browser globals and fetch; no browser or dev server is necessary.

## Coverage Results

Verified on 2026-10-16 with Python 3.14.2 and Node.js 24.21.0:

| Suite | Tests | Measured coverage | Enforced minimum |
| --- | --- | --- | --- |
| Python authentication business logic | 85 passed | 91.35% statements in `services/api/auth.py` | 70% statements |
| TypeScript shared auth/session utilities | 28 passed | 100% statements, branches, functions, lines | 90% in each metric |

Coverage intentionally measures the production authentication modules, not test
code or unrelated monorepo projects. Coverage artifacts and installed dependencies
are ignored; dependency lockfiles are included for reproducibility.

No production logic changes were required by the tested cases. The expired JWT
regression check confirms that a correctly signed token with a past expiration is
rejected. Password reset replay is rejected after successful use, and a delivery
failure removes the unusable reset link. Database tests never open the real auth
database, and mocked email delivery never contacts Resend. Credentials and JWT
signing secrets in fixtures are test-only values.

## Scope And Existing Suites

Existing HTTP integration suites in `services/api/tests/` are preserved but are
not part of default unit-test discovery. They exercise framework routing and may
require separate authentication/environment setup. This milestone does not count
them toward its business-logic coverage. Optional API-042 backoffice and FE-019
Next.js utility suites were not added; the Jest suite above covers the existing
shared TypeScript authentication utilities, not the separate Next.js application.