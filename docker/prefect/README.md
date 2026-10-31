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

- Cohorts are generated into a checksum-keyed cache
  (`target.cache_schema`, `target.cache_table`). The study-facing
  `target.schema.target.table` is populated only by a final copy phase using the
  requested integer cohort ids.
- `target.registry_table` (the cache registry) stores checksum, completion,
  row count and timestamps. It does not store full definition JSON/SQL. A cache
  entry is reused by any integer cohort id with the same canonical checksum.
- Cache rows, cache registry and the final cohort table are independent
  parameters; persistent table count does not grow with cohort count.
- Session/staging tables are cleaned by each process and by the independent
  `python -m circe.runner.cleanup --payload /payload.json` job.
- `target.schema`/`cache_schema` must be scratch/results schemas. Circepy warns
  when they are the CDM schema.
- Checksums are queryable directly from the registry:

  ```sql
  SELECT cohort_checksum, row_count, completed, completed_at
  FROM results.cohort_cache_registry
  ORDER BY cohort_checksum;
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
