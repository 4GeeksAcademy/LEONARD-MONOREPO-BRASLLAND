# Supabase Telemetry Storage Setup

## 1. Create the table

Open your Supabase project, select **SQL Editor**, and create a new query.
Paste the following script and run it once as the database owner.

The source script is
[`services/api/sql/telemetry_events.sql`](../../services/api/sql/telemetry_events.sql).
If the table already exists, stop and inspect its schema rather than deleting it
or ignoring the error.

```sql
BEGIN;

CREATE TABLE public.telemetry_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp timestamptz NOT NULL,
    service text NOT NULL,
    event_type text NOT NULL,
    level text DEFAULT 'info',
    value numeric,
    message text,
    tags jsonb DEFAULT '{}'::jsonb
);

CREATE INDEX telemetry_events_timestamp_idx
    ON public.telemetry_events (timestamp);
CREATE INDEX telemetry_events_event_type_idx
    ON public.telemetry_events (event_type);
CREATE INDEX telemetry_events_tags_gin_idx
    ON public.telemetry_events USING gin (tags);

ALTER TABLE public.telemetry_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.telemetry_events
    FROM PUBLIC, anon, authenticated, service_role;
GRANT INSERT, SELECT ON TABLE public.telemetry_events TO service_role;

COMMIT;
```

The transaction creates the table, indexes, and permissions together. If a
statement fails, the transaction does not commit any of those changes.

## 2. Verify the structure

Run these queries in the SQL Editor:

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'telemetry_events'
ORDER BY ordinal_position;

SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'telemetry_events';

SELECT relrowsecurity
FROM pg_class
WHERE oid = 'public.telemetry_events'::regclass;

SELECT grantee, privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND table_name = 'telemetry_events'
  AND grantee IN ('PUBLIC', 'anon', 'authenticated', 'service_role')
ORDER BY grantee, privilege_type;
```

Expected results:

- Eight columns: `id`, `timestamp`, `service`, `event_type`, `level`, `value`,
  `message`, and `tags`.
- Four indexes: the primary-key index, two B-tree indexes on `timestamp` and
  `event_type`, and a GIN index on `tags`.
- `relrowsecurity` is `true`.
- Only `INSERT` and `SELECT` grants for `service_role`; no grants for `PUBLIC`,
  `anon`, or `authenticated`.

## 3. Backend access

The existing backend connects directly to Postgres using
`SUPABASE_DATABASE_URL` or the `SUPABASE_DB_*` settings described in the
[backend README](../../services/api/README.md#inventory-database).
Keep these credentials server-side; do not put them in frontend code or
`NEXT_PUBLIC_*` variables.

The connection must use the table owner or a server-only role with insert
permission. A non-owner role without `BYPASSRLS` also needs an explicit INSERT
policy; a table grant alone does not bypass RLS.

Browser roles cannot access this table directly. `service_role` can insert and
read events but cannot update, delete, or truncate them. The application treats
events as immutable; database owners retain administrative privileges.

The backend validates events against `event-schemas.json` and inserts each batch
using the existing server-side Postgres connection. It stores `eventId` as `id`
so retried batches do not create duplicates; event properties are stored at the
top level of `tags`, with `sessionId`, `userId`, `requestId`, and `schemaVersion`
under `tags._telemetry`. The `service` is `backoffice`; `level` comes from
`severity` or defaults to `info`. The optional `value` and `message` columns use
matching event properties when present.

## 4. Inspect stored events

After the persistent endpoint is implemented and receives events, run:

```sql
SELECT id, timestamp, service, event_type, level, value, message, tags
FROM public.telemetry_events
ORDER BY timestamp DESC
LIMIT 20;
```

Confirm that business and technical events appear, timestamps are correct, and
top-level `tags` contains only permitted event properties, including the
relevant location dimensions from the [telemetry plan](telemetry-plan.md).
