-- AI Foundation Teambook Schema for PostgreSQL
-- This script initializes the database with all required tables and indices

-- Notes table - main storage for teambook notes
CREATE TABLE IF NOT EXISTS notes (
    id BIGSERIAL PRIMARY KEY,
    content TEXT,
    summary TEXT,
    tags TEXT[],
    pinned BOOLEAN DEFAULT FALSE,
    author VARCHAR NOT NULL,
    owner VARCHAR,
    teambook_name VARCHAR,
    type VARCHAR,
    parent_id BIGINT,
    created TIMESTAMPTZ NOT NULL,
    session_id BIGINT,
    linked_items TEXT,
    pagerank DOUBLE PRECISION DEFAULT 0.0,
    has_vector BOOLEAN DEFAULT FALSE
);

-- Edges table - knowledge graph relationships
CREATE TABLE IF NOT EXISTS edges (
    from_id BIGINT NOT NULL,
    to_id BIGINT NOT NULL,
    type VARCHAR NOT NULL,
    weight DOUBLE PRECISION DEFAULT 1.0,
    created TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(from_id, to_id, type)
);

-- Evolution outputs table - stores collaborative problem-solving results
CREATE TABLE IF NOT EXISTS evolution_outputs (
    id BIGSERIAL PRIMARY KEY,
    evolution_id BIGINT NOT NULL,
    output_path TEXT NOT NULL,
    created TIMESTAMPTZ NOT NULL,
    author VARCHAR NOT NULL
);

-- Teambooks registry - tracks all teambook instances
CREATE TABLE IF NOT EXISTS teambooks (
    name VARCHAR PRIMARY KEY,
    created TIMESTAMPTZ NOT NULL,
    created_by VARCHAR NOT NULL,
    last_active TIMESTAMPTZ
);

-- Entities table - named entity recognition and tracking
CREATE TABLE IF NOT EXISTS entities (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    type VARCHAR NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    mention_count INTEGER DEFAULT 1
);

-- Entity notes junction - links entities to notes
CREATE TABLE IF NOT EXISTS entity_notes (
    entity_id BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    note_id BIGINT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    PRIMARY KEY(entity_id, note_id)
);

-- Sessions table - conversation session tracking
CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    started TIMESTAMPTZ NOT NULL,
    ended TIMESTAMPTZ NOT NULL,
    note_count INTEGER DEFAULT 1,
    coherence_score DOUBLE PRECISION DEFAULT 1.0
);

-- Vault table - encrypted secrets storage
CREATE TABLE IF NOT EXISTS vault (
    key VARCHAR PRIMARY KEY,
    encrypted_value BYTEA NOT NULL,
    created TIMESTAMPTZ NOT NULL,
    updated TIMESTAMPTZ NOT NULL,
    author VARCHAR NOT NULL
);

-- Stats table - operation tracking and analytics
CREATE TABLE IF NOT EXISTS stats (
    id BIGSERIAL PRIMARY KEY,
    operation VARCHAR NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    dur_ms INTEGER,
    author VARCHAR
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created DESC);
CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned DESC, created DESC);
CREATE INDEX IF NOT EXISTS idx_notes_pagerank ON notes(pagerank DESC);
CREATE INDEX IF NOT EXISTS idx_notes_owner ON notes(owner);
CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(type);
CREATE INDEX IF NOT EXISTS idx_notes_parent ON notes(parent_id);
CREATE INDEX IF NOT EXISTS idx_notes_teambook ON notes(teambook_name);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id);

-- Full-text search using PostgreSQL's native GIN index
CREATE INDEX IF NOT EXISTS idx_notes_fts 
ON notes USING GIN (to_tsvector('english', content || ' ' || COALESCE(summary, '')));

-- Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO teambook;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO teambook;
