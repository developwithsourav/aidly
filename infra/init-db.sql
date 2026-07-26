-- Extensions the schema depends on. PostGIS gives us indexed "nearest
-- responder" queries; pgvector gives us protocol retrieval without a separate
-- vector database.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
