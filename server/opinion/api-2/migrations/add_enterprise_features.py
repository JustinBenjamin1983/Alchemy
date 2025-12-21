"""
Migration: Add Enterprise Features tables (Phase 7)

Creates tables for:
- Users (minimal for collaboration features)
- Audit logging
- Finding assignments and comments
- Review workflows
- Report templates
- Export jobs

Run this script to create the tables:
    python migrations/add_enterprise_features.py

Rollback:
    python migrations/add_enterprise_features.py --rollback
"""
import os
import sys
import json

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Load environment from local.settings.json
settings_path = os.path.join(parent_dir, "local.settings.json")
if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
        for key, value in settings.get("Values", {}).items():
            if key not in os.environ:
                os.environ[key] = value

from shared.session import engine
from sqlalchemy import text


def run_migration():
    """Create enterprise feature tables."""

    # ============================================
    # USERS TABLE (minimal for collaboration)
    # ============================================
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) NOT NULL UNIQUE,
        name VARCHAR(255),
        role VARCHAR(50) DEFAULT 'member',  -- admin, partner, senior_associate, associate, member
        avatar_url TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        last_login_at TIMESTAMP WITH TIME ZONE
    );

    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    """

    # ============================================
    # AUDIT LOGGING
    # ============================================
    create_audit_log_table = """
    CREATE TABLE IF NOT EXISTS dd_audit_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_type VARCHAR(100) NOT NULL,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        entity_type VARCHAR(50) NOT NULL,  -- dd, document, finding, report
        entity_id UUID NOT NULL,
        dd_id UUID REFERENCES due_diligence(id) ON DELETE CASCADE,  -- For filtering by project
        details JSONB,
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON dd_audit_log(entity_type, entity_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_user ON dd_audit_log(user_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_type ON dd_audit_log(event_type);
    CREATE INDEX IF NOT EXISTS idx_audit_log_created ON dd_audit_log(created_at);
    CREATE INDEX IF NOT EXISTS idx_audit_log_dd ON dd_audit_log(dd_id);
    """

    # ============================================
    # FINDING ASSIGNMENTS
    # ============================================
    create_finding_assignment_table = """
    CREATE TABLE IF NOT EXISTS dd_finding_assignment (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        finding_id UUID NOT NULL REFERENCES perspective_risk_finding(id) ON DELETE CASCADE,
        assignee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
        priority VARCHAR(20) DEFAULT 'normal',  -- urgent, high, normal, low
        due_date TIMESTAMP WITH TIME ZONE,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'assigned',  -- assigned, in_progress, completed, escalated
        completed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_finding_assignment_finding ON dd_finding_assignment(finding_id);
    CREATE INDEX IF NOT EXISTS idx_finding_assignment_assignee ON dd_finding_assignment(assignee_id);
    CREATE INDEX IF NOT EXISTS idx_finding_assignment_status ON dd_finding_assignment(status);
    CREATE INDEX IF NOT EXISTS idx_finding_assignment_due ON dd_finding_assignment(due_date) WHERE status != 'completed';
    """

    # ============================================
    # FINDING COMMENTS
    # ============================================
    create_finding_comment_table = """
    CREATE TABLE IF NOT EXISTS dd_finding_comment (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        finding_id UUID NOT NULL REFERENCES perspective_risk_finding(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        comment TEXT NOT NULL,
        comment_type VARCHAR(20) DEFAULT 'general',  -- general, question, resolution, approval
        parent_id UUID REFERENCES dd_finding_comment(id) ON DELETE CASCADE,  -- For threaded replies
        is_edited BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_finding_comment_finding ON dd_finding_comment(finding_id);
    CREATE INDEX IF NOT EXISTS idx_finding_comment_user ON dd_finding_comment(user_id);
    CREATE INDEX IF NOT EXISTS idx_finding_comment_parent ON dd_finding_comment(parent_id);
    """

    # ============================================
    # REVIEW WORKFLOWS
    # ============================================
    create_review_workflow_table = """
    CREATE TABLE IF NOT EXISTS dd_review_workflow (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id UUID NOT NULL REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        status VARCHAR(20) DEFAULT 'pending',  -- pending, in_review, approved, rejected
        current_stage VARCHAR(50) DEFAULT 'initial_review',
        stages JSONB DEFAULT '[]'::jsonb,  -- Workflow stage configuration
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

        UNIQUE(run_id)
    );

    CREATE INDEX IF NOT EXISTS idx_review_workflow_dd ON dd_review_workflow(dd_id);
    CREATE INDEX IF NOT EXISTS idx_review_workflow_status ON dd_review_workflow(status);
    """

    create_workflow_approval_table = """
    CREATE TABLE IF NOT EXISTS dd_workflow_approval (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        workflow_id UUID NOT NULL REFERENCES dd_review_workflow(id) ON DELETE CASCADE,
        stage VARCHAR(50) NOT NULL,
        approver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status VARCHAR(20) NOT NULL,  -- approved, rejected, pending
        comments TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_workflow_approval_workflow ON dd_workflow_approval(workflow_id);
    CREATE INDEX IF NOT EXISTS idx_workflow_approval_approver ON dd_workflow_approval(approver_id);
    """

    # ============================================
    # REPORT TEMPLATES
    # ============================================
    create_report_template_table = """
    CREATE TABLE IF NOT EXISTS dd_report_template (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(200) NOT NULL,
        description TEXT,
        template_type VARCHAR(50) DEFAULT 'standard',  -- standard, executive, detailed, custom
        config JSONB NOT NULL,  -- Template configuration
        sections JSONB DEFAULT '[]'::jsonb,  -- Ordered list of section configs
        styles JSONB DEFAULT '{}'::jsonb,  -- Styling configuration
        is_default BOOLEAN DEFAULT FALSE,
        is_public BOOLEAN DEFAULT TRUE,  -- Available to all users
        created_by UUID REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_report_template_type ON dd_report_template(template_type);
    CREATE INDEX IF NOT EXISTS idx_report_template_default ON dd_report_template(is_default) WHERE is_default = TRUE;
    """

    # ============================================
    # EXPORT JOBS
    # ============================================
    create_export_job_table = """
    CREATE TABLE IF NOT EXISTS dd_export_job (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE SET NULL,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        export_type VARCHAR(50) NOT NULL,  -- report_pdf, report_docx, report_html, excel, csv
        template_id UUID REFERENCES dd_report_template(id) ON DELETE SET NULL,
        status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
        config JSONB,  -- Export configuration
        file_name VARCHAR(500),
        file_size_bytes BIGINT,
        download_url TEXT,
        blob_key VARCHAR(255),  -- Storage key for cleanup
        expires_at TIMESTAMP WITH TIME ZONE,
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE
    );

    CREATE INDEX IF NOT EXISTS idx_export_job_dd ON dd_export_job(dd_id);
    CREATE INDEX IF NOT EXISTS idx_export_job_user ON dd_export_job(user_id);
    CREATE INDEX IF NOT EXISTS idx_export_job_status ON dd_export_job(status);
    CREATE INDEX IF NOT EXISTS idx_export_job_expires ON dd_export_job(expires_at) WHERE status = 'completed';
    """

    # ============================================
    # ADD COLUMNS TO perspective_risk_finding
    # ============================================
    alter_finding_table = """
    -- Add review_status for workflow tracking
    ALTER TABLE perspective_risk_finding
    ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) DEFAULT 'pending';
    -- pending, approved, rejected, requires_changes

    -- Add reviewed_by as UUID (migrate from text if exists)
    DO $$
    BEGIN
        -- Check if reviewed_by is text type
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding'
            AND column_name = 'reviewed_by'
            AND data_type = 'text'
        ) THEN
            -- Rename old column
            ALTER TABLE perspective_risk_finding RENAME COLUMN reviewed_by TO reviewed_by_email;
            -- Add new UUID column
            ALTER TABLE perspective_risk_finding ADD COLUMN reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL;
        END IF;
    EXCEPTION
        WHEN undefined_column THEN NULL;
        WHEN duplicate_column THEN NULL;
    END $$;

    -- Add reviewed_at timestamp
    ALTER TABLE perspective_risk_finding
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE;

    -- Add risk_category for grouping (maps to blueprint categories)
    ALTER TABLE perspective_risk_finding
    ADD COLUMN IF NOT EXISTS risk_category VARCHAR(100);

    -- Add title field (derived from phrase but more concise)
    ALTER TABLE perspective_risk_finding
    ADD COLUMN IF NOT EXISTS title VARCHAR(500);

    -- Create index on review_status
    CREATE INDEX IF NOT EXISTS idx_finding_review_status ON perspective_risk_finding(review_status);
    CREATE INDEX IF NOT EXISTS idx_finding_risk_category ON perspective_risk_finding(risk_category);
    """

    # ============================================
    # INSERT DEFAULT REPORT TEMPLATES
    # ============================================
    insert_default_templates = """
    INSERT INTO dd_report_template (id, name, description, template_type, config, sections, styles, is_default, is_public)
    VALUES
    (
        gen_random_uuid(),
        'Standard DD Report',
        'Comprehensive due diligence report with all sections',
        'standard',
        '{"header_logo": true, "footer_page_numbers": true, "toc": true}'::jsonb,
        '["executive_summary", "risk_matrix", "deal_blockers", "findings_by_category", "change_of_control_analysis", "consent_requirements", "financial_exposure", "recommendations", "appendix_document_list"]'::jsonb,
        '{"heading_font": "Arial", "body_font": "Times New Roman", "heading_color": "#1a365d", "accent_color": "#2563eb"}'::jsonb,
        TRUE,
        TRUE
    ),
    (
        gen_random_uuid(),
        'Executive Summary',
        'Concise summary for senior stakeholders (max 10 pages)',
        'executive',
        '{"header_logo": true, "footer_page_numbers": true, "toc": false, "max_pages": 10}'::jsonb,
        '["executive_summary", "risk_matrix", "deal_blockers", "top_recommendations"]'::jsonb,
        '{"heading_font": "Arial", "body_font": "Arial", "heading_color": "#1a365d", "accent_color": "#2563eb"}'::jsonb,
        FALSE,
        TRUE
    ),
    (
        gen_random_uuid(),
        'Detailed Analysis',
        'Full detailed report with document extracts and appendices',
        'detailed',
        '{"header_logo": true, "footer_page_numbers": true, "toc": true, "include_appendices": true, "include_document_extracts": true}'::jsonb,
        '["executive_summary", "risk_matrix", "deal_blockers", "findings_by_category", "change_of_control_analysis", "consent_requirements", "financial_exposure", "recommendations", "appendix_document_list", "appendix_full_findings", "appendix_document_extracts"]'::jsonb,
        '{"heading_font": "Arial", "body_font": "Times New Roman", "heading_color": "#1a365d", "accent_color": "#2563eb"}'::jsonb,
        FALSE,
        TRUE
    )
    ON CONFLICT DO NOTHING;
    """

    with engine.connect() as conn:
        print("Creating users table...")
        conn.execute(text(create_users_table))
        conn.commit()

        print("Creating dd_audit_log table...")
        conn.execute(text(create_audit_log_table))
        conn.commit()

        print("Creating dd_finding_assignment table...")
        conn.execute(text(create_finding_assignment_table))
        conn.commit()

        print("Creating dd_finding_comment table...")
        conn.execute(text(create_finding_comment_table))
        conn.commit()

        print("Creating dd_review_workflow table...")
        conn.execute(text(create_review_workflow_table))
        conn.commit()

        print("Creating dd_workflow_approval table...")
        conn.execute(text(create_workflow_approval_table))
        conn.commit()

        print("Creating dd_report_template table...")
        conn.execute(text(create_report_template_table))
        conn.commit()

        print("Creating dd_export_job table...")
        conn.execute(text(create_export_job_table))
        conn.commit()

        print("Altering perspective_risk_finding table...")
        conn.execute(text(alter_finding_table))
        conn.commit()

        print("Inserting default report templates...")
        conn.execute(text(insert_default_templates))
        conn.commit()

        print("\nMigration completed successfully!")
        print("")
        print("Tables created:")
        print("  - users: User accounts for collaboration")
        print("  - dd_audit_log: Complete audit trail")
        print("  - dd_finding_assignment: Finding assignments to users")
        print("  - dd_finding_comment: Comments and discussions")
        print("  - dd_review_workflow: Approval workflow tracking")
        print("  - dd_workflow_approval: Individual approvals")
        print("  - dd_report_template: Customizable report templates")
        print("  - dd_export_job: Export job tracking")
        print("")
        print("Columns added to perspective_risk_finding:")
        print("  - review_status: Workflow approval status")
        print("  - reviewed_at: When finding was reviewed")
        print("  - risk_category: Category for grouping")
        print("  - title: Concise title for display")


def rollback_migration():
    """Drop all enterprise feature tables."""

    drop_tables_sql = """
    -- Drop tables in reverse dependency order
    DROP TABLE IF EXISTS dd_export_job CASCADE;
    DROP TABLE IF EXISTS dd_report_template CASCADE;
    DROP TABLE IF EXISTS dd_workflow_approval CASCADE;
    DROP TABLE IF EXISTS dd_review_workflow CASCADE;
    DROP TABLE IF EXISTS dd_finding_comment CASCADE;
    DROP TABLE IF EXISTS dd_finding_assignment CASCADE;
    DROP TABLE IF EXISTS dd_audit_log CASCADE;

    -- Drop users table last (most dependencies)
    DROP TABLE IF EXISTS users CASCADE;

    -- Remove added columns from perspective_risk_finding
    ALTER TABLE perspective_risk_finding DROP COLUMN IF EXISTS review_status;
    ALTER TABLE perspective_risk_finding DROP COLUMN IF EXISTS reviewed_at;
    ALTER TABLE perspective_risk_finding DROP COLUMN IF EXISTS risk_category;
    ALTER TABLE perspective_risk_finding DROP COLUMN IF EXISTS title;

    -- Restore reviewed_by from email if it was migrated
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding'
            AND column_name = 'reviewed_by_email'
        ) THEN
            ALTER TABLE perspective_risk_finding DROP COLUMN IF EXISTS reviewed_by;
            ALTER TABLE perspective_risk_finding RENAME COLUMN reviewed_by_email TO reviewed_by;
        END IF;
    EXCEPTION
        WHEN undefined_column THEN NULL;
    END $$;
    """

    with engine.connect() as conn:
        print("Dropping all enterprise feature tables...")
        conn.execute(text(drop_tables_sql))
        conn.commit()
        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 7 Enterprise Features migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
