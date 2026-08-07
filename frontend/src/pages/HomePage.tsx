import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

function HomePage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl border border-slate-800 bg-slate-900/70 p-10 shadow-2xl"
        >
          <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Agentic AI Platform</p>
          <h1 className="mt-3 text-4xl font-semibold">Main Dashboard</h1>
          <p className="mt-4 max-w-3xl text-slate-300">
            Use this as your central page. Add upcoming AI features as separate modules. The Resume Analyzer is now a dedicated second page.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <Link
              to="/resume-analyzer"
              className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-6 transition hover:bg-cyan-500/20"
            >
              <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Module</p>
              <h2 className="mt-2 text-2xl font-semibold">Resume Analyzer</h2>
              <p className="mt-2 text-slate-300">
                Analyze resume text, extract projects, validate GitHub data, and show exact LeetCode solved stats with graph and improvement comments.
              </p>
            </Link>

            <Link
              to="/roadmap"
              className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6 transition hover:bg-emerald-500/20"
            >
              <p className="text-sm uppercase tracking-[0.2em] text-emerald-300">Tool</p>
              <h2 className="mt-2 text-2xl font-semibold">Roadmap Generator</h2>
              <p className="mt-2 text-slate-300">
                Create complex, tree-structured roadmaps with timelines and weekly breakdowns using the Groq model.
              </p>
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default HomePage;
