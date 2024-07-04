echo "Starting database copy."

pg_dump $SOURCE_DB_CONNECTION | psql $TARGET_DB_CONNECTION main

exit
