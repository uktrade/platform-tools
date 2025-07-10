DO $$ DECLARE
  r RECORD;
BEGIN
  -- DROP TABLES
    FOR r IN
        SELECT schemaname, tablename FROM pg_tables
        WHERE schemaname = 'public'
        AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            JOIN pg_extension e ON d.refobjid = e.oid
            WHERE d.objid = ('public.' || quote_ident(tablename))::regclass::oid
        )
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.schemaname) || '.' || quote_ident(r.tablename) || ' CASCADE';
        RAISE NOTICE 'Dropped table: %.%', r.schemaname, r.tablename;
    END LOOP;

  -- DROP SEQUENCES
  FOR r IN
    SELECT sequence_schema, sequence_name FROM information_schema.sequences
    WHERE sequence_schema = 'public'
    AND NOT EXISTS (
        SELECT 1 FROM pg_depend d
        JOIN pg_extension e ON d.refobjid = e.oid
        WHERE d.objid = ('public.' || quote_ident(sequence_name))::regclass::oid
    )
  LOOP
    EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE;', r.sequence_name);
    RAISE NOTICE 'Dropped sequence: %.%', r.sequence_schema, r.sequence_name;
  END LOOP;

  -- DROP VIEWS
  FOR r IN (SELECT table_schema, table_name FROM information_schema.views WHERE table_schema = 'public' AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            JOIN pg_extension e ON d.refobjid = e.oid
            WHERE d.objid = ('public.' || quote_ident(table_name))::regclass::oid
        )
  ) LOOP
    EXECUTE format('DROP VIEW IF EXISTS %I CASCADE;', r.table_name);
    RAISE NOTICE 'Dropped view: %.%', r.table_schema, r.table_name;
  END LOOP;

  FOR r IN (SELECT schemaname, matviewname FROM pg_matviews WHERE schemaname = 'public' AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            JOIN pg_extension e ON d.refobjid = e.oid
            WHERE d.objid = ('public.' || quote_ident(matviewname))::regclass::oid
        )
  ) LOOP
    EXECUTE format('DROP MATERIALIZED VIEW IF EXISTS %I CASCADE', r.matviewname);
    RAISE NOTICE 'Dropped materialized view: %.%', r.schemaname, r.matviewname;
  END LOOP;

  -- DROP USER DEFINED FUNCTIONS
  FOR r IN (
    SELECT n.nspname as schemaname, p.proname as functionname,
               pg_get_function_identity_arguments(p.oid) as args
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            JOIN pg_extension e ON d.refobjid = e.oid
            WHERE d.objid = p.oid
        )
  ) LOOP
    EXECUTE format('DROP FUNCTION IF EXISTS %I.%I(%s) CASCADE;', r.schemaname, r.functionname, r.args);
    RAISE NOTICE 'Dropped function: %.%', r.schemaname, r.functionname;
  END LOOP;
END $$;
