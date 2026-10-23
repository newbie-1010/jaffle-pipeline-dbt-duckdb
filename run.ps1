python ingest\ingest.py
if ($LASTEXITCODE -ne 0) { exit 1 }

dbt source freshness
if ($LASTEXITCODE -ne 0) { exit 1 }

dbt build
if ($LASTEXITCODE -ne 0) { exit 1 }

dbt docs generate