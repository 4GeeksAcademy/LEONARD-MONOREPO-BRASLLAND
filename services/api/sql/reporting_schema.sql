-- Reporting schema for business performance data pipeline
-- Brasaland business KPIs and pipeline execution audit trails
-- Status: Ready for Supabase SQL Editor execution

BEGIN;

-- Create reporting schema
CREATE SCHEMA IF NOT EXISTS reporting;

-- Table 1: Daily operations rollup (business KPIs by location and date)
CREATE TABLE IF NOT EXISTS reporting.daily_operations_rollup (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date date NOT NULL,
    location_id text NOT NULL,
    daily_sales_cop numeric NOT NULL DEFAULT 0,
    daily_sales_usd numeric NOT NULL DEFAULT 0,
    fulfillment_count integer NOT NULL DEFAULT 0,
    avg_fulfillment_time_hours numeric DEFAULT NULL,
    stock_breach_count integer NOT NULL DEFAULT 0,
    run_id uuid NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    CONSTRAINT unique_rollup_date_location UNIQUE (report_date, location_id)
);

-- Index for fast queries by date range and location
CREATE INDEX reporting_daily_ops_date_idx ON reporting.daily_operations_rollup (report_date DESC);
CREATE INDEX reporting_daily_ops_location_idx ON reporting.daily_operations_rollup (location_id);
CREATE INDEX reporting_daily_ops_run_id_idx ON reporting.daily_operations_rollup (run_id);

-- Table 2: Pipeline execution audit log
CREATE TABLE IF NOT EXISTS reporting.pipeline_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL UNIQUE,
    run_start_time timestamptz NOT NULL,
    run_end_time timestamptz DEFAULT NULL,
    extraction_record_count integer DEFAULT 0,
    transformation_record_count integer DEFAULT 0,
    load_record_count integer DEFAULT 0,
    status text NOT NULL CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    error_message text DEFAULT NULL,
    invalidation_trigger text DEFAULT 'scheduled' CHECK (invalidation_trigger IN ('scheduled', 'manual_trigger', 'late_event_recompute')),
    late_event_count integer DEFAULT 0,
    phase_checkpoint text DEFAULT NULL CHECK (phase_checkpoint IN ('EXTRACT_COMPLETE', 'TRANSFORM_COMPLETE', 'LOAD_COMPLETE')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Index for fast lookups by run status and time
CREATE INDEX reporting_pipeline_runs_status_idx ON reporting.pipeline_runs (status);
CREATE INDEX reporting_pipeline_runs_start_time_idx ON reporting.pipeline_runs (run_start_time DESC);
CREATE INDEX reporting_pipeline_runs_run_id_idx ON reporting.pipeline_runs (run_id);

-- Table 3: Location and product inventory snapshots
CREATE TABLE IF NOT EXISTS reporting.location_product_inventory (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id text NOT NULL,
    product_id text NOT NULL,
    quantity_on_hand numeric NOT NULL,
    quantity_critical_threshold numeric NOT NULL,
    is_critical boolean NOT NULL DEFAULT FALSE,
    snapshot_timestamp timestamptz NOT NULL,
    run_id uuid NOT NULL,
    created_at timestamptz DEFAULT now(),
    CONSTRAINT unique_inventory_snapshot UNIQUE (location_id, product_id, snapshot_timestamp)
);

-- Index for fast queries by location, criticality, and time
CREATE INDEX reporting_inventory_location_idx ON reporting.location_product_inventory (location_id);
CREATE INDEX reporting_inventory_critical_idx ON reporting.location_product_inventory (is_critical);
CREATE INDEX reporting_inventory_timestamp_idx ON reporting.location_product_inventory (snapshot_timestamp DESC);
CREATE INDEX reporting_inventory_run_id_idx ON reporting.location_product_inventory (run_id);

-- Enable RLS on all reporting tables
ALTER TABLE reporting.daily_operations_rollup ENABLE ROW LEVEL SECURITY;
ALTER TABLE reporting.pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reporting.location_product_inventory ENABLE ROW LEVEL SECURITY;

-- Set permissions: service_role can insert and select (but not update or delete)
-- Pipeline runs table is immutable; only insertion and reads allowed
REVOKE ALL ON TABLE reporting.daily_operations_rollup FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE reporting.daily_operations_rollup TO service_role;

REVOKE ALL ON TABLE reporting.pipeline_runs FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE reporting.pipeline_runs TO service_role;

REVOKE ALL ON TABLE reporting.location_product_inventory FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE reporting.location_product_inventory TO service_role;

-- Allow schema queries for verification
REVOKE ALL ON SCHEMA reporting FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA reporting TO service_role;

COMMIT;
