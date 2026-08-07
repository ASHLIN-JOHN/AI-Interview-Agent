import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ResumeAnalyzerPage from './pages/ResumeAnalyzerPage';
import RoadmapPage from './pages/RoadmapPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/resume-analyzer" element={<ResumeAnalyzerPage />} />
        <Route path="/roadmap" element={<RoadmapPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
