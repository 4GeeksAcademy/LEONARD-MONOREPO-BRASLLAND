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
