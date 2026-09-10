CREATE USER living_memory_test PASSWORD 'local-test-only';
CREATE DATABASE living_memory_test OWNER living_memory_test;
REVOKE CONNECT ON DATABASE living_memory_dev FROM PUBLIC;
GRANT CONNECT ON DATABASE living_memory_dev TO living_memory;
