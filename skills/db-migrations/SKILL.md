---
name: db-migrations
description: Use when writing a schema or data migration, adding a column or index to a large table, planning a rollback, or preparing a zero-downtime deploy. Postgres locks and lock_timeout, CREATE INDEX CONCURRENTLY, expand-contract renames, batched backfills, Django and golang-migrate workflows.
---

# Database migration patterns

Safe, reversible schema changes for production systems.

## When to use

- Creating or altering tables
- Adding or removing columns or indexes
- Running data migrations (backfill, transform)
- Planning zero-downtime schema changes
- Setting up migration tooling for a new project

## Core principles

1. **Every change is a migration.** Never alter production databases by hand.
2. **Migrations are forward-only in production.** Rollbacks are new forward migrations.
3. **Schema and data migrations are separate.** Never mix DDL and DML in one migration.
4. **Test against production-sized data.** A migration that works on 100 rows may lock on 10M.
5. **Migrations are immutable once deployed.** Never edit a migration that has run in production.

## Safety checklist

Before applying any migration:

- [ ] Migration has both UP and DOWN (or is explicitly marked irreversible)
- [ ] Lock modes and expected hold times reviewed; concurrent operations used where supported
- [ ] On populated tables, new columns are nullable or have defaults compatible with their constraints
- [ ] Indexes created concurrently (not inline with CREATE TABLE for existing tables)
- [ ] Data backfill is a separate migration from the schema change
- [ ] Tested against a copy of production data
- [ ] Rollback plan documented

## PostgreSQL patterns

### Adding a column safely

```sql
-- Nullable column: no table rewrite, but takes ACCESS EXCLUSIVE lock
ALTER TABLE users ADD COLUMN avatar_url TEXT;

-- PostgreSQL 11+: a non-volatile default avoids a table rewrite
-- Still takes ACCESS EXCLUSIVE lock and may wait for other transactions
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;

-- BAD on a populated table: existing rows would have NULL in the new column
ALTER TABLE users ADD COLUMN role TEXT NOT NULL;
-- Fails with not_null_violation (SQLSTATE 23502); does not backfill existing rows
```

Avoiding a table rewrite does not mean avoiding locks. These `ADD COLUMN` operations take an `ACCESS EXCLUSIVE` lock, held until the transaction ends. Keep the transaction short and set a `lock_timeout` to bound lock acquisition waits. A volatile default such as `clock_timestamp()` requires a table rewrite; the PostgreSQL 11+ fast path applies only to non-volatile defaults. Adding a `NOT NULL` column without a default can succeed on an empty table.

Run the self-checking [reproduction SQL](examples/postgres-add-column.sql) on PostgreSQL 11+:

```bash
psql -X -v ON_ERROR_STOP=1 -f examples/postgres-add-column.sql
```

It uses a temporary table, rolls back the ALTERs and drops the fixture, checking lock acquisition, rewrites and the expected constraint violation.

Reference: [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html).

### Adding an index without downtime

```sql
-- BAD: blocks writes on large tables
CREATE INDEX idx_users_email ON users (email);

-- GOOD: non-blocking, allows concurrent writes
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);

-- Note: CONCURRENTLY cannot run inside a transaction block
-- Most migration tools need special handling for this
```

### Renaming a column (zero-downtime)

For a pure rename (both columns hold the same value), use expand-contract. Keep `username` authoritative until the read cutover:

```sql
-- Step 1: Expand (migration 001)
ALTER TABLE users ADD COLUMN display_name TEXT;

-- Step 2: Deploy app v2: read username, write BOTH columns atomically.
-- Cover every INSERT/UPDATE path, including jobs, imports, and admin tools.
-- Drain old-only writers and their in-flight transactions before backfilling.

-- Step 3: Backfill in bounded primary-key ranges (separate data migration).
-- Example range; advance bounds to cover every existing id.
BEGIN;
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET LOCAL lock_timeout = '2s';
UPDATE users SET display_name = username
WHERE id > 0 AND id <= 10000
  AND display_name IS DISTINCT FROM username;
COMMIT;

-- Step 4: Validate AFTER all ranges complete, while dual writes continue.
-- Require zero mismatches before switching reads.
SELECT count(*) AS mismatched_rows FROM users
WHERE display_name IS DISTINCT FROM username;

-- Step 5: Deploy app v3: read display_name, still write BOTH columns.
-- Keep dual writes throughout the rollback window.

-- Step 6: After the rollback window, stop backfill/reconciliation workers.
-- Transfer required constraints/indexes/dependencies to the new column.
-- Make old-column constraints compatible with new-only INSERTs/UPDATEs.
-- Drain non-app readers of username and their in-flight transactions first.
-- Then deploy app v4 using ONLY display_name; drain remaining old-column users.

-- Step 7: Contract in a separate migration after checking dependencies.
ALTER TABLE users DROP COLUMN username;
```

Commit each range independently; checkpoint only after commit and retry failed batch transactions. Choose bounds for the actual key space (including zero or negative IDs if present). `IS DISTINCT FROM` repairs stale non-NULL values and handles NULL pairs without repeatedly updating them. Do not fetch `username` into application memory and later write that stale snapshot: copy the row's current value in the same `UPDATE`. At Read Committed, concurrent updates serialize on the row and PostgreSQL rechecks the predicate after waiting.

