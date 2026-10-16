# Student Records API

A small Python backend for managing student records with FastAPI and SQLite. It supports the assignment's CRUD, filtering, validation, and persistence requirements. The optional Ollama endpoint is disabled by default.

## Features

- Create, list, retrieve, update (PUT/PATCH), and delete student records.
- SQLite storage with automatic table creation and persistent data.
- Filters for name, course, email, and date-of-birth range.
- Validated ISO dates, email addresses, non-empty names, and contact requirement (email or phone).
- Interactive OpenAPI docs at `/docs`.
- Optional local Ollama integration that receives only records selected by the backend; it cannot execute SQL.

## Prerequisites

- Python 3.10 or newer
- pip
- (Optional AI) Ollama installed and running locally with a model such as `llama3.2:1b`

## Install and run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --env-file .env
```

The API listens at `http://127.0.0.1:8000`. The SQLite database is created at `data/students.db` by default. Set `STUDENT_DB_PATH` to choose another path.

## Publish a public evaluation link with Render

The repository includes `render.yaml` for a public Render Web Service. To deploy it:

1. Copy this project into your GitHub repository and push it to GitHub.
2. Create a Render account, choose **New + → Blueprint**, and connect that GitHub repository.
3. Review the Blueprint resources and deploy. Render will provide an `onrender.com` URL; add `/docs` to open the API documentation.
4. Send the `/docs` URL to your evaluator. Use `/health` to confirm the service is responding.

The Blueprint uses a paid web-service plan and a 1 GB persistent disk so SQLite data survives restarts and deployments. Render Free web services cannot attach persistent disks; their local SQLite files are lost when the service restarts, spins down, or redeploys. Check Render's current pricing before creating the service. The optional Ollama integration remains disabled in the public deployment.

## API reference and examples

The complete interactive reference is at `http://127.0.0.1:8000/docs`.

Create a record:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/students -ContentType 'application/json' -Body '{"student_id":"STU-001","name":"Alex Example","date_of_birth":"2005-04-12","email":"alex@example.com","course":"Python Backend","enrollment_date":"2026-09-01"}'
```

List, filter, and retrieve:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/students
Invoke-RestMethod 'http://127.0.0.1:8000/students?course=Python%20Backend&dob_after=2000-01-01'
Invoke-RestMethod http://127.0.0.1:8000/students/STU-001
```

Update (PATCH modifies only supplied fields; PUT replaces all editable fields):

```powershell
Invoke-RestMethod -Method Patch -Uri http://127.0.0.1:8000/students/STU-001 -ContentType 'application/json' -Body '{"phone":"+1-555-0100"}'
```

Delete:

```powershell
Invoke-RestMethod -Method Delete -Uri http://127.0.0.1:8000/students/STU-001
```

Endpoints return `404` for unknown IDs, `409` for duplicate IDs, and `422` for invalid input. List responses are paginated with `limit` (1-100, default 50) and `offset` (default 0).

## Optional Ollama question answering

Install and start Ollama, then pull a model (example: `ollama pull llama3.2:1b`). Set `AI_ENABLED=true` in `.env` and optionally set `OLLAMA_MODEL` and `OLLAMA_URL`. Restart the API and send:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask -ContentType 'application/json' -Body '{"question":"How many students are there?"}'
```

The backend loads the relevant records and passes those records as context to Ollama. Model output is informational and may be inaccurate; verify it against `/students`. The model receives no database credentials or SQL execution capability. Keep real personal data out of demonstrations and repositories.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

Tests use a temporary SQLite database and synthetic records.

## GitHub submission

Review `git status`, confirm the database and `.env` are not tracked, then create an empty GitHub repository and push this folder:

```powershell
git init
git add .
git commit -m "Build student records API"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace the remote URL with your repository URL. Do not commit real student records, credentials, or `.env`.
