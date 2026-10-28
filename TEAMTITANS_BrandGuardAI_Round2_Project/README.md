# BrandGuard AI — TEAMTITANS

A Flask prototype for the Inkloom AI brand-governance problem statement.

## Features implemented
- Add brand rules: phrase to avoid, phrase to include, and preferred-term checks
- Paste text and run checks against active rules
- See explanations and suggested next steps for each flag
- Save review history in SQLite
- Human review decision: Needs review, Approved by human, or Changes requested
- Simple heuristic nudges for bare URLs and long copy
- Health endpoint at `/health`

## Important limitations
This MVP uses deterministic phrase matching, not a general AI model. A "no issues found" result does not prove that content is factually accurate or compliant. It does not currently inspect images, verify claims against external sources, support user accounts, or provide multi-user permissions. Do not enter confidential material in a public demo.

## Run locally
Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Publish with Render
1. Create a GitHub repository and upload these project files.
2. In Render, choose New > Web Service and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Deploy, then test the public URL on another device/incognito.
6. Note: local SQLite storage on some hosts may reset on redeploy. For a persistent production deployment, attach a persistent disk or move to a managed database.

## Suggested Round 3 improvements
1. Evidence-backed claim checking against a curated, approved fact library with source references.
2. Image/logo and basic accessibility checks for uploaded campaign assets.
3. Role-based reviewer workflow with change history and analytics for repeated issues.

## Team roles (confirm actual work before submission)
- Varsha: Backend Developer & Technical Lead
- Yuvashree: Frontend Developer
- Joyal: Product Planning, Research & Documentation

Use only the claims that match what the team has actually built and tested. Review all files before submitting.
