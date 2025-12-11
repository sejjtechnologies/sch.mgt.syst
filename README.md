# Sch.Manager

Primary school management system (Flask + PostgreSQL / Neon).

Quick start (local)

1. Create and activate virtualenv (Windows PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# edit .env and set DATABASE_URL and SECRET_KEY
```

2. Run locally:

```powershell
# from project root
python app.py
```

Deployment (Vercel Docker)

1. Ensure repository pushed to GitHub.
2. In Vercel, import the Git repo. Vercel will use the provided `vercel.json` and `Dockerfile`.
3. In Project Settings → Environment Variables add `DATABASE_URL` and `SECRET_KEY`.

Troubleshooting

- If the Docker build fails with missing system libs (weasyprint, Pillow), update the `Dockerfile` to install required apt packages and re-deploy.
- For Neon Postgres, use the connection string in `DATABASE_URL`.

Contact

Owner: sejjtechnologies (sejjtechnologies@gmail.com)