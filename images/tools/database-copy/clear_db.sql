DO $$ DECLARE
  r RECORD;
BEGIN
  -- DROP TABLES
  FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
    CASE
      WHEN r.tablename NOT IN ('spatial_ref_sys') THEN
        EXECUTE format('DROP TABLE IF EXISTS %I CASCADE;', r.tablename);
      ELSE null;
    END CASE;
  END LOOP;

  -- DROP SEQUENCES
  FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
    EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE;', r.sequence_name);
  END LOOP;

  -- DROP VIEWS
  FOR r IN (SELECT table_name FROM information_schema.views WHERE table_schema = 'public') LOOP
    EXECUTE format('DROP VIEW IF EXISTS %I CASCADE;', r.table_name);
  END LOOP;

  FOR r IN (SELECT matviewname FROM pg_matviews WHERE schemaname = 'public') LOOP
    EXECUTE format('DROP MATERIALIZED VIEW IF EXISTS %I CASCADE', r.matviewname);
  END LOOP;

  -- DROP USER DEFINED FUNCTIONS
  FOR r IN (
    SELECT n.nspname AS schemaname, p.proname AS functionname, pg_get_function_identity_arguments(p.oid) AS args
    FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
  ) LOOP
    EXECUTE format('DROP FUNCTION IF EXISTS %I.%I(%s) CASCADE;', r.schemaname, r.functionname, r.args);
  END LOOP;
END $$;
