# AskDB - Natural Language to SQL for MySQL

Type what you want in English. AskDB writes the MySQL, checks it, shows it to you,
and runs it on your own MySQL database.

## What it does
1. You type a request ("add a salary column to employees").
2. The backend reads your real schema (tables, columns, primary/foreign keys).
3. Gemini 2.5 Flash writes one MySQL statement from that schema.
4. A validator checks it: one statement only, no comments, role permissions,
   UPDATE/DELETE need a WHERE, system schemas and file access are blocked.
5. Reads (SELECT/SHOW/DESCRIBE) run automatically. Anything that changes data or
   structure waits for your confirmation (UPDATE/DELETE can preview affected rows).
   DROP/TRUNCATE also need the `admin` role and you must type CONFIRM.
6. Results appear in a table with search, sort, pagination, CSV export, stats and charts.
7. If MySQL returns an error, the AI can fix it (max 2 tries). Read queries re-run
   automatically; writes come back as a suggestion you must confirm.
8. Every run is stored in History and written to an audit log.

The stage list in the UI shows measured times from the backend, not fake progress.

## Run it (Windows 11, PowerShell)
Needs Python 3.12, Node.js 18+, a running MySQL 8, and a Gemini API key.

Backend (terminal 1):
    cd backend
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env
    notepad .env          # set GEMINI_API_KEY (and MySQL details if you want auto-connect)
    uvicorn app.main:app --reload --port 8000

Frontend (terminal 2):
    cd frontend
    npm install
    npm run dev

Open http://localhost:5173 and connect to your MySQL.

If PowerShell blocks the venv script:
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Tests: `cd backend; pytest`

## Roles (APP_ROLE in backend/.env)
- readonly: SELECT, SHOW, DESCRIBE only
- write: plus INSERT, UPDATE, DELETE, CREATE, ALTER (default)
- admin: plus DROP and TRUNCATE
Also use a least-privilege MySQL user, for example:
    CREATE USER 'askdb'@'localhost' IDENTIFIED BY 'strong-password';
    GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON mydb.* TO 'askdb'@'localhost';

## API
POST /api/v1/database/connect | GET status, list, schema, tables, tables/{name} | POST select
POST /api/v1/ai/generate-sql
POST /api/v1/query/validate | preview | execute
GET  /api/v1/query/history, /history/{id}, /stats
Docs: http://localhost:8000/docs

## Layout
backend/app: api, core, database, schemas, services, ai, sql_engine, security
frontend/src: components, services

## Limits
- DDL (CREATE/ALTER/DROP) commits immediately in MySQL and cannot be rolled back.
- The SQL editor is a plain text box (no syntax colors).
- Row counts in the explorer are MySQL's estimates.
- Values come from the AI inside the SQL text, so parameterized queries are not used;
  the validator, confirmation step and MySQL permissions are the protection.
