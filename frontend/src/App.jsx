import { useEffect, useState } from 'react'
import { Download, Film, Link2, LoaderCircle, Settings2, ShieldCheck, Sparkles, Upload, Youtube } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function App() {
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [mode, setMode] = useState('youtube')
  const [numClips, setNumClips] = useState(3)
  const [clipDuration, setClipDuration] = useState(30)
  const [captions, setCaptions] = useState(true)
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [jobId, setJobId] = useState(null)

  const validYouTube = /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)(\/|$)/i.test(url.trim())

  useEffect(() => {
    if (!jobId || status !== 'processing') return
    const timer = setInterval(async () => {
      try {
        const response = await fetch(`${API}/jobs/${jobId}`)
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail || 'Could not read job status.')
        setProgress(data.progress ?? 0)
        setMessage(data.message || 'Working…')
        if (data.status === 'completed') {
          setResult(data.result)
          setProgress(100)
          setStatus('complete')
          setJobId(null)
        } else if (data.status === 'failed') {
          throw new Error(data.error || 'Processing failed.')
        }
      } catch (e) {
        setError(e.message)
        setStatus('idle')
        setJobId(null)
      }
    }, 1000)
    return () => clearInterval(timer)
  }, [jobId, status])

  async function generate() {
    setError(''); setResult(null)
    if (mode === 'youtube' && !validYouTube) { setError('Enter a valid YouTube URL.'); return }
    if (mode === 'upload' && !file) { setError('Choose a video first.'); return }
    try {
      setStatus('processing'); setProgress(5)
      setMessage(mode === 'youtube' ? 'Starting YouTube download…' : 'Uploading video…')
      let response
      if (mode === 'youtube') {
        response = await fetch(`${API}/process-url`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: url.trim(), options: { num_clips: numClips, clip_duration: clipDuration, captions } }) })
      } else {
        const form = new FormData()
        form.append('file', file); form.append('num_clips', String(numClips)); form.append('clip_duration', String(clipDuration)); form.append('captions', String(captions))
        response = await fetch(`${API}/process`, { method: 'POST', body: form })
      }
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Generation failed.')
      setJobId(data.job_id)
    } catch (e) { setError(e.message); setStatus('idle'); setProgress(0) }
  }

  function reset() { setUrl(''); setFile(null); setResult(null); setStatus('idle'); setProgress(0); setMessage(''); setError(''); setJobId(null) }

  return <main>
    <nav><div className="brand"><span className="brandmark"><Sparkles size={17}/></span>ClipForge<span>AI</span></div><div className="badge"><ShieldCheck size={14}/> Local AI · No API key</div></nav>
    <section className="hero">
      <p className="eyebrow">LONG-FORM → SHORT-FORM</p>
      <h1>Turn long videos into <em>Shorts.</em></h1>
      <p className="sub">Paste a YouTube link or upload a video. ClipForge AI downloads it, transcribes speech locally, finds strong moments, creates 9:16 clips and burns in captions.</p>
      {status === 'idle' && !result && <div className="panel">
        <div className="tabs"><button className={mode === 'youtube' ? 'active' : ''} onClick={() => setMode('youtube')}><Youtube size={17}/> YouTube URL</button><button className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}><Upload size={17}/> Upload video</button></div>
        {mode === 'youtube' ? <div className="urlbox"><Link2 size={20}/><input value={url} onChange={e => setUrl(e.target.value)} placeholder="Paste YouTube video URL…" onKeyDown={e => e.key === 'Enter' && generate()}/></div> : <label className="drop"><Upload size={28}/><strong>{file ? file.name : 'Drop your video here or click to browse'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : 'MP4, MOV, MKV, AVI, WebM · Max 2 GB'}</span><input hidden type="file" accept="video/*" onChange={e => { setFile(e.target.files?.[0] || null); setError('') }}/></label>}
        <div className="options"><div className="options-title"><Settings2 size={16}/> Output settings</div><label>Shorts <select value={numClips} onChange={e => setNumClips(Number(e.target.value))}><option value={1}>1</option><option value={2}>2</option><option value={3}>3</option><option value={4}>4</option><option value={5}>5</option></select></label><label>Length <select value={clipDuration} onChange={e => setClipDuration(Number(e.target.value))}><option value={15}>15 sec</option><option value={20}>20 sec</option><option value={30}>30 sec</option><option value={45}>45 sec</option><option value={60}>60 sec</option></select></label><label className="check"><input type="checkbox" checked={captions} onChange={e => setCaptions(e.target.checked)}/> Captions</label></div>
        {error && <div className="error">{error}</div>}
        <button className="primary" onClick={generate}><Sparkles size={18}/> Generate Best Shorts</button>
        <p className="fineprint">Use videos you own or have permission to download and transform.</p>
      </div>}
      {status === 'processing' && <div className="processing"><LoaderCircle className="spin" size={38}/><h2>Creating your Shorts…</h2><p>{message || 'Downloading, transcribing, ranking and rendering.'}</p><div className="bar"><i style={{width: `${progress}%`}}/></div><strong>{progress}%</strong></div>}
    </section>
    {result && <section className="results"><div className="result-head"><div><p className="eyebrow">PROCESS COMPLETE</p><h2>{result.number_of_clips} Shorts generated</h2><p>{result.warning || (result.has_audio ? 'Whisper analyzed the speech and ranked the strongest moments.' : 'No audio was available; fallback highlights were created.')}</p></div><button className="secondary" onClick={reset}>Process another</button></div><div className="grid">{result.clips.map(c => <article className="card" key={c.clip_number}><div className="preview"><video controls preload="metadata" src={`${API}${c.download_url}`}/><div className="score">🔥 {c.score}/100</div></div><div className="card-body"><h3>{c.title}</h3><p>{c.text || 'AI-selected highlight'}</p><div className="meta">Starts at {formatTime(c.start)} · {Math.round(c.duration)} sec</div><a className="download" href={`${API}${c.download_url}`} download><Download size={17}/> Download Short</a></div></article>)}</div></section>}
    <section className="features"><div><Sparkles/><b>Best moments</b><span>Transcript-based AI ranking</span></div><div><Film/><b>Vertical 9:16</b><span>1080 × 1920 MP4</span></div><div><Download/><b>Ready to post</b><span>Preview and download</span></div></section>
    <footer>ClipForge AI · Local processing · No API key</footer>
  </main>
}

function formatTime(seconds) { const total = Math.max(0, Math.floor(seconds)); const h = Math.floor(total / 3600); const m = Math.floor((total % 3600) / 60); const s = total % 60; return h ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}` }
