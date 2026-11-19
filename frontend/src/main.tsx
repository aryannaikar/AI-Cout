import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Courtroom Replay is a fully separate, lazily loaded page (/courtroom-replay/:caseId).
// It is never bundled into or mounted by the main AI Court UI.
const ReplayPage = lazy(() => import('./replay/CourtroomReplayPage'))
const replayMatch = window.location.pathname.match(/^\/courtroom-replay\/([^/]+)\/?$/)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {replayMatch ? (
      <Suspense fallback={null}>
        <ReplayPage caseId={decodeURIComponent(replayMatch[1])} />
      </Suspense>
    ) : (
      <App />
    )}
  </StrictMode>,
)
