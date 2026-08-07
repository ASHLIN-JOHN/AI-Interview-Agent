import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

type AnyRecord = Record<string, any>;

function ResumeAnalyzerPage() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [githubUrl, setGithubUrl] = useState('');
  const [leetcodeUrl, setLeetcodeUrl] = useState('');
  const [portfolioUrl, setPortfolioUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnyRecord | null>(null);
  const [progress, setProgress] = useState<string>('Ready to analyze');

  const handleSubmit = async () => {
    if (!resumeFile) {
      alert('Please upload a resume first.');
      return;
    }

    setLoading(true);
    setProgress('Uploading resume...');

    const formData = new FormData();
    formData.append('file', resumeFile);

    try {
      const uploadResponse = await fetch(`${API_BASE}/api/upload-resume`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        const text = await uploadResponse.text();
        throw new Error(text || 'Resume upload failed');
      }

      const uploadJson = await uploadResponse.json();
      if (!uploadJson?.success || !uploadJson?.resume_text?.trim()) {
        throw new Error(uploadJson?.message || 'Could not extract text from the uploaded resume.');
      }

      setProgress('Analyzing real resume, GitHub, and LeetCode data...');

      const scoreResponse = await fetch(`${API_BASE}/api/job-score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: uploadJson.resume_text,
          github_url: githubUrl,
          leetcode_url: leetcodeUrl,
          portfolio_url: portfolioUrl,
        }),
      });

      if (!scoreResponse.ok) {
        const raw = await scoreResponse.text();
        let message = raw;
        try {
          const parsed = JSON.parse(raw);
          message = parsed?.detail?.message || parsed?.detail || parsed?.message || raw;
          if (typeof message !== 'string') {
            message = JSON.stringify(message);
          }
        } catch {
          message = raw;
        }
        throw new Error(message || 'Scoring request failed');
      }

      const scoreJson = await scoreResponse.json();
      setResult(scoreJson);
      setProgress('Analysis complete');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed';
      setProgress(message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const chartData = result
    ? [
        { name: 'Resume', value: result.components?.resume_quality || 0 },
        { name: 'GitHub', value: result.components?.github_profile || 0 },
        { name: 'Projects', value: result.components?.projects || 0 },
        { name: 'Coding', value: result.components?.coding_platforms || 0 },
        { name: 'Portfolio', value: result.components?.portfolio || 0 },
      ]
    : [];

  const getList = (value: unknown): string[] => {
    if (!Array.isArray(value)) {
      return [];
    }
    return value.filter((item) => typeof item === 'string' && item.trim().length > 0) as string[];
  };

  const resumeRecommendations = getList(result?.resume_agent?.recommendations);
  const githubRecommendations = getList(result?.github_agent?.recommendations);
  const projectRecommendations = getList(result?.project_analysis?.projects?.flatMap((p: any) => p?.improvements || []));
  const extractedProjects = Array.isArray(result?.project_analysis?.projects) ? result.project_analysis.projects : [];

  const solved = result?.leetcode_context?.solved || {};
  const leetcodeChartData = [
    { name: 'Easy', value: solved.easy || 0 },
    { name: 'Medium', value: solved.medium || 0 },
    { name: 'Hard', value: solved.hard || 0 },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Agentic AI</p>
            <h1 className="text-3xl font-semibold">Resume Analyzer</h1>
          </div>
          <Link to="/" className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-900">
            Back to Main Page
          </Link>
        </div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-2xl">
          <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Real Data Mode</p>
              <h2 className="mt-3 text-4xl font-semibold">Resume, GitHub, and LeetCode verification</h2>
              <p className="mt-4 text-slate-300">This page uses extracted resume text, GitHub API data, and LeetCode solved counts from your public profile page.</p>

              <div className="mt-6 space-y-4">
                <label className="block rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                  <span className="mb-2 block text-sm text-slate-400">Resume (PDF or DOCX)</span>
                  <input type="file" accept=".pdf,.docx" onChange={(e) => setResumeFile(e.target.files?.[0] || null)} className="w-full text-sm text-slate-200" />
                </label>
                <input value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)} placeholder="GitHub profile URL" className="w-full rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3" />
                <input value={leetcodeUrl} onChange={(e) => setLeetcodeUrl(e.target.value)} placeholder="LeetCode profile URL (e.g. https://leetcode.com/u/username/)" className="w-full rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3" />
                <input value={portfolioUrl} onChange={(e) => setPortfolioUrl(e.target.value)} placeholder="Portfolio URL (optional)" className="w-full rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3" />

                <button onClick={handleSubmit} disabled={loading} className="w-full rounded-2xl bg-cyan-500 px-4 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-70">
                  {loading ? 'Analyzing...' : 'Run Analysis'}
                </button>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
                <p className="font-medium">Live progress</p>
                <p className="mt-1 text-slate-400">{progress}</p>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              {result ? (
                <>
                  <div className="flex items-end justify-between">
                    <div>
                      <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Overall Job Readiness</p>
                      <h2 className="mt-2 text-5xl font-semibold">{result.overall_job_score}%</h2>
                    </div>
                    <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-cyan-300">
                      {result.interview_chance}% interview chance
                    </div>
                  </div>

                  <div className="mt-6 h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                        <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                        <Tooltip />
                        <Bar dataKey="value" fill="#22d3ee" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </>
              ) : (
                <div className="flex h-full items-center justify-center text-slate-400">No analysis yet. Upload a resume and profile links to begin.</div>
              )}
            </div>
          </div>
        </motion.div>

        {result && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-2xl">
            <h3 className="text-2xl font-semibold">Exact LeetCode Solved Data</h3>
            <p className="mt-2 text-slate-300">
              Total solved: <span className="font-semibold text-cyan-300">{solved.total || 0}</span>
              {' '}| Easy: {solved.easy || 0} | Medium: {solved.medium || 0} | Hard: {solved.hard || 0}
            </p>
            <p className="mt-2 text-slate-300">{result?.leetcode_context?.comment || 'No LeetCode comment returned.'}</p>

            <div className="mt-5 h-60 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={leetcodeChartData}>
                  <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#22d3ee" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <h3 className="mt-8 text-2xl font-semibold">Targeted Improvements</h3>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
                <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">Resume Improvements</p>
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {resumeRecommendations.length > 0 ? resumeRecommendations.map((item, idx) => <li key={`resume-${idx}`}>- {item}</li>) : <li>No resume recommendations were returned in this result.</li>}
                </ul>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
                <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">GitHub Improvements</p>
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {githubRecommendations.length > 0 ? githubRecommendations.map((item, idx) => <li key={`github-${idx}`}>- {item}</li>) : <li>No GitHub recommendations were returned in this result.</li>}
                </ul>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
                <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">Project Improvements</p>
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {projectRecommendations.length > 0 ? projectRecommendations.map((item, idx) => <li key={`project-${idx}`}>- {item}</li>) : <li>No project improvements were returned in this result.</li>}
                </ul>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
              <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">Projects Extracted From Resume</p>
              {extractedProjects.length === 0 ? (
                <p className="mt-3 text-sm text-slate-300">No projects were extracted from the resume text.</p>
              ) : (
                <div className="mt-4 space-y-4">
                  {extractedProjects.map((project: any, idx: number) => (
                    <div key={`extracted-project-${idx}`} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <p className="font-semibold text-slate-100">{project?.name || `Project ${idx + 1}`}</p>
                      <p className="mt-2 text-sm text-slate-300">{project?.explanation || 'No explanation returned.'}</p>
                      <p className="mt-2 text-xs text-slate-400">Evidence from resume: {project?.evidence || 'Not provided'}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default ResumeAnalyzerPage;
