import express from 'express'
import cors from 'cors'
import { existsSync, readFileSync, writeFileSync } from 'fs'

const app = express()
const PORT = process.env.PORT || 4000
const DATA_FILE = './server/data.json'
const initial = { projects: [], services: [], inquiries: [] }
app.use(cors())
app.use(express.json())

function load() { if (!existsSync(DATA_FILE)) { writeFileSync(DATA_FILE, JSON.stringify(initial, null, 2)); return structuredClone(initial) } return JSON.parse(readFileSync(DATA_FILE, 'utf8')) }
function save(data) { writeFileSync(DATA_FILE, JSON.stringify(data, null, 2)) }
function id() { return Date.now().toString(36) }

app.get('/api/health', (_, res) => res.json({ ok: true, service: 'AI Agent Client Demo API' }))
app.get('/api/projects', (_, res) => res.json(load().projects))
app.post('/api/projects', (req, res) => { const data = load(); const item = { id: id(), title: req.body.title || 'Untitled Project', type: req.body.type || 'General', year: req.body.year || new Date().getFullYear().toString(), status: req.body.status || 'Draft' }; data.projects.push(item); save(data); res.status(201).json(item) })
app.patch('/api/projects/:id', (req, res) => { const data = load(); const item = data.projects.find(p => p.id === req.params.id); if (!item) return res.status(404).json({ error: 'Project not found' }); Object.assign(item, req.body); save(data); res.json(item) })
app.delete('/api/projects/:id', (req, res) => { const data = load(); data.projects = data.projects.filter(p => p.id !== req.params.id); save(data); res.status(204).end() })
app.get('/api/services', (_, res) => res.json(load().services))
app.post('/api/inquiries', (req, res) => { const data = load(); const item = { id: id(), name: req.body.name, email: req.body.email, message: req.body.message, createdAt: new Date().toISOString() }; data.inquiries.unshift(item); save(data); res.status(201).json({ success: true }) })
app.get('/api/inquiries', (_, res) => res.json(load().inquiries))
app.delete('/api/inquiries', (_, res) => { const data = load(); data.inquiries = []; save(data); res.status(204).end() })
app.listen(PORT, () => console.log(`API running at http://localhost:${PORT}`))
