# Job Readiness Agentic AI

A full-stack app that evaluates a candidate’s job readiness using multiple AI agents powered by Groq.

## Features

- Resume upload and text extraction
- Optional GitHub, LeetCode, and portfolio analysis
- Multi-agent scoring workflow with structured JSON responses
- React dashboard with score visualization

## Requirements

- Python 3.10+
- Node.js 18+
- npm 9+
- A Groq API key

## 1) Clone and open the project

```bash
cd d:\eec\agenticai
```

## 2) Backend setup

Create a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r backend/requirements.txt
```

Set your Groq API key:

Create a file named `.env` in the project root with:

```env
GROQ_API_KEY=your_groq_api_key
```

On Windows PowerShell, you can also load it for the current session:

```powershell
$env:GROQ_API_KEY="your_groq_api_key"
```

Start the backend:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010
```

The API will be available at:

- http://127.0.0.1:8010/api/dashboard

## 3) Frontend setup

Open a new terminal and run:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

- http://127.0.0.1:5173

## 4) Use the app

1. Open the frontend in your browser.
2. Upload a resume PDF or DOCX file.
3. Optionally add GitHub, LeetCode, and portfolio links.
4. Click "Check Your Score".

## 5) API endpoints

- POST /api/upload-resume
- POST /api/github-analysis
- POST /api/leetcode-analysis
- POST /api/portfolio-analysis
- POST /api/job-score
- GET /api/dashboard
- GET /api/report

## 6) Notes

- If Groq credentials are missing, the app will return an error response instead of scoring.
- The current prototype uses a simple scoring workflow and can be expanded with Redis caching, WebSocket progress updates, and downloadable reports.
