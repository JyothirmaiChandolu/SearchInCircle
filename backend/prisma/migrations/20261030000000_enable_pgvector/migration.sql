-- Enables the pgvector extension used later by the Matching Service for
-- embedding storage/similarity queries (cosine distance via the <=> operator).
CREATE EXTENSION IF NOT EXISTS vector;
