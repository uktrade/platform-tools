DO $$ DECLARE
  r RECORD;
BEGIN
  FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
    CASE
      WHEN r.tablename NOT IN ('spatial_ref_sys') THEN
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
      ELSE null;
    END CASE;
  END LOOP;
END $$;
