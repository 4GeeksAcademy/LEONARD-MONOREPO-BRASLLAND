# Brasaland Operations Backoffice

Incident analysis is the initial application-menu view. The browser supports
file selection and drag/drop, displays totals, categories, statuses,
satisfaction distribution, and each invalid-rule count, and downloads the
aggregate CSV. Empty, loading, success, no-score, all-invalid, and error states
are supported. A failed upload preserves the last successful summary.

## Build and Run

```bash
npm --prefix uis/backoffice ci
npm --prefix uis/backoffice run build
```

Then run the [FastAPI service](../../services/api/README.md) and the existing
[Next.js application](../talent-pipeline-tracker/README.md). Register or log in at
`http://localhost:3001/login`, then open `http://localhost:3001/backoffice/`.
Next.js proxies the static assets and API calls onto one browser origin so the
backoffice shares its stored JWT with the tracker and profile views. Do not open
the backoffice directly on the API port or through a file/static-server URL.
Generated JavaScript/font bundles are ignored by Git and must be built before serving.

Both incident analysis and the supplier directory validate the stored session
before rendering. Uploads, downloads, and supplier requests attach the latest
bearer token; protected `401` responses and logout clear storage and redirect to
the integrated Next.js login page. No separate auth application is used.

The interface uses bundled Lucide icons, DM Sans and Space Grotesk fonts, and
a local food photograph. No CDN requests, analytics, or external AI calls occur
at runtime. The photograph is decorative restaurant-food imagery, not a claim
to depict an actual Brasaland location; source:
https://images.unsplash.com/photo-1555939594-58d7cb561ad1

## Browser Verification

Install Chromium with `npm --prefix uis/backoffice exec -- playwright install chromium`.
If browser runtime libraries are missing, install the dependencies recommended
by Playwright using your environment's approved process before testing.

```bash
npm --prefix uis/talent-pipeline-tracker test
```

The AUTH-02 suite starts isolated API/Next.js servers on ports 8013/3011 and
verifies real login, profiles, protected routes, incident upload/export, supplier
loading, and session cleanup. See the Next.js README for setup and screenshots.

The original `npm --prefix uis/backoffice test` suite still assumes anonymous
API access and requires migration before it can be used as a gate. Its pre-auth
coverage included desktop/mobile uploads, metrics and CSV download, drag/drop,
clean validation, malformed and empty files, all-invalid/no-score results,
local assets/fonts/icons, runtime errors, and layout overflow. Tests capture
the script and web screenshots in [docs/incident-analysis](../../docs/incident-analysis/README.md).

Generate the synthetic demo CSV first if it is absent:

```bash
python scripts/generate_incident_demo.py
```