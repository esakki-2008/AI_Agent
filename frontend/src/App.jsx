import { useState } from 'react'
import { Download, Film, Link2, LoaderCircle, ShieldCheck, Sparkles, Upload, Youtube } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function App() {
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [mode, setMode] = useState('youtube')
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const validYouTube = /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)(\/|$)/i.test(url.trim())

  async function generate() {
    setStatus('processing'); setProgress(8); setError(''); setResult(null)
    try {
      let response
      if (mode === 'youtube') {
        if (!validYouTube) throw new Error('Enter a valid YouTube URL.')
        response = await fetch(`${API}/process-url`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: url.trim() }) })
      } else {
        if (!file) throw new Error('Choose a video first.')
        const form = new FormData(); form.append('file', file)
        response = await fetch(`${API}/process`, { method: 'POST', body: form })
      }
      const timer = setInterval(() => setProgress(p => p < 92 ? p + 3 : p), 900)
      const data = await response.json()
      clearInterval(timer)
      if (!response.ok) throw new Error(data.detail || 'Generation failed.')
      setProgress(100); setResult(data); setStatus('complete')
    } catch (e) { setError(e.message); setStatus('idle'); setProgress(0) }
  }

  function reset() { setUrl(''); setFile(null); setResult(null); setStatus('idle'); setProgress(0); setError('') }

  return <main>
    <nav><div className="brand"><span className="brandmark"><Sparkles size={17}/></span>ClipForge<span>AI</span></div><div className="badge"><ShieldCheck size={14}/> Local AI · No API key</div></nav>
    <section className="hero">
      <p className="eyebrow">LONG-FORM → SHORT-FORM</p>
      <h1>Turn long videos into <em>Shorts.</em></h1>
      <p className="sub">Paste a YouTube link or upload a video. ClipForgeAI finds strong moments, crops them to 9:16 and adds captions.</p>
      {status === 'idle' && !result && <div className="panel">
        <div className="tabs"><button className={mode === 'youtube' ? 'active' : ''} onClick={() => setMode('youtube')}><Youtube size={17}/> YouTube URL</button><button className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}><Upload size={17}/> Upload video</button></div>
        {mode === 'youtube' ? <div className="urlbox"><Link2 size={20}/><input value={url} onChange={e => setUrl(e.target.value)} placeholder="Paste YouTube video URL..." onKeyDown={e => e.key === 'Enter' && generate()}/></div> : <label className="drop"><Upload/><strong>{file ? file.name : 'Drop your video here or click to browse'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : 'MP4, MOV, MKV, AVI, WebM · Max 2 GB'}</span><input hidden type="file" accept="video/*" onChange={e => { setFile(e.target.files[0]); setError('') }}/></label>}
        {error && <div className="error">{error}</div>}
        <button className="primary" onClick={generate}><Sparkles size={18}/> Generate Best Shorts</button>
      </div>}
      {status === 'processing' && <div className="processing"><LoaderCircle className="spin" size={36}/><h2>Creating your Shorts…</h2><p>Downloading, transcribing, ranking highlights and rendering vertical clips.</p><div className="bar"><i style={{width: `${progress}%`}}/></div><strong>{progress}%</strong></div>}
    </section>
    {result && <section className="results"><div className="result-head"><div><p className="eyebrow">PROCESS COMPLETE</p><h2>{result.number_of_clips} Shorts generated</h2><p>{result.has_audio ? 'Whisper analyzed the speech and ranked the strongest moments.' : 'No speech detected; a fallback highlight was created.'}</p></div><button className="secondary" onClick={reset}>Create another</button></div><div className="grid">{result.clips.map(c => <article className="card" key={c.clip_number}><div className="preview"><video controls preload="metadata" src={`${API}${c.download_url}`}/><div className="score">🔥 {c.score}/100</div></div><div className="card-body"><h3>{c.title}</h3><p>{c.text || 'AI-selected highlight'}</p><a className="download" href={`${API}${c.download_url}`} download><Download size={17}/> Download Short</a></div></article>)}</div></section>}
    <section className="features"><div><Sparkles/><b>Best moments</b><span>Transcript-based ranking</span></div><div><Film/><b>Vertical 9:16</b><span>1080 × 1920 MP4</span></div><div><Download/><b>Ready to post</b><span>Preview and download</span></div></section>
    <footer>ClipForge AI · Built for creators</footer>
  </main>
}
