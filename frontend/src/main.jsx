import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Upload, Sparkles, Download, Play, CheckCircle2, Loader2, Film, Zap } from 'lucide-react'
import './style.css'

const API = 'http://127.0.0.1:8000'

function App() {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const chooseFile = (f) => {
    if (!f) return
    setFile(f); setResult(null); setError('')
  }

  const processVideo = async () => {
    if (!file) return
    setLoading(true); setError(''); setResult(null)
    try {
      setStage('Uploading video…')
      const form = new FormData(); form.append('file', file)
      setStage('AI is finding the best moments…')
      const response = await fetch(`${API}/process`, { method: 'POST', body: form })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || data.message || 'Processing failed')
      setResult(data); setStage('Done! Your Shorts are ready.')
    } catch (e) { setError(e.message); setStage('') }
    finally { setLoading(false) }
  }

  return <div className="app">
    <nav><div className="brand"><div className="logo"><Sparkles size={18}/></div> ClipForge <span>AI</span></div><div className="nav-pill"><Zap size={15}/> Local AI • No API key</div></nav>
    <main>
      <section className="hero"><p className="eyebrow">LONG-FORM → SHORT-FORM</p><h1>Turn hours of video into<br/><em>scroll-stopping Shorts.</em></h1><p className="sub">Upload your video. AI finds the strongest moments, converts them to 9:16, and gives you ready-to-post clips.</p></section>
      {!result && <section className="card upload-card">
        <div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={e=>{e.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);chooseFile(e.dataTransfer.files[0])}}>
          <input id="video" type="file" accept="video/*" onChange={e=>chooseFile(e.target.files[0])}/>
          <label htmlFor="video"><div className="upload-icon"><Upload/></div><h3>{file ? file.name : 'Drop your video here'}</h3><p>{file ? `${(file.size/1024/1024).toFixed(1)} MB • Ready to process` : 'or click to browse • MP4, MOV, MKV, WebM'}</p></label>
        </div>
        <button className="primary" disabled={!file || loading} onClick={processVideo}>{loading ? <><Loader2 className="spin"/> {stage}</> : <><Sparkles/> Generate Shorts</>}</button>
        {error && <div className="error">{error}</div>}
      </section>}

      {loading && <div className="progress"><div className="progress-head"><span>{stage}</span><span>AI processing</span></div><div className="bar"><div/></div><div className="steps"><span><CheckCircle2/> Upload</span><span><Loader2 className="spin"/> Analyze</span><span><Film/> Render</span></div></div>}

      {result && <section className="results"><div className="result-head"><div><p className="eyebrow">PROCESS COMPLETE</p><h2>{result.number_of_clips} Shorts generated</h2><p>{result.has_audio ? 'Audio detected and transcript analyzed.' : 'No audio detected; a highlight was created from the video.'}</p></div><button className="secondary" onClick={()=>{setFile(null);setResult(null);setStage('')}}>Process another</button></div>
        <div className="clip-grid">{result.clips.map(clip=><article className="clip" key={clip.clip_number}><div className="video-box"><video controls src={`${API}${clip.file}`} /><div className="score">{clip.score}/100</div></div><div className="clip-info"><div><h3>{clip.title}</h3><p>{clip.text || 'AI-selected highlight'}</p></div><a href={`${API}${clip.file}`} download><Download size={18}/></a></div></article>)}</div>
      </section>}
      <section className="features"><div><Sparkles/><b>AI highlight detection</b><span>Finds moments worth sharing</span></div><div><Film/><b>9:16 vertical video</b><span>Ready for Reels & Shorts</span></div><div><Download/><b>One-click export</b><span>Download MP4 clips</span></div></section>
    </main>
    <footer>ClipForge AI • Built for creators</footer>
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
