-- PostgreSQL 11+; run with psql -X -v ON_ERROR_STOP=1 -f postgres-batch-backfill.sql
-- Do not use --single-transaction: COMMIT is valid only in a top-level DO command.
\set ON_ERROR_STOP on
CREATE TEMP TABLE batch_backfill_demo (
    id integer PRIMARY KEY,
    email text,
    normalized_email text
);
INSERT INTO batch_backfill_demo
SELECT i, 'USER' || i || '@EXAMPLE.COM', NULL
FROM generate_series(1, 5) AS i;

DO $$
DECLARE
    batch_size integer := 2;
    rows_updated integer;
BEGIN
    LOOP
        UPDATE batch_backfill_demo
        SET normalized_email = LOWER(email)
        WHERE id IN (
            SELECT id FROM batch_backfill_demo
            WHERE normalized_email IS NULL
            LIMIT batch_size
            FOR UPDATE SKIP LOCKED
        );
        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        RAISE NOTICE 'Updated % rows', rows_updated;
        EXIT WHEN rows_updated = 0;
        COMMIT;
    END LOOP;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM batch_backfill_demo
        WHERE normalized_email IS DISTINCT FROM LOWER(email)
    ) THEN
        RAISE EXCEPTION 'Expected every row to be normalized after the final empty batch';
    END IF;
    RAISE NOTICE 'PASS: top-level DO/COMMIT completes all batches';
END $$;
DROP TABLE batch_backfill_demo;
