import os
import json
import re
import tempfile
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
import requests
from bs4 import BeautifulSoup

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

app = FastAPI(title="Job Readiness Agentic AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = None


def get_client() -> Groq:
    global client
    if client is None:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return client


class JobScoreRequest(BaseModel):
    resume_text: str
    github_url: Optional[str] = None
    leetcode_url: Optional[str] = None
    portfolio_url: Optional[str] = None

class AnalysisResult(BaseModel):
    score: float
    confidence: float
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    reasoning: str


class RoadmapRequest(BaseModel):
    prompt: str
    weeks: Optional[int] = 12


def ensure_client() -> Groq:
    return get_client()


def parse_structured_json(content: str) -> Dict[str, Any]:
    raw = (content or "").strip()
    if not raw:
        raise ValueError("Model returned empty content")

    # Accept strict JSON or JSON wrapped in markdown fences.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_github_username(github_url: str) -> Optional[str]:
    if not github_url:
        return None
    try:
        parsed = urlparse(github_url)
        path = (parsed.path or "").strip("/")
        if not path:
            return None
        return path.split("/")[0]
    except Exception:
        return None


def get_github_context(github_url: Optional[str]) -> Dict[str, Any]:
    if not github_url:
        return {"available": False, "reason": "GitHub URL not provided."}

    username = extract_github_username(github_url)
    if not username:
        return {"available": False, "reason": "Invalid GitHub profile URL."}

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "job-readiness-agentic-ai",
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        profile_resp = requests.get(
            f"https://api.github.com/users/{username}",
            headers=headers,
            timeout=12,
        )
        if profile_resp.status_code != 200:
            profile_body = {}
            try:
                profile_body = profile_resp.json()
            except Exception:
                profile_body = {}
            return {
                "available": False,
                "reason": f"GitHub profile API returned {profile_resp.status_code}",
                "profile_api_status": profile_resp.status_code,
                "rate_limit_remaining": profile_resp.headers.get("X-RateLimit-Remaining"),
                "api_message": profile_body.get("message"),
                "username": username,
            }

        profile = profile_resp.json()
        repos_resp = requests.get(
            f"https://api.github.com/users/{username}/repos?per_page=20&sort=updated",
            headers=headers,
            timeout=12,
        )
        repos = repos_resp.json() if repos_resp.status_code == 200 else []

        top_repos = sorted(
            [
                {
                    "name": r.get("name"),
                    "stargazers_count": r.get("stargazers_count", 0),
                    "forks_count": r.get("forks_count", 0),
                    "language": r.get("language"),
                    "updated_at": r.get("updated_at"),
                }
                for r in repos
                if isinstance(r, dict)
            ],
            key=lambda x: x.get("stargazers_count", 0),
            reverse=True,
        )[:5]

        languages = sorted(
            {
                r.get("language")
                for r in repos
                if isinstance(r, dict) and r.get("language")
            }
        )

        return {
            "available": True,
            "profile_api_status": profile_resp.status_code,
            "repos_api_status": repos_resp.status_code,
            "rate_limit_remaining": repos_resp.headers.get("X-RateLimit-Remaining"),
            "username": username,
            "name": profile.get("name"),
            "bio": profile.get("bio"),
            "public_repos": profile.get("public_repos", 0),
            "followers": profile.get("followers", 0),
            "following": profile.get("following", 0),
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at"),
            "languages": languages,
            "top_repos": top_repos,
        }
    except Exception as exc:
        return {
            "available": False,
            "reason": f"Failed to fetch GitHub data: {str(exc)}",
            "username": username,
        }


def find_key_deep(obj: Any, target_key: str) -> Any:
    if isinstance(obj, dict):
        if target_key in obj:
            return obj[target_key]
        for value in obj.values():
            result = find_key_deep(value, target_key)
            if result is not None:
                return result
    if isinstance(obj, list):
        for item in obj:
            result = find_key_deep(item, target_key)
            if result is not None:
                return result
    return None


def extract_leetcode_username(leetcode_url: str) -> Optional[str]:
    if not leetcode_url:
        return None
    try:
        parsed = urlparse(leetcode_url)
        path_parts = [part for part in (parsed.path or "").split("/") if part]
        if not path_parts:
            return None
        if path_parts[0] == "u" and len(path_parts) >= 2:
            return path_parts[1]
        return path_parts[0]
    except Exception:
        return None


def build_leetcode_comment(total: int, easy: int, medium: int, hard: int) -> str:
    if total == 0:
        return "No solved submissions found yet. Start with easy problems and build a daily streak."
    if hard >= 150:
        return "Strong advanced problem-solving profile with significant hard-problem completion."
    if medium >= 200:
        return "Solid interview readiness in core DSA areas; continue increasing hard-problem coverage."
    if easy >= 150 and medium < 120:
        return "Good foundations on easy problems. Focus now on medium-level patterns to improve interview outcomes."
    return "Consistent progress detected. Improve by balancing medium and hard problems with topic-wise practice."


def build_leetcode_recommendations(total: int, easy: int, medium: int, hard: int) -> list[str]:
    recs: list[str] = []
    if total < 100:
        recs.append("Target the first 100 solved problems with a strict weekly plan.")
    if medium < max(60, easy // 2):
        recs.append("Increase medium-level problems to improve coding interview success rate.")
    if hard < max(20, medium // 5):
        recs.append("Add at least 2 hard problems per week to strengthen advanced reasoning.")
    recs.append("Track mistakes by topic (arrays, graphs, DP, trees) and do spaced revision.")
    return recs[:4]


def score_leetcode(total: int, easy: int, medium: int, hard: int) -> float:
    weighted = easy * 1 + medium * 2 + hard * 3
    # 800 weighted points maps to 100.
    return min(100.0, round((weighted / 800.0) * 100.0, 1))


def get_leetcode_stats_via_graphql(username: str) -> Optional[Dict[str, Any]]:
    graphql_url = "https://leetcode.com/graphql"
    payload = {
        "query": """
query userPublicProfile($username: String!) {
  matchedUser(username: $username) {
    username
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
""",
        "variables": {"username": username},
        "operationName": "userPublicProfile",
    }

    headers = {
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/u/{username}/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) "
            "Gecko/20100101 Firefox/141.0"
        ),
    }

    try:
        response = requests.post(graphql_url, json=payload, headers=headers, timeout=20)
        if response.status_code != 200:
            return None
        body = response.json()
        matched_user = ((body.get("data") or {}).get("matchedUser") or {})
        submit_stats = (matched_user.get("submitStatsGlobal") or {}).get("acSubmissionNum")
        if not isinstance(submit_stats, list):
            return None

        solved_by_diff: Dict[str, int] = {
            "All": 0,
            "Easy": 0,
            "Medium": 0,
            "Hard": 0,
        }
        for entry in submit_stats:
            if not isinstance(entry, dict):
                continue
            difficulty = entry.get("difficulty")
            count = entry.get("count")
            if difficulty in solved_by_diff:
                try:
                    solved_by_diff[difficulty] = int(count)
                except Exception:
                    solved_by_diff[difficulty] = 0

        total = solved_by_diff.get("All", 0)
        easy = solved_by_diff.get("Easy", 0)
        medium = solved_by_diff.get("Medium", 0)
        hard = solved_by_diff.get("Hard", 0)
        computed_total = easy + medium + hard
        if total == 0 and computed_total > 0:
            total = computed_total

        return {
            "source": "graphql",
            "solved": {
                "total": total,
                "easy": easy,
                "medium": medium,
                "hard": hard,
            },
        }
    except Exception:
        return None


def get_leetcode_context(leetcode_url: Optional[str]) -> Dict[str, Any]:
    if not leetcode_url:
        return {
            "available": False,
            "reason": "LeetCode URL not provided.",
        }

    username = extract_leetcode_username(leetcode_url)
    if not username:
        return {
            "available": False,
            "reason": "Invalid LeetCode URL.",
        }

    url = f"https://leetcode.com/u/{username}/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) "
            "Gecko/20100101 Firefox/141.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            graphql_stats = get_leetcode_stats_via_graphql(username)
            if graphql_stats is not None:
                solved = graphql_stats.get("solved", {})
                total = int(solved.get("total", 0))
                easy = int(solved.get("easy", 0))
                medium = int(solved.get("medium", 0))
                hard = int(solved.get("hard", 0))
                return {
                    "available": True,
                    "username": username,
                    "profile_url": url,
                    "status_code": response.status_code,
                    "source": "graphql-fallback",
                    "solved": {
                        "total": total,
                        "easy": easy,
                        "medium": medium,
                        "hard": hard,
                    },
                    "leetcode_score": score_leetcode(total, easy, medium, hard),
                    "comment": build_leetcode_comment(total, easy, medium, hard),
                    "recommendations": build_leetcode_recommendations(total, easy, medium, hard),
                }
            return {
                "available": False,
                "username": username,
                "status_code": response.status_code,
                "reason": "Failed to load LeetCode profile page.",
            }

        soup = BeautifulSoup(response.text, "html.parser")
        next_data_script = soup.find("script", id="__NEXT_DATA__")
        if next_data_script is None or not next_data_script.string:
            graphql_stats = get_leetcode_stats_via_graphql(username)
            if graphql_stats is not None:
                solved = graphql_stats.get("solved", {})
                total = int(solved.get("total", 0))
                easy = int(solved.get("easy", 0))
                medium = int(solved.get("medium", 0))
                hard = int(solved.get("hard", 0))
                return {
                    "available": True,
                    "username": username,
                    "profile_url": url,
                    "status_code": response.status_code,
                    "source": "graphql-fallback",
                    "solved": {
                        "total": total,
                        "easy": easy,
                        "medium": medium,
                        "hard": hard,
                    },
                    "leetcode_score": score_leetcode(total, easy, medium, hard),
                    "comment": build_leetcode_comment(total, easy, medium, hard),
                    "recommendations": build_leetcode_recommendations(total, easy, medium, hard),
                }
            return {
                "available": False,
                "username": username,
                "status_code": response.status_code,
                "reason": "Unable to read LeetCode profile data from page.",
            }

        payload = json.loads(next_data_script.string)
        ac_submission_num = find_key_deep(payload, "acSubmissionNum")
        if not isinstance(ac_submission_num, list):
            graphql_stats = get_leetcode_stats_via_graphql(username)
            if graphql_stats is not None:
                solved = graphql_stats.get("solved", {})
                total = int(solved.get("total", 0))
                easy = int(solved.get("easy", 0))
                medium = int(solved.get("medium", 0))
                hard = int(solved.get("hard", 0))
                return {
                    "available": True,
                    "username": username,
                    "profile_url": url,
                    "status_code": response.status_code,
                    "source": "graphql-fallback",
                    "solved": {
                        "total": total,
                        "easy": easy,
                        "medium": medium,
                        "hard": hard,
                    },
                    "leetcode_score": score_leetcode(total, easy, medium, hard),
                    "comment": build_leetcode_comment(total, easy, medium, hard),
                    "recommendations": build_leetcode_recommendations(total, easy, medium, hard),
                }
            return {
                "available": False,
                "username": username,
                "status_code": response.status_code,
                "reason": "Solved-count data not found on profile page.",
            }

        solved_by_diff: Dict[str, int] = {
            "All": 0,
            "Easy": 0,
            "Medium": 0,
            "Hard": 0,
        }
        for entry in ac_submission_num:
            if not isinstance(entry, dict):
                continue
            difficulty = entry.get("difficulty")
            count = entry.get("count")
            if difficulty in solved_by_diff:
                try:
                    solved_by_diff[difficulty] = int(count)
                except Exception:
                    solved_by_diff[difficulty] = 0

        total = solved_by_diff.get("All", 0)
        easy = solved_by_diff.get("Easy", 0)
        medium = solved_by_diff.get("Medium", 0)
        hard = solved_by_diff.get("Hard", 0)
        computed_total = easy + medium + hard
        if total == 0 and computed_total > 0:
            total = computed_total

        return {
            "available": True,
            "username": username,
            "profile_url": url,
            "status_code": response.status_code,
            "solved": {
                "total": total,
                "easy": easy,
                "medium": medium,
                "hard": hard,
            },
            "leetcode_score": score_leetcode(total, easy, medium, hard),
            "comment": build_leetcode_comment(total, easy, medium, hard),
            "recommendations": build_leetcode_recommendations(total, easy, medium, hard),
        }
    except Exception as exc:
        return {
            "available": False,
            "username": username,
            "reason": f"Failed to fetch LeetCode profile data: {str(exc)}",
        }


def run_groq_agent(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    if not os.getenv("GROQ_API_KEY"):
        return {
            "error": "GROQ_API_KEY is missing",
            "source": "groq_error",
        }

    try:
        response = ensure_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
            top_p=1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return parse_structured_json(content)
    except Exception as exc:
        return {
            "error": str(exc),
            "source": "groq_error",
        }


def run_groq_agent_required(system_prompt: str, user_prompt: str, agent_name: str) -> Dict[str, Any]:
    result = run_groq_agent(system_prompt, user_prompt)
    if result.get("source") == "groq_error":
        raise HTTPException(status_code=502, detail=f"{agent_name} failed: {result.get('error', 'Unknown Groq error')}")
    return result


def normalize_score(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        score = float(value)
        # Normalize 0-10 rubric outputs into 0-100 percentage scale.
        if 0.0 <= score <= 10.0:
            score = score * 10.0
        return min(100.0, max(0.0, score))
    except Exception:
        return None


def weighted_average(items: list[tuple[Optional[float], float]]) -> Optional[float]:
    valid = [(score, weight) for score, weight in items if score is not None]
    if not valid:
        return None
    total_weight = sum(weight for _, weight in valid)
    if total_weight <= 0:
        return None
    return sum(score * weight for score, weight in valid) / total_weight


def extract_projects_from_resume(resume_text: str) -> Dict[str, Any]:
    return run_groq_agent_required(
        (
            "You are a strict resume project extractor. "
            "Only use facts that explicitly appear in the resume text. "
            "Return valid JSON only with keys: project_score, summary, projects. "
            "projects must be an array of objects with keys: name, evidence, explanation, improvements. "
            "Do not invent projects. If no project evidence exists, return projects as an empty array."
        ),
        (
            "Extract and explain projects from this resume text. "
            "Also provide concrete project improvement suggestions for each extracted project.\n\n"
            f"Resume:\n{resume_text}"
        ),
        "Project extraction agent",
    )


async def extract_resume_text(file_path: str, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(page for page in pages if page)
        except Exception:
            return ""
    if filename.lower().endswith((".docx", ".doc")):
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text)
        except Exception:
            return ""

    path = Path(file_path)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")
    return ""


def normalize_roadmap_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"title": "Roadmap", "overview": "", "total_weeks": 12, "nodes": []}

    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        nodes = []

    def normalize_node(node: Any, index: int = 0) -> Dict[str, Any]:
        if not isinstance(node, dict):
            return {
                "id": f"node-{index}",
                "title": "Untitled",
                "start_week": None,
                "end_week": None,
                "details": "",
                "children": [],
            }

        title = node.get("title") or node.get("name") or f"Step {index + 1}"
        details = node.get("details") or node.get("description") or ""
        if not details:
            tasks = node.get("tasks")
            if isinstance(tasks, list) and tasks:
                details = "; ".join(str(task) for task in tasks if str(task).strip())
            elif isinstance(node.get("milestones"), list):
                details = "; ".join(str(m) for m in node.get("milestones") if str(m).strip())

        children = node.get("children")
        if not isinstance(children, list):
            children = []

        return {
            "id": str(node.get("id") or f"node-{index + 1}"),
            "title": str(title),
            "start_week": node.get("start_week"),
            "end_week": node.get("end_week"),
            "details": str(details),
            "children": [normalize_node(child, i) for i, child in enumerate(children)],
        }

    normalized_nodes = [normalize_node(node, i) for i, node in enumerate(nodes)]
    return {
        "title": str(payload.get("title") or "Roadmap"),
        "overview": str(payload.get("overview") or ""),
        "total_weeks": int(payload.get("total_weeks") or 12),
        "nodes": normalized_nodes,
    }


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    temp_path = None
    try:
        ext = os.path.splitext(file.filename or "")[1] or ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        resume_text = await extract_resume_text(temp_path, file.filename or "")
        if not resume_text.strip():
            return {
                "success": False,
                "filename": file.filename,
                "resume_text": "",
                "extracted_chars": 0,
                "message": "Could not extract any readable text from the uploaded file. Please upload a PDF, DOCX, or a plain text file.",
            }
        return {
            "success": True,
            "filename": file.filename,
            "resume_text": resume_text[:4000],
            "extracted_chars": len(resume_text),
            "message": "Resume uploaded and extracted successfully.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/github-analysis")
async def github_analysis(payload: JobScoreRequest):
    github_context = get_github_context(payload.github_url)
    prompt = (
        "Analyze the following GitHub profile context and return structured JSON. "
        "If profile data is unavailable, return a neutral score and explain why.\n\n"
        f"GitHub context: {json.dumps(github_context)}"
    )
    result = run_groq_agent(
        "You are a senior tech recruiter. Return valid JSON only with keys score, confidence, summary, strengths, weaknesses, recommendations, reasoning.",
        prompt,
    )
    return result


@app.post("/api/leetcode-analysis")
async def leetcode_analysis(payload: JobScoreRequest):
    leetcode_context = get_leetcode_context(payload.leetcode_url)
    prompt = (
        "Analyze the following LeetCode profile context and return structured JSON. "
        "Use only the provided solved data and do not invent numbers.\n\n"
        f"LeetCode context: {json.dumps(leetcode_context)}"
    )
    result = run_groq_agent(
        "You are a senior software engineering recruiter. Return valid JSON only.",
        prompt,
    )
    return {
        "leetcode_context": leetcode_context,
        "analysis": result,
    }


@app.post("/api/portfolio-analysis")
async def portfolio_analysis(payload: JobScoreRequest):
    prompt = f"Analyze the following portfolio context and return structured JSON. If the portfolio link is missing, return a neutral score and say the data was unavailable.\n\nPortfolio: {payload.portfolio_url or 'Not provided'}"
    result = run_groq_agent(
        "You are a hiring manager for product and engineering roles. Return valid JSON only.",
        prompt,
    )
    return result


@app.post("/api/job-score")
async def job_score(payload: JobScoreRequest):
    resume_text = (payload.resume_text or "").strip()
    if not resume_text:
        raise HTTPException(status_code=422, detail="Resume text is required.")

    github_context = get_github_context(payload.github_url)
    leetcode_context = get_leetcode_context(payload.leetcode_url)

    project_analysis = extract_projects_from_resume(resume_text)
    projects = project_analysis.get("projects") if isinstance(project_analysis.get("projects"), list) else []
    if len(projects) == 0:
        raise HTTPException(
            status_code=422,
            detail="No projects were detected in the uploaded resume. Add a Projects section with explicit project details.",
        )

    if payload.github_url and not github_context.get("available"):
        raise HTTPException(
            status_code=424,
            detail={
                "message": "GitHub data could not be fetched. Provide a valid GITHUB_TOKEN or retry after rate-limit reset.",
                "github_context": github_context,
            },
        )

    resume_result = run_groq_agent_required(
        "You are an expert recruiter. Return valid JSON only with keys score, confidence, summary, strengths, weaknesses, recommendations, reasoning. Never hallucinate missing profile data.",
        f"Analyze the resume and return a JSON object with score, confidence, summary, strengths, weaknesses, recommendations, and reasoning. Resume:\n{resume_text}",
        "Resume agent",
    )

    github_result = None
    if payload.github_url:
        github_result = run_groq_agent_required(
            "You are a technical recruiter. Return valid JSON only with keys score, confidence, summary, strengths, weaknesses, recommendations, reasoning.",
            "Evaluate the GitHub profile quality and return JSON with score, confidence, summary, strengths, weaknesses, recommendations, and reasoning. "
            f"GitHub context: {json.dumps(github_context)}",
            "GitHub agent",
        )

    leetcode_result = None
    if leetcode_context.get("available"):
        leetcode_result = {
            "score": leetcode_context.get("leetcode_score"),
            "confidence": 0.9,
            "summary": f"LeetCode solved total: {leetcode_context.get('solved', {}).get('total', 0)}",
            "strengths": [leetcode_context.get("comment", "")],
            "weaknesses": [],
            "recommendations": leetcode_context.get("recommendations", []),
            "reasoning": "Score is computed from exact solved counts scraped from the profile page.",
        }
    portfolio_result = run_groq_agent(
        "You are a technical recruiter. Return valid JSON only.",
        f"Evaluate the portfolio quality and return JSON with score, confidence, summary, strengths, weaknesses, recommendations, and reasoning. Portfolio: {payload.portfolio_url or 'Not provided'}",
    )

    resume_score = normalize_score(resume_result.get("score"))
    github_score = normalize_score(github_result.get("score")) if github_result else None
    leetcode_score = normalize_score(leetcode_result.get("score")) if leetcode_result else None
    portfolio_score = normalize_score(portfolio_result.get("score"))
    projects_score = normalize_score(project_analysis.get("project_score"))

    if resume_score is None:
        raise HTTPException(status_code=502, detail="Resume scoring did not return a valid numeric score.")
    if payload.github_url and github_score is None:
        raise HTTPException(status_code=502, detail="GitHub scoring did not return a valid numeric score.")
    if projects_score is None:
        raise HTTPException(status_code=502, detail="Project extraction did not return a valid project score.")

    ats_score = resume_score
    professional_score = weighted_average(
        [
            (github_score, 0.5),
            (portfolio_score, 0.25),
            (leetcode_score, 0.25),
        ]
    )

    overall = weighted_average(
        [
            (resume_score, 0.30),
            (projects_score, 0.30),
            (github_score, 0.20),
            (leetcode_score, 0.10),
            (portfolio_score, 0.10),
        ]
    )
    if overall is None:
        raise HTTPException(status_code=502, detail="Unable to compute final score from available data.")

    return {
        "overall_job_score": round(overall, 1),
        "interview_chance": round(min(100, max(0, overall * 0.95)), 1),
        "ats_pass_rate": round(min(100, max(0, ats_score)), 1),
        "hiring_probability": round(min(100, max(0, overall * 0.84)), 1),
        "components": {
            "resume_quality": round(resume_score, 1),
            "github_profile": round(github_score, 1) if github_score is not None else None,
            "projects": round(projects_score, 1),
            "coding_platforms": round(leetcode_score, 1) if leetcode_score is not None else None,
            "portfolio": round(portfolio_score, 1) if portfolio_score is not None else None,
            "ats_compatibility": round(ats_score, 1),
            "professional_presence": round(professional_score, 1) if professional_score is not None else None,
        },
        "resume_agent": resume_result,
        "project_analysis": project_analysis,
        "github_agent": github_result,
        "github_context": github_context,
        "leetcode_agent": leetcode_result,
        "leetcode_context": leetcode_context,
        "portfolio_agent": portfolio_result,
        "data_sources": {
            "resume_projects_detected": len(projects),
            "github_data_available": bool(github_context.get("available")),
        },
    }


@app.get("/api/dashboard")
async def dashboard():
    return {
        "status": "ready",
        "agents": [
            "Resume Analysis Agent",
            "GitHub Analysis Agent",
            "LeetCode Analysis Agent",
            "Portfolio Analysis Agent",
            "ATS Resume Agent",
            "Coding Skill Evaluation Agent",
            "Project Intelligence Agent",
            "Skill Gap Agent",
            "Recruiter Simulation Agent",
            "Career Roadmap Agent",
            "Final Score Aggregation Agent",
        ],
    }



@app.post("/api/roadmap")
async def generate_roadmap(payload: RoadmapRequest):
    if not payload.prompt or not payload.prompt.strip():
        raise HTTPException(status_code=422, detail="A prompt is required to generate a roadmap.")

    system_prompt = (
        "You are a specialist Roadmap Generator. Produce a detailed, tree-structured roadmap for a project. "
        "Return strictly valid JSON (no extra text). The JSON must include: title, overview, total_weeks, "
        "and nodes which is an array representing a tree. Each node must have: id, title, start_week, end_week, "
        "details, and optional children (array of nodes). The structure should be top-to-bottom, with more branches near the leaves. "
        "Assign weeks across nodes so timelines do not overlap incorrectly. Make the roadmap more complex deeper in the tree. "
        "Prefer more branches at the bottom (leaf nodes). Use the provided weeks as the total timeline length unless the prompt overrides it."
    )

    user_prompt = (
        f"Generate a roadmap for the following request. Weeks budget: {int(payload.weeks)}. "
        f"User prompt: {payload.prompt}\n\nReturn the roadmap as JSON following the schema described exactly."
    )

    result = run_groq_agent(system_prompt, user_prompt)
    if result.get("source") == "groq_error":
        raise HTTPException(status_code=502, detail={"message": "Roadmap generation failed", "error": result.get("error")})

    normalized = normalize_roadmap_payload(result)
    if not normalized.get("nodes"):
        normalized = {
            "title": "Roadmap",
            "overview": "A fallback roadmap was generated because the model output was empty.",
            "total_weeks": int(payload.weeks or 12),
            "nodes": [
                {
                    "id": "phase-1",
                    "title": "Foundation",
                    "start_week": 1,
                    "end_week": int(payload.weeks or 12),
                    "details": payload.prompt.strip(),
                    "children": [],
                }
            ],
        }

    return {"roadmap": normalized}


@app.get("/api/report")
async def report():
    return {
        "report": "Job readiness report generated successfully.",
        "download_url": "/api/report/download",
    }
