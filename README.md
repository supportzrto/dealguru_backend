# DealGuru FastAPI backend — Stage 1

## Requirements
- Python 3.11 or newer
- Railway PostgreSQL service

## Setup (Windows PowerShell)
```powershell
cd backend
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```
Edit `.env` and set `DATABASE_URL` to the Railway PostgreSQL connection URL. Never commit `.env`.

## Run
```powershell
uvicorn app.main:app --reload --port 8000
```
Open:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/health/db
- http://127.0.0.1:8000/docs

The SQLAlchemy models are prepared for the next database-migration step. Do not use `create_all()` as the production migration strategy; Stage 1.2 will add Alembic migrations and create the schema deliberately.
