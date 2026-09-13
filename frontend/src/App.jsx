import React, { useMemo, useState } from 'react'
import { Upload, Sparkles, Download, LoaderCircle, Film, ShieldCheck } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function App() {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)
  const sizeLabel = useMemo(() => file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : '', [file])

  function choose(f) {
    if (!f) return
    if (!f.type.startsWith('video/')) return setError('Please select a video file.')
    if (f.size > 2 * 1024 * 1024 * 1024) return setError('Maximum upload size is 2 GB.')
    setFile(f); setError(''); setResult(null)
  }

  async function process() {
    if (!file) return
    setStatus('processing'); setProgress(10); setError('')
    const form = new FormData(); form.append('file', file)
    try {
      const timer = setInterval(() => setProgress(p => p < 88 ? p + 4 : p), 700)
      const res = await fetch(`${API}/process`, { method: 'POST', body: form })
      clearInterval(timer)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Processing failed')
      setProgress(100); setResult(data); setStatus('complete')
    } catch (e) { setError(e.message); setStatus('idle'); setProgress(0) }
  }

  const reset = () => { setFile(null); setResult(null); setStatus('idle'); setProgress(0); setError('') }

  return <main>
    <nav><div className="brand"><span className="brandmark"><Sparkles size={17}/></span> ClipForge<span>AI</span></div><div className="badge"><ShieldCheck size={14}/> Local AI · No API key</div></nav>
    <section className="hero"><p className="eyebrow">LONG-FORM → SHORT-FORM</p><h1>Turn long-form video into <em>Shorts.</em></h1><p className="sub">AI finds strong moments, formats them for vertical platforms, and exports ready-to-post clips.</p>
      {status === 'idle' && !result && <><div className={`drop ${dragging ? 'dragging' : ''}`} onDragOver={e => {e.preventDefault();setDragging(true)}} onDragLeave={() => setDragging(false)} onDrop={e => {e.preventDefault();setDragging(false);choose(e.dataTransfer.files[0])}} onClick={() => document.getElementById('video').click()}><input id="video" hidden type="file" accept="video/*" onChange={e => choose(e.target.files[0])}/><div className="upload-icon"><Upload/></div><h3>{file ? file.name : 'Drop your video here'}</h3><p>{file ? sizeLabel : 'or click to browse · MP4, MOV, MKV, AVI, WebM'}</p></div>{error && <div className="error">{error}</div>}{file && <button className="primary" onClick={process}><Sparkles size={18}/> Generate Shorts</button>}</>}
      {status === 'processing' && <div className="processing"><LoaderCircle className="spin" size={34}/><h2>Creating your Shorts…</h2><p>Analyzing audio, finding highlights and rendering vertical clips.</p><div className="bar"><i style={{width:`${progress}%`}}/></div><strong>{progress}%</strong></div>}
    </section>
    {result && <section className="results"><div className="result-head"><div><p className="eyebrow">PROCESS COMPLETE</p><h2>{result.number_of_clips} Short{result.number_of_clips !== 1 ? 's' : ''} generated</h2><p>{result.has_audio ? 'Transcript analyzed with Whisper.' : 'No audio detected; a video highlight was created.'}</p></div><button className="secondary" onClick={reset}>Process another</button></div><div className="grid">{result.clips.map(c => <article className="card" key={c.clip_number}><div className="preview"><video controls preload="metadata" src={`${API}${c.download_url}`}/><div className="score">{c.score}/100</div></div><div className="card-body"><h3>{c.title}</h3><p>{c.text || 'AI-selected highlight'}</p><a className="download" href={`${API}${c.download_url}`} download><Download size={17}/> Download</a></div></article>)}</div></section>}
    <section className="features"><div><Sparkles/><b>AI highlights</b><span>Finds strong moments</span></div><div><Film/><b>Vertical 9:16</b><span>1080 × 1920 MP4</span></div><div><Download/><b>Easy export</b><span>Preview and download</span></div></section><footer>ClipForge AI · Built for creators</footer>
  </main>
}
