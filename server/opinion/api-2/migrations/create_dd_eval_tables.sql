-- Migration: Create DD Evaluation Tables
-- Date: 2026-02-02
-- Description: Creates tables for DD evaluation testing system

-- Create dd_eval_rubric table
CREATE TABLE IF NOT EXISTS dd_eval_rubric (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    rubric_data JSONB NOT NULL,
    total_points INTEGER DEFAULT 200,
    dd_id UUID REFERENCES due_diligence(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);

-- Create index on dd_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_dd_eval_rubric_dd_id ON dd_eval_rubric(dd_id);

-- Create dd_evaluation table
CREATE TABLE IF NOT EXISTS dd_evaluation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rubric_id UUID NOT NULL REFERENCES dd_eval_rubric(id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    scores JSONB,
    total_score INTEGER,
    percentage FLOAT,
    performance_band VARCHAR(20),
    evaluation_model VARCHAR(100) DEFAULT 'claude-opus-4-20250514',
    raw_response TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_dd_evaluation_rubric_id ON dd_evaluation(rubric_id);
CREATE INDEX IF NOT EXISTS idx_dd_evaluation_run_id ON dd_evaluation(run_id);
CREATE INDEX IF NOT EXISTS idx_dd_evaluation_status ON dd_evaluation(status);

-- Add comments for documentation
COMMENT ON TABLE dd_eval_rubric IS 'Stores evaluation rubrics for DD quality testing against known answer sets';
COMMENT ON TABLE dd_evaluation IS 'Stores evaluation results comparing DD analysis runs against rubrics';
