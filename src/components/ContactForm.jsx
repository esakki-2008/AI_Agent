import { useState } from 'react'

export default function ContactForm() {
  const [form, setForm] = useState({ name: '', email: '', message: '' })
  const [sent, setSent] = useState(false)
  function submit(e) {
    e.preventDefault()
    let previous = []
    try { previous = JSON.parse(localStorage.getItem('atelier-inquiries')) || [] } catch {}
    localStorage.setItem('atelier-inquiries', JSON.stringify([...previous, { ...form, createdAt: new Date().toISOString() }]))
    setSent(true)
    setForm({ name: '', email: '', message: '' })
  }
  if (sent) return <div className="form-success"><span>✓</span><h3>Message received.</h3><p>Your inquiry is saved in the admin panel.</p><button onClick={() => setSent(false)}>Send another ↗</button></div>
  return <form className="contact-form" onSubmit={submit}><label>Name<input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Your name" required /></label><label>Email<input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="you@company.com" required /></label><label>Project details<textarea value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} placeholder="Tell us what you want to build..." required /></label><button className="form-submit">Send inquiry <span>↗</span></button></form>
}
