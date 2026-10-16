import React from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
      <div className="max-w-xl"><p className="text-teal-400 font-semibold">RampUp</p><h1 className="text-4xl font-bold mt-4">Learn the repository. Build with guidance.</h1><p className="text-slate-400 mt-6">Shared frontend starter is ready. Learner and mentor experiences are coming next.</p></div>
    </main>
  </React.StrictMode>,
)
