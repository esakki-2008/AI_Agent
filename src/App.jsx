import { useEffect, useState } from 'react'

const words = ['different.', 'alive.', 'memorable.']

export default function App() {
  const [word, setWord] = useState(0)
  const [mouse, setMouse] = useState({ x: 50, y: 50 })

  useEffect(() => {
    const timer = setInterval(() => setWord((current) => (current + 1) % words.length), 2600)
    return () => clearInterval(timer)
  }, [])

  function handleMove(event) {
    const rect = event.currentTarget.getBoundingClientRect()
    setMouse({
      x: ((event.clientX - rect.left) / rect.width) * 100,
      y: ((event.clientY - rect.top) / rect.height) * 100,
    })
  }

  return (
    <main className="site-shell" onMouseMove={handleMove} style={{ '--mx': `${mouse.x}%`, '--my': `${mouse.y}%` }}>
      <div className="noise" />
      <header className="nav">
        <a className="brand" href="#top" aria-label="Atelier home">
          <span className="brand-mark">A</span>
          <span>ATELIER<span className="brand-dot">.</span></span>
        </a>
        <nav className="nav-links" aria-label="Main navigation">
          <a href="#work">Work</a>
          <a href="#about">About</a>
          <a href="#contact">Contact</a>
        </nav>
        <button className="nav-cta">Start a project <span>↗</span></button>
      </header>

      <section id="top" className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span /> Independent digital studio · 2026</p>
          <h1>We make digital<br /><em>{words[word]}</em></h1>
          <p className="hero-text">Strategy, identity and interactive experiences for ambitious brands that refuse to blend in.</p>
          <div className="hero-actions">
            <button className="primary-btn">Explore our work <span>↓</span></button>
            <span className="scroll-note">Scroll to discover</span>
          </div>
        </div>

        <div className="orbital" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="orbit orbit-three" />
          <div className="core"><span>01</span></div>
          <div className="orbital-label">Ideas<br />in motion</div>
        </div>
      </section>

      <section id="work" className="preview-strip">
        <span>Selected direction</span>
        <strong>Brand × Digital × Motion</strong>
        <span className="line" />
        <span>01 / 04</span>
      </section>

      <section id="about" className="intro-block">
        <p className="section-index">01 — THE APPROACH</p>
        <h2>Static is easy.<br /><span>We build experiences.</span></h2>
      </section>

      <section id="contact" className="contact-preview">
        <p>Have a bold idea?</p>
        <a href="mailto:hello@example.com">Let’s make it real <span>↗</span></a>
      </section>
    </main>
  )
}
