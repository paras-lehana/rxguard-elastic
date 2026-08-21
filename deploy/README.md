# Deployment

The live deployment on the Lehana platform keeps its Docker configs under
`/root/docker/` per that platform's layout rules. These are verbatim copies so
the repository is self-contained and reproducible by anyone cloning it.

| File | Live location |
|------|---------------|
| `Dockerfile.portal` | `/root/docker/pharma-frontend/Dockerfile` |
| `docker-compose.portal.yml` | `/root/docker/pharma-frontend/docker-compose.yml` |
| `docker-compose.elasticsearch.yml` | `/root/docker/rxguard-es/docker-compose.yml` |

## Bring the stack up

```bash
# 1. Elasticsearch — the retrieval core.
#    Set ELASTIC_PASSWORD in a .env beside the compose file first.
docker compose -f docker-compose.elasticsearch.yml up -d

# 2. Create indices and seed the curated pharmacological pairs
ES_URL=http://localhost:9200 python scripts/bootstrap_elastic.py

# 3. Ingest the CDSCO gazette corpus
ES_URL=http://localhost:9200 python scripts/ingest_gazettes.py

# 4. Mine banned FDCs back out of the corpus.
#    ALWAYS dry-run first and read the rows — a false ban is the worst error
#    this system can make.
ES_URL=http://localhost:9200 python scripts/mine_banned_fdcs.py
ES_URL=http://localhost:9200 python scripts/mine_banned_fdcs.py --commit

# 5. The portal
docker compose -f docker-compose.portal.yml up -d --build
```

## Notes

- Elasticsearch is **never** published through the reverse proxy. It binds to the
  internal Docker network plus `127.0.0.1:9200` for host-side scripts.
- The portal runs under gunicorn with a 600s timeout, sized for N×N medication
  screens that issue one LLM call per pair.
- After recreating the portal container, the reverse-proxy route can 404 for
  30-60s while the Docker provider re-syncs. Warm it before probing asset URLs —
  a CDN in front will happily cache those 404s.
