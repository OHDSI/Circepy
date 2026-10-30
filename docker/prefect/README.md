# Prefect-compatible cohort-generation container

This image runs a cohort definition set through circepy's shared-checkpoint
generator and writes into a target schema/table.  It can be invoked directly or
used as the image for a Prefect deployment/work pool.

## Build

From the repository root:

```bash
docker build -f docker/prefect/Dockerfile -t circe-cohort-runner .
```

The image installs the `prefect`, `ibis-postgres` and `ibis-databricks` extras.
Override with `--build-arg CIRCE_EXTRAS="prefect,ibis-postgres"` for a smaller
Postgres-only image.

## Payload

See `payload.example.json`:

```json
{
  "cdm_schema": "demo_cdm",
  "vocabulary_schema": "demo_cdm",
  "target": {
    "schema": "circe_demo_results",
    "table": "cohort",
    "registry_table": "cohort_definition_registry",
    "reuse_existing": true,
    "on_definition_change": "error"
  },
  "definitions": {
    "settings_file": "/data/Cohorts.csv",
    "json_folder": "/data/cohorts",
    "sql_folder": "/data/sql/sql_server",
    "base_dir": "/data"
  },
  "backend": {
    "type": "postgresql",
    "host": "host.docker.internal",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password_env": "PGPASSWORD"
  },
  "shared": true
}
```

Secrets are read from environment variables named by `password_env` /
`access_token_env`; they must not be put in the payload.

## Run directly

```bash
docker run --rm \
  -e PGPASSWORD="$PGPASSWORD" \
  -v "$PWD/definitions:/data:ro" \
  -v "$PWD/payload.json:/payload.json:ro" \
  circe-cohort-runner
```

Use `--prefect` to execute through the Prefect flow:

```bash
docker run --rm ... circe-cohort-runner --prefect
```

## Run under Prefect

Use the image as the deployment image and set the entrypoint to either:

```bash
python -m circe.runner --payload /payload.json
```

or, when the deployment supplies a payload file, run the flow directly:

```bash
python -m circe.runner --prefect --payload /payload.json
```

Mount the definitions directory at `/data` and the payload at `/payload.json`.
The flow is exported as `circe.runner.flow:run_cohort_generation_flow`; it
accepts the same payload dictionary.

## Persistence model

- Cohort rows are written to `target.schema.target.table`, one cohort id at a
  time. On backends without cohort-scoped transactions, circepy stages the new
  rows and then deletes/inserts only the affected cohort ids; it never rewrites
  the whole cohort table.
- `target.registry_table` stores the definition checksum and a completion
  marker (`completed`, `row_count`, `completed_at`). It does not store full
  definition JSON or SQL, keeping registry writes small and portable. Each
  cohort is marked complete immediately after its rows are written, not at the
  end of the shard. Reruns reuse a cohort only when the definition checksum matches, the
  previous write completed, and the target row count matches the recorded count.
  An interrupted shard therefore resumes at cohort granularity; only the cohort
  that was in flight needs to be regenerated. Registry writes reconnect before
  each write and retry with a fresh connection, and the original backend error
  is chained into `ShardingError`.
- If an id already exists with a different definition, the runner fails by
  default. Set `on_definition_change="replace"` only when you own that id.
  Identifier mapping across users/definitions is deliberately deferred.
- `target.schema` must be a scratch/results schema. Circepy warns when the target
  schema is the CDM schema, or when a lower-level API would create session/cohort
  tables in the CDM schema.
- Checksums are queryable directly from the registry:

  ```sql
  SELECT cohort_definition_id, definition_checksum, row_count, completed, completed_at
  FROM results.cohort_definition_registry
  ORDER BY cohort_definition_id;
  ```

## Family sharding

Cohorts can carry a `family` tag in `Cohorts.csv`:

```csv
cohort_id,cohort_name,family
1,celecoxib,fam-celecoxib
2,celecoxib-age40,fam-celecoxib
3,ibuprofen,fam-ibuprofen
```

Families are atomic: all cohorts in a family run in one worker so shared
checkpoint reuse is retained. For large sets, run family-balanced shards against
the same target table:

```bash
# 564 families, 10 processes, same target schema/table
docker run --rm ... circe-cohort-runner \
  --shards 10 --max-workers 10

# Write a manifest for Databricks Workflows / Prefect fan-out instead
docker run --rm ... circe-cohort-runner \
  --shards 10 --plan-shards /tmp/shards.json
```

Each shard receives its own `<registry>_sNNN` table; the cohort table is shared.
The driver pre-creates the target and session tables before workers start and
retries failed shards. Start with 10 workers and raise `--shards`/
`--max-workers` gradually while watching Delta concurrency errors.

## Databricks

Set `backend.type="databricks"` and provide `server_hostname`, `http_path`,
`catalog`, `schema`, and `access_token_env`.  The image uses
`circe.execution.connect_databricks()` and therefore the same ibis 12 /
sqlglot compatibility requirements as the library.
