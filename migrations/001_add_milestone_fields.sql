-- Migration: Add milestone-driven system fields
-- Date: 2024-01-27
-- Description: Adds support for document uploads, approval actions, and regeneration tracking

-- Add documents field to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS documents JSON;

-- Add action field to approvals table  
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS action VARCHAR(50) DEFAULT 'proceed';

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_approvals_action ON approvals(action);
CREATE INDEX IF NOT EXISTS idx_approvals_stage_run ON approvals(run_id, stage);

-- Add comments for documentation
COMMENT ON COLUMN projects.documents IS 'JSON array of uploaded document metadata';
COMMENT ON COLUMN approvals.action IS 'Approval action: proceed, regenerate, or reject';
