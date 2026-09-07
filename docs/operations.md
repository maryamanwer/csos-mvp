# Local operation and deployment handover

## Start the development demonstration

Install Docker Desktop with Compose support. Extract the source archive, enter its `csos-mvp` directory, then run:

```sh
docker compose up --build -d
docker compose exec ollama ollama pull llama3.1
```

Open http://localhost:3000. Development login: admin@csos.com / csos-demo. API docs: http://localhost:8000/docs. A model download requires network access and sufficient disk/RAM. For an air-gapped site, prepare container images and model weights on a connected staging machine and transfer them through your approved process before starting the site.

Compose starts PostgreSQL and Neo4j, imports the graph seed, and runs the backend database bootstrap. Bootstrap creates the new conversation/workflow tables on startup. Existing table alterations still need reviewed migrations; this is not a production migration framework.

## Walkthrough

1. Log in as Admin and create an asset. Set its criticality and exposure.
2. Create a vulnerability linked to the asset. Open Risk Dashboard and inspect the formula.
3. Open Custom Standards. Enter a reference ID, name, framework, and semicolon-separated asset IDs. Save; inspect Compliance and Topology.
4. Ask Chat about assets. Check selected model, agent trace and evidence IDs. Ask a follow-up in the same page session.
5. Generate PDF and Excel reports. Download both from history.
6. Create a workflow and progress open → in_progress → resolved → closed. Read its notification.
7. Sign in as another user and verify private report/workflow records are inaccessible.

## Troubleshooting

```sh
docker compose ps
docker compose logs --tail=100 backend
docker compose logs --tail=100 neo4j
docker compose exec ollama ollama list
```

AI 503 means the configured runtime/model could not respond. Check model installation and AI environment settings. Uploaded files must follow the schema shown on the Standards screen. A failed import appears in history after graph processing begins; invalid input is rejected before persistence. Report downloads require the generating user's authenticated session and an existing report volume.

## Data retention and backups

Persist all four volumes: PostgreSQL, Neo4j, Ollama, and report files. Back up PostgreSQL with pg_dump and Neo4j using its supported backup/dump procedure for the installed edition. Back up report files together with PostgreSQL report metadata. Test restoration into a separate environment before relying on backups. Do not use `docker compose down -v` when data must be retained.

## Before production

The checked-in Compose and .env.example are demonstration settings. Replace the JWT secret, database credentials and demo administrator password; disable DEBUG; restrict CORS and published database ports; terminate HTTPS at a managed reverse proxy; restrict host access; define retention for chat, reports and audit records. Review dependency advisories and pin validated versions/images. Establish migrations, backups, restore drills and service monitoring. A full integration/security acceptance review is still required.

## Developer verification

```sh
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
cd ../frontend
npm install
npm run build
```

The archive also includes pnpm-lock.yaml from the tested dependency resolution. For matching frontend dependencies, use pnpm with this lockfile. Tests substitute SQLite and fake graph/model responses; run the walkthrough with real services as a separate integration check.
