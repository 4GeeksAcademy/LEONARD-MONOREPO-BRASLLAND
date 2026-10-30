# Brasaland Operations Backoffice

The application menu includes the centralized incident manager, incident
analysis, and supplier directory. The manager registers incidents, displays
aggregates from `/api/incidents/summary`, filters the live list, and updates
lifecycle status with rollback and user-facing errors. Its page is available at
`/backoffice/incidents/`.

Incident analysis supports file selection and drag/drop, displays totals,
categories, statuses, satisfaction distribution, and each invalid-rule count,
and downloads the aggregate CSV. Empty, loading, success, no-score, all-invalid,
and error states are supported. A failed upload preserves the last successful
summary.

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

## Ingredient Inventory (Milestone 5)

The existing backoffice provides four authenticated views:

- `/backoffice/inventory/products`: ingredient name, SKU, category, unit and current stock at the selected restaurant, with links to receive a delivery or log consumption.
- `/backoffice/inventory/orders/inbound`: register a delivery by ingredient name, restaurant location and quantity.
- `/backoffice/inventory/orders/outbound`: log consumption or an exit, with freshly fetched location-specific stock and an excessive-quantity warning.
- `/backoffice/inventory/orders`: read-only entries and exits across all locations, including ingredient name, quantity, creation date and creator UUID.

All inventory calls live in `src/inventory-api.js` and use the existing bearer-token session helper. API errors are visible, including insufficient-stock `400` messages next to the quantity field. Quantities allow up to three decimal places. Stock indicators use the ingredient's unit at the selected restaurant: zero or below is empty, up to 10 is low, above 10 is healthy. This is a provisional UI threshold, not a reorder policy.

No `company-BRIEFING.md` was present during implementation. Labels follow the existing Brasaland API schemas and company context: ingredients, SKU, category, unit, deliveries, consumption and the 14 restaurant location codes. Confirm these labels against the missing briefing before submission.

Configure `NEXT_PUBLIC_INVENTORY_API_URL` in the existing Next.js app's ignored `uis/talent-pipeline-tracker/.env.local` to point to the inventory service (locally, `http://127.0.0.1:8012`). It defaults to `AUTH_API_URL` when omitted. Restart Next.js after changing it. The static backoffice does not load `.env.local` itself: Next.js proxies inventory requests to that URL, preserving the shared browser origin and authentication. Never put tokens in environment files. The root `.gitignore` already excludes `.env.*`, including `.env.local`.

Build with the command above, start the API with its database configuration, then run `npm --prefix uis/talent-pipeline-tracker run dev -- --hostname 0.0.0.0 --port 3001`. Open `http://localhost:3001/backoffice/inventory/products` after logging in. Inventory data requires the backend's configured SQL database; a `503` is displayed rather than replaced with demo data.

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