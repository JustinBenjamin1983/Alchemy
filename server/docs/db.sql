DROP TABLE IF EXISTS perspective_risk CASCADE;
DROP TABLE IF EXISTS perspective CASCADE;
DROP TABLE IF EXISTS document_history CASCADE;
DROP TABLE IF EXISTS document CASCADE;
DROP TABLE IF EXISTS folder CASCADE;
DROP TABLE IF EXISTS due_diligence_member CASCADE;
DROP TABLE IF EXISTS due_diligence CASCADE;

-- Drop ENUM type used by document_history
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_action') THEN
        DROP TYPE document_action;
    END IF;
END$$;


CREATE TYPE document_action AS ENUM ('ZIP uploaded', 'Added', 'Moved', 'Deleted', 'File Renamed');

CREATE TABLE due_diligence (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    briefing TEXT,
    owned_by TEXT NOT NULL,
    original_file_name TEXT,
    original_file_doc_id UUID,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE due_diligence_member (
    id UUID PRIMARY KEY,
    dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
    member_email TEXT NOT NULL,
    CONSTRAINT uq_dd_member UNIQUE (dd_id, member_email)
);

CREATE TABLE folder (
    id UUID PRIMARY KEY,
    dd_id UUID REFERENCES due_diligence(id) ON DELETE CASCADE,
    folder_name TEXT NOT NULL,
    is_root BOOLEAN DEFAULT FALSE,
    path TEXT NOT NULL,
    hierarchy TEXT NOT NULL
);


CREATE TABLE document (
    id UUID PRIMARY KEY,
    folder_id UUID NOT NULL REFERENCES folder(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    is_original BOOLEAN DEFAULT FALSE,
    original_file_name TEXT NOT NULL,
    uploaded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    processing_status TEXT NOT NULL,
    size_in_bytes BIGINT
);

CREATE TABLE document_history (
    id SERIAL PRIMARY KEY,
    doc_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
    original_file_name TEXT NOT NULL,
    previous_folder TEXT,
    current_folder TEXT,
    action document_action NOT NULL,
    by_user TEXT,
    action_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE perspective (
    id UUID PRIMARY KEY,
    member_id UUID NOT NULL REFERENCES due_diligence_member(id) ON DELETE CASCADE,
    lens TEXT NOT NULL
);
CREATE TABLE perspective_risk (
    id UUID PRIMARY KEY,
    perspective_id UUID NOT NULL REFERENCES perspective(id) ON DELETE CASCADE,
    category TEXT NOT null,
    detail TEXT NOT null,
    is_processed BOOLEAN DEFAULT FALSE
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE TYPE perspective_risk_finding_status AS ENUM ('New', 'Red', 'Amber', 'Deleted');

CREATE TABLE perspective_risk_finding (
    id UUID PRIMARY KEY,
    perspective_risk_id UUID NOT NULL REFERENCES perspective_risk(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    phrase TEXT NOT NULL,
    page_number TEXT NOT NULL,
    status perspective_risk_finding_status NOT NULL,
    is_reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by TEXT
);
