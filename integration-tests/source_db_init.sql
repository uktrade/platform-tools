CREATE DATABASE test_db;
\c test_db;
CREATE TABLE test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    value INT
);
INSERT INTO test_table (name, value) VALUES ("Bob", 500);