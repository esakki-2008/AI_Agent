import { useEffect, useState } from 'react'
import AnimatedCursor from './components/AnimatedCursor'
import ProjectShowcase from './components/ProjectShowcase'
import ScrollReveal from './components/ScrollReveal'
import AdminPanel from './components/AdminPanel'
import ContactForm from './components/ContactForm'
import './admin.css'

const words = ['different.', 'alive.', 'memorable.']
const services = [{ number: '01', title: 'Digital Strategy', text: 'Turn ambitious ideas into clear digital direction.' }, { number: '02', title: 'Brand Systems', text: 'Build a visual language people remember instantly.' }, { number: '03', title: 'Interactive Web', text: 'Create responsive experiences that react to people.' }]
const stats = [['24', 'Projects launched'], ['11', 'Industries explored'], ['07', 'Years creating']]
function TiltCard({ children }) { function move(e) { const r=e.currentTarget.getBoundingClientRect(); const x=((e.clientX-r.left)/r.width-.5)*8; const y=((e.clientY-r.top)/r.height-.5)*-8; e.currentTarget.style.transform=`perspective(800px) rotateX(${y}deg) rotateY(${x}deg) translateY(-4px)` } function leave(e){e.currentTarget.style.transform=''} return <div onMouseMove={move} onMouseLeave={leave}>{children}</div> }

export default function App() {
  const [admin, setAdmin] = useState(window.location.hash === '#admin')
  const [word, setWord] = useState(0)
  const [mouse, setMouse] = useState({x:50,y:50})
  const [scroll, setScroll] = useState(0)
  useEffect(() => { const hashChange=()=>setAdmin(window.location.hash==='#admin'); window.addEventListener('hashchange',hashChange); const timer=setInterval(()=>setWord(c=>(c+1)%words.length),2600); const onScroll=()=>{const max=document.documentElement.scrollHeight-window.innerHeight;setScroll(max>0?window.scrollY/max*100:0)}; window.addEventListener('scroll',onScroll,{passive:true}); return()=>{clearInterval(timer);window.removeEventListener('hashchange',hashChange);window.removeEventListener('scroll',onScroll)} },[])
  function handleMove(e){const r=e.currentTarget.getBoundingClientRect();setMouse({x:(e.clientX-r.left)/r.width*100,y:(e.clientY-r.top)/r.height*100})}
  function exitAdmin(){window.location.hash='top';setAdmin(false)}
  if(admin) return <AdminPanel onExit={exitAdmin} />

  return <main className="site-shell" onMouseMove={handleMove} style={{'--mx':`${mouse.x}%`,'--my':`${mouse.y}%`,'--scroll':`${scroll}%`}}><AnimatedCursor/><div className="scroll-progress"/><div className="noise"/>
    <header className="nav"><a className="brand" href="#top"><span className="brand-mark">A</span><span>ATELIER<span className="brand-dot">.</span></span></a><nav className="nav-links"><a href="#work">Work</a><a href="#services">Services</a><a href="#about">About</a><a href="#contact">Contact</a></nav><a className="nav-cta" href="#admin">Admin ↗</a></header>
    <section id="top" className="hero"><div className="hero-grid"/><div className="hero-copy"><p className="eyebrow"><span/> Independent digital studio · 2026</p><h1>We make digital<br/><em key={words[word]}>{words[word]}</em></h1><p className="hero-text">Strategy, identity and interactive experiences for ambitious brands that refuse to blend in.</p><div className="hero-actions"><a className="primary-btn" href="#work">Explore our work <span>↓</span></a><span className="scroll-note">Scroll to discover</span></div></div><div className="orbital"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="orbit-dot dot-one"/><div className="orbit-dot dot-two"/><div className="core"><span>01</span></div><div className="orbital-label">Ideas<br/>in motion</div></div></section>
    <section id="work" className="work-wrap"><ScrollReveal><ProjectShowcase/></ScrollReveal></section>
    <section id="services" className="services-section"><ScrollReveal className="section-heading"><p className="section-index">02 — WHAT WE DO</p><h2>Built to move<br/><span>your brand forward.</span></h2></ScrollReveal><div className="service-list">{services.map(s=><ScrollReveal key={s.number}><TiltCard><article className="service-card"><span className="service-number">{s.number}</span><div><h3>{s.title}</h3><p>{s.text}</p></div><span className="service-arrow">↗</span></article></TiltCard></ScrollReveal>)}</div></section>
    <ScrollReveal><section id="about" className="intro-block"><p className="section-index">03 — THE APPROACH</p><h2>Static is easy.<br/><span>We build experiences.</span></h2><div className="stats">{stats.map(([v,l])=><div className="stat" key={l}><strong>{v}<small>+</small></strong><span>{l}</span></div>)}</div></section></ScrollReveal>
    <section id="contact" className="contact-preview"><ScrollReveal><p>Have a bold idea?</p><h2>Let’s make it real <span>↗</span></h2><ContactForm/></ScrollReveal><div className="contact-foot"><span>ATELIER. / DIGITAL STUDIO</span><span>INDIA · WORLDWIDE</span></div></section>
  </main>
}
