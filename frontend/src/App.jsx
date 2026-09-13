import { useState } from 'react'
import { Upload, Sparkles, Download, Film, Zap, Loader2, CheckCircle2 } from 'lucide-react'

const API = 'http://127.0.0.1:8000'

export default function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const choose = (f) => { if (f) { setFile(f); setResult(null); setError('') } }
  async function generate() {
    if (!file) return
    setLoading(true); setError(''); setStatus('Uploading and analyzing…')
    try {
      const body = new FormData(); body.append('file', file)
      const res = await fetch(`${API}/process`, { method: 'POST', body })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Processing failed')
      setResult(data); setStatus('Your Shorts are ready.')
    } catch (e) { setError(e.message); setStatus('') }
    finally { setLoading(false) }
  }
  return (
    <div className="app">
      <header><div className="brand"><div className="logo"><Sparkles size={18}/></div>ClipForge <span>AI</span></div><div className="local"><Zap size={14}/> Local AI · No API key</div></header>
      <main>
        <section className="hero"><div className="eyebrow">LONG-FORM → SHORT-FORM</div><h1>Turn hours of video into <em>Shorts.</em></h1><p>AI finds the strongest moments, formats them for vertical platforms, and exports ready-to-post clips.</p></section>
        {!result ? <section className="card"><div className="drop" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();choose(e.dataTransfer.files[0])}}><input id="video" type="file" accept="video/*" onChange={e=>choose(e.target.files[0])}/><label htmlFor="video"><div className="uploadIcon"><Upload/></div><b>{file ? file.name : 'Drop your video here'}</b><small>{file ? `${(file.size/1048576).toFixed(1)} MB · Ready` : 'Click to browse · MP4, MOV, MKV, WebM'}</small></label></div><button className="primary" disabled={!file||loading} onClick={generate}>{loading?<><Loader2 className="spin"/>{status}</>:<><Sparkles/>Generate Shorts</>}</button>{error&&<div className="error">{error}</div>}</section> : <section className="results"><div className="resultTop"><div><div className="eyebrow">PROCESS COMPLETE</div><h2>{result.number_of_clips} Shorts generated</h2><p>{result.has_audio?'Transcript analyzed with Whisper.':'No audio detected; fallback clip created.'}</p></div><button className="secondary" onClick={()=>{setFile(null);setResult(null)}}>Process another</button></div><div className="grid">{result.clips.map(c=><article className="clip" key={c.clip_number}><div className="preview"><video controls src={`${API}${c.file}`}/><span>{c.score}/100</span></div><div className="clipBottom"><div><b>{c.title}</b><small>{c.text||'AI-selected highlight'}</small></div><a href={`${API}${c.file}`} download><Download size={17}/></a></div></article>)}</div></section>}
        <div className="features"><div><Sparkles/><b>AI highlights</b><small>Finds strong moments</small></div><div><Film/><b>Vertical 9:16</b><small>1080 × 1920 MP4</small></div><div><Download/><b>Easy export</b><small>Preview and download</small></div></div>
      </main><footer>ClipForge AI · Built for creators</footer>
    </div>
  )
}
