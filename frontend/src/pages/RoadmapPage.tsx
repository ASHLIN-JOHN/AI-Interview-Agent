import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

type RoadmapNode = {
  id: string;
  title: string;
  start_week?: number;
  end_week?: number;
  details?: string;
  children?: RoadmapNode[];
};

function RenderNode({ node, depth = 0 }: { node: RoadmapNode; depth?: number }) {
  const [childrenOpen, setChildrenOpen] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const hasChildren = Array.isArray(node.children) && node.children.length > 0;
  return (
    <div className="mt-6 font-sans">
      <div className="flex justify-center">
        <motion.div
          layout
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          whileHover={{ scale: 1.01 }}
          onClick={() => setChildrenOpen((s) => !s)}
          role="button"
          tabIndex={0}
          className="relative flex items-center gap-3 rounded-lg border border-slate-100 bg-white p-2 shadow-sm cursor-pointer w-full max-w-4xl"
        >
          <div className="flex items-center justify-center h-9 w-9 rounded-full bg-gradient-to-br from-cyan-300 to-emerald-300 text-slate-900 font-bold text-sm">{node.title ? node.title.charAt(0).toUpperCase() : '?'}</div>

          <div className="text-left flex-1 ml-2">
            <div className="font-medium text-slate-900 text-sm">{node.title || 'Untitled'}</div>
            <div className="text-xs text-slate-400">{node.start_week != null || node.end_week != null ? `${node.start_week ?? 'TBD'} - ${node.end_week ?? 'TBD'}` : ''}</div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); setShowDetails((s) => !s); }}
              className="rounded-md bg-slate-50 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100"
              title="Toggle description"
            >
              i
            </button>
            <div className="ml-1 text-xs text-slate-400">{childrenOpen ? '▾' : '▸'}</div>
          </div>
        </motion.div>
      </div>

      {/* render details when info toggled */}
      <div className="flex justify-center">
        <div className="w-full max-w-3xl">
          <AnimatePresence>
            {showDetails && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.16 }} className="mt-2 rounded-md bg-slate-50 p-3 text-sm text-slate-600 border border-slate-100">
                {node.details || 'No details provided.'}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* render children only when childrenOpen to keep UI compact */}
      {childrenOpen && hasChildren && (
        <div className="mt-3">
          <div className="flex justify-center">
            <svg width="20" height="34" viewBox="0 0 20 34" className="overflow-visible">
              <defs>
                <linearGradient id={`g-v-${node.id}`} x1="0" x2="1">
                  <stop offset="0%" stopColor="#34d399" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.85" />
                </linearGradient>
              </defs>
              <motion.path d="M10 0 C10 10,10 24,10 34" stroke={`url(#g-v-${node.id})`} strokeWidth="4" strokeLinecap="round" fill="none" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.5 }} />
            </svg>
          </div>

          <div className="mt-2 flex justify-center">
            <div className="w-full max-w-5xl">
              <div className="flex items-start justify-center gap-10">
                {node.children!.map((c) => (
                  <div key={c.id || Math.random().toString(36).slice(2, 8)} className="flex-1 min-w-[120px]">
                    <div className="flex justify-center mb-1">
                      <svg width="100" height="26" viewBox="0 0 100 26" className="overflow-visible">
                        <defs>
                          <linearGradient id={`g-h-${c.id}`} x1="0" x2="1">
                            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.9" />
                            <stop offset="100%" stopColor="#34d399" stopOpacity="0.9" />
                          </linearGradient>
                        </defs>
                        <motion.path d="M6 4 C28 11,72 11,94 4" stroke={`url(#g-h-${c.id})`} strokeWidth={2.5} strokeLinecap="round" fill="none" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.5 }} />
                      </svg>
                    </div>
                    <RenderNode node={c} depth={depth + 1} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RoadmapPage() {
  const [prompt, setPrompt] = useState('');
  const [weeks, setWeeks] = useState(12);
  const [loading, setLoading] = useState(false);
  const [roadmap, setRoadmap] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  const generate = async () => {
    if (!prompt.trim()) {
      alert('Please enter a prompt describing the project or goal.');
      return;
    }
    setLoading(true);
    setError(null);
    setRoadmap(null);
    try {
      const res = await fetch(`${API_BASE}/api/roadmap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, weeks }),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || 'Roadmap generation failed');
      }
      const json = await res.json();
      const rm = json.roadmap || json;
      // If nodes missing or empty, expose raw JSON and show guidance
      if (!rm || !Array.isArray(rm.nodes) || rm.nodes.length === 0) {
        setRoadmap(rm);
        setError('Roadmap nodes not found — showing raw output. Try a more specific prompt (include milestones and deliverables).');
        setShowRaw(true);
      } else {
        setRoadmap(rm);
        setError(null);
        setShowRaw(false);
      }
    } catch (err: any) {
      setError(err?.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Agentic AI</p>
            <h1 className="text-3xl font-semibold">Roadmap Generator</h1>
          </div>
          <Link to="/" className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-900">
            Back to Main Page
          </Link>
        </div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-slate-200 bg-white p-8 shadow-lg">
          <div className="grid gap-8 lg:grid-cols-[1fr_0.9fr]">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Generator</p>
              <h2 className="mt-3 text-2xl font-semibold">Create a tree-based roadmap with timelines</h2>
              <p className="mt-3 text-slate-600">Enter a short prompt describing the goal, target audience, or project. Adjust total weeks if desired. The roadmap will be produced by the Groq model and returned as a nested tree with weekly timelines.</p>

              <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={6} className="mt-4 w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800" placeholder="Describe the project or goal (e.g. Build a full-stack portfolio website focused on data visualizations)..." />

              <div className="mt-3 flex items-center gap-3">
                <label className="text-sm text-slate-600">Total weeks:</label>
                <input type="number" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} min={1} max={104} className="w-28 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900" />
                <button onClick={generate} disabled={loading} className="ml-auto rounded-2xl bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:opacity-70">{loading ? 'Generating...' : 'Generate Roadmap'}</button>
              </div>

              {error && <div className="mt-3 text-sm text-rose-400">{error}</div>}
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              {roadmap ? (
                <div>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-semibold">{roadmap.title || 'Roadmap'}</h3>
                      <p className="mt-2 text-slate-600">{roadmap.overview || 'No overview provided.'}</p>
                      <p className="mt-2 text-xs text-slate-500">Total weeks: {roadmap.total_weeks || weeks}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <button onClick={() => setShowRaw((s) => !s)} className="rounded-md border border-slate-200 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50">{showRaw ? 'Hide Raw' : 'Show Raw'}</button>
                    </div>
                  </div>

                  <div className="mt-6">
                    {showRaw ? (
                      <pre className="max-h-96 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800">{JSON.stringify(roadmap, null, 2)}</pre>
                    ) : (
                      (Array.isArray(roadmap.nodes) ? roadmap.nodes : []).map((n: RoadmapNode) => (
                        <RenderNode key={n.id || Math.random().toString(36).slice(2,8)} node={n} />
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-slate-500">No roadmap yet. Enter a prompt and press Generate Roadmap.</div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
