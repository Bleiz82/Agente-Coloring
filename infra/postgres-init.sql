-- ColorForge initial DB setup
-- Extensions used by the schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- fuzzy search on titles/keywords
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- composite indexes on JSONB

-- Application role with limited privileges (the apps will use this, not superuser)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'colorforge_app') THEN
    CREATE ROLE colorforge_app LOGIN PASSWORD 'colorforge_app_dev';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE colorforge TO colorforge_app;
GRANT USAGE ON SCHEMA public TO colorforge_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO colorforge_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO colorforge_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO colorforge_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO colorforge_app;
