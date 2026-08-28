-- ============================================================
-- CSOS PostgreSQL Schema (Implementation Phase 2)
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
    token_hash  VARCHAR(255) UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);

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

-- ---------- Phase 3 collection layer ----------
CREATE TABLE connector_configs (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name              VARCHAR(255) NOT NULL,
    connector_key     VARCHAR(100) NOT NULL,
    description       TEXT,
    config            JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled           BOOLEAN NOT NULL DEFAULT true,
    schedule_minutes  INTEGER,
    last_run_at       TIMESTAMPTZ,
    last_run_status   VARCHAR(20),
    last_run_summary  JSONB,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_connector_configs_key ON connector_configs(connector_key);

CREATE TABLE connector_runs (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connector_config_id   UUID NOT NULL REFERENCES connector_configs(id) ON DELETE CASCADE,
    connector_key         VARCHAR(100) NOT NULL,
    status                VARCHAR(20) NOT NULL DEFAULT 'queued',
    trigger               VARCHAR(20) NOT NULL DEFAULT 'manual',
    started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at           TIMESTAMPTZ,
    duration_seconds      DOUBLE PRECISION,
    assets_found          INTEGER DEFAULT 0,
    interfaces_found      INTEGER DEFAULT 0,
    links_found           INTEGER DEFAULT 0,
    vulnerabilities_found INTEGER DEFAULT 0,
    events_found          INTEGER DEFAULT 0,
    written               JSONB,
    errors                JSONB,
    triggered_by          UUID REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX idx_connector_runs_config ON connector_runs(connector_config_id);
CREATE INDEX idx_connector_runs_started ON connector_runs(started_at DESC);

CREATE TABLE ingest_api_keys (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(255) NOT NULL,
    key_hash      VARCHAR(64) UNIQUE NOT NULL,
    key_prefix    VARCHAR(16) NOT NULL,
    enabled       BOOLEAN NOT NULL DEFAULT true,
    scope         VARCHAR(50) NOT NULL DEFAULT 'agent',
    last_used_at  TIMESTAMPTZ,
    last_used_ip  VARCHAR(64),
    use_count     INTEGER NOT NULL DEFAULT 0,
    created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ
);
CREATE INDEX idx_ingest_api_keys_hash ON ingest_api_keys(key_hash);

CREATE TABLE ai_conversations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_conversations_user ON ai_conversations(user_id);

CREATE TABLE ai_messages (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id  UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role              VARCHAR(20) NOT NULL,
    content           TEXT NOT NULL,
    agent_trace       JSONB,
    citations         JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_messages_conversation ON ai_messages(conversation_id);

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
    ('ComplianceOfficer', 'Manage frameworks, policies, and audits')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;

-- ---------- Seed Phase 2 permissions ----------
INSERT INTO permissions (code, description) VALUES
    ('dashboard:read', 'View role-appropriate dashboards'),
    ('asset:read', 'View assets and relationships'),
    ('asset:write', 'Create and update assets and relationships'),
    ('vulnerability:read', 'View vulnerabilities'),
    ('vulnerability:write', 'Create and update vulnerabilities'),
    ('admin:manage', 'Manage users, roles, and audit information')
ON CONFLICT (code) DO UPDATE SET description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT role.id, permission.id
FROM roles role
CROSS JOIN permissions permission
WHERE role.name = 'Admin'
ON CONFLICT DO NOTHING;
