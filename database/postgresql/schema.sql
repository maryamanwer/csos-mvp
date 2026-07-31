-- ============================================================
-- CSOS PostgreSQL Schema (Implementation Phase 1)
-- Scope: Users, Auth, RBAC, Configuration, Audit Logs
-- (Assets/Risks/Vulns/Policies/Relationships live in Neo4j — see neo4j/schema.cypher)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------- Roles ----------
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(50) UNIQUE NOT NULL,   -- Admin, Executive, Analyst, Engineer, ComplianceOfficer
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Users ----------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    role_id         UUID NOT NULL REFERENCES roles(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX idx_users_role_id ON users(role_id);

-- ---------- Permissions (fine-grained, optional beyond role) ----------
CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code        VARCHAR(100) UNIQUE NOT NULL,   -- e.g. asset:write, report:generate
    description TEXT
);

CREATE TABLE role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- ---------- Refresh tokens ----------
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- ---------- Audit Log ----------
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(100) NOT NULL,     -- e.g. LOGIN, ASSET_CREATE, ROLE_CHANGE
    entity_type VARCHAR(100),
    entity_id   VARCHAR(100),
    metadata    JSONB,
    ip_address  VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- ---------- System Configuration ----------
CREATE TABLE system_config (
    key         VARCHAR(100) PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Custom Standards / Policy Uploads (metadata; content parsed into Neo4j) ----------
CREATE TABLE standards_uploads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    file_name       VARCHAR(255) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,     -- csv, xlsx, docx, json, manual
    status          VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, processed, failed
    controls_parsed INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Reports (generated artifacts metadata) ----------
CREATE TABLE reports (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generated_by UUID NOT NULL REFERENCES users(id),
    report_type VARCHAR(50) NOT NULL,   -- risk, compliance, asset
    format      VARCHAR(10) NOT NULL,   -- pdf, xlsx
    file_path   TEXT NOT NULL,
    filters     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Notifications (core platform implementation) ----------
CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    body        TEXT,
    severity    VARCHAR(20) DEFAULT 'info',  -- info, warning, critical
    read        BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Seed default roles ----------
INSERT INTO roles (name, description) VALUES
    ('Admin', 'Full system administration'),
    ('Executive', 'Read-only strategic dashboards'),
    ('Analyst', 'Investigate and respond to risks/vulnerabilities'),
    ('Engineer', 'Manage assets and technical controls'),
    ('ComplianceOfficer', 'Manage frameworks, policies, and audits');