Deploying dual writes does not repair earlier drift by itself. Finish draining old-only writers before backfill, and validate parity before read cutover. Once new-only writes start, the old column may be stale: do not restart this backfill or roll back to old readers without a reconciliation plan. The timeline below shows deployment gates, not guaranteed elapsed time or lock-free DDL.

The [self-checking SQL example](examples/postgres-column-rename.sql) reproduces the stale-value failure and verifies reconciliation, retries and NULL handling:

```bash
psql -X -v ON_ERROR_STOP=1 -f examples/postgres-column-rename.sql
```

Reference: [PostgreSQL Read Committed behavior](https://www.postgresql.org/docs/current/transaction-iso.html#XACT-READ-COMMITTED).

### Removing a column safely

```sql
-- Step 1: Remove all application references to the column
-- Step 2: Deploy application without the column reference
-- Step 3: Drop column in next migration
ALTER TABLE orders DROP COLUMN legacy_status;

-- For Django: use SeparateDatabaseAndState to remove from model
-- without generating DROP COLUMN (then drop in next migration)
```

### Large data migrations

```sql
-- BAD: updates all rows in one transaction (locks table)
UPDATE users SET normalized_email = LOWER(email);

-- GOOD: batch update with progress
DO $$
DECLARE
  batch_size INT := 10000;
  rows_updated INT;
BEGIN
  LOOP
    UPDATE users
    SET normalized_email = LOWER(email)
    WHERE id IN (
      SELECT id FROM users
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
```

## Django (Python)

### Workflow

```bash
# Generate migration from model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Generate empty migration for custom SQL
python manage.py makemigrations --empty app_name -n description
```

### Data migration

```python
from django.db import migrations

def backfill_display_names(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    batch_size = 5000
    users = User.objects.filter(display_name="")
    while users.exists():
        batch = list(users[:batch_size])
        for user in batch:
            user.display_name = user.username
        User.objects.bulk_update(batch, ["display_name"], batch_size=batch_size)

def reverse_backfill(apps, schema_editor):
    pass  # Data migration, no reverse needed

class Migration(migrations.Migration):
    dependencies = [("accounts", "0015_add_display_name")]

    operations = [
        migrations.RunPython(backfill_display_names, reverse_backfill),
    ]
```

### SeparateDatabaseAndState

Remove a column from the Django model without dropping it from the database yet:

```python
class Migration(migrations.Migration):
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="user", name="legacy_field"),
            ],
            database_operations=[],  # Don't touch the DB yet
        ),
    ]
```

## golang-migrate (Go)

### Workflow

```bash
# Create migration pair
migrate create -ext sql -dir migrations -seq add_user_avatar

# Apply all pending migrations
migrate -path migrations -database "$DATABASE_URL" up

# Roll back last migration
migrate -path migrations -database "$DATABASE_URL" down 1

# Force version (fix dirty state)
migrate -path migrations -database "$DATABASE_URL" force VERSION
```

### Migration files

```sql
-- migrations/000003_add_user_avatar.up.sql
ALTER TABLE users ADD COLUMN avatar_url TEXT;
CREATE INDEX CONCURRENTLY idx_users_avatar ON users (avatar_url) WHERE avatar_url IS NOT NULL;

-- migrations/000003_add_user_avatar.down.sql
DROP INDEX IF EXISTS idx_users_avatar;
ALTER TABLE users DROP COLUMN IF EXISTS avatar_url;
```

## Zero-downtime strategy

For critical production changes, follow expand-contract:

```
Phase 1: EXPAND
  - Add new column/table (nullable or with default)
  - Deploy: app reads OLD, writes BOTH atomically
  - Drain old-only writers and in-flight transactions
  - Backfill in committed batches, then verify parity

Phase 2: MIGRATE
  - Deploy: app reads from NEW, writes to BOTH
  - Monitor parity and retain dual writes throughout the rollback window

Phase 3: CONTRACT
  - End rollback window; stop backfill and migrate constraints/dependencies
  - Drain non-app old-column readers and their in-flight transactions
  - Deploy: app only uses NEW; drain remaining old-column users
  - Drop old column/table in separate migration
```

### Timeline example

```
Day 1: Migration adds new_status column (nullable)
Day 1: Deploy app v2: reads status, writes both columns atomically
Day 2: Drain old-only writers; backfill in batches; require zero mismatches
Day 3: Deploy app v3: reads new_status, still writes both columns
Day 7: End rollback window; stop backfill; migrate constraints/dependencies
Day 7: Drain non-app old-column readers and their in-flight transactions
Day 7: Deploy app v4: only uses new_status; drain remaining old-column users
Later: Separate migration drops status after all contract gates pass
```

## Anti-patterns

| Anti-pattern | Why it fails | Better approach |
|-------------|-------------|-----------------|
| Manual SQL in production | No audit trail, unrepeatable | Always use migration files |
| Editing deployed migrations | Causes drift between environments | Create a new migration instead |
| Adding NOT NULL column without default to populated table | Fails because existing rows would contain NULL | Add nullable, backfill, then set NOT NULL |
| Inline index on large table | Blocks writes during build | CREATE INDEX CONCURRENTLY |
| Schema + data in one migration | Hard to roll back, long transactions | Separate migrations |
| Dropping column before removing code | Application errors on missing column | Remove code first, drop column next deploy |

Adapted from affaan-m/everything-claude-code (MIT) @3f14a10: database-migrations.
