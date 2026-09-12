import express from 'express'
import cors from 'cors'
import { existsSync, readFileSync, writeFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const app = express()
const PORT = process.env.PORT || 4000
const ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const DATA_FILE = join(ROOT, 'server', 'data.json')
const initial = { settings: { heroLine: 'We make digital', heroWord: 'different.', heroText: 'Strategy, identity and interactive experiences for ambitious brands that refuse to blend in.' }, projects: [], services: [], inquiries: [] }
app.use(cors())
app.use(express.json({ limit: '1mb' }))
function load(){if(!existsSync(DATA_FILE)){writeFileSync(DATA_FILE,JSON.stringify(initial,null,2));return structuredClone(initial)}const data=JSON.parse(readFileSync(DATA_FILE,'utf8'));return {...initial,...data,settings:{...initial.settings,...(data.settings||{})}}}
function save(data){writeFileSync(DATA_FILE,JSON.stringify(data,null,2))}
function id(){return Date.now().toString(36)}
app.get('/api/health',(_,res)=>res.json({ok:true,service:'AI Agent Client Demo API',time:new Date().toISOString()}))
app.get('/api/settings',(_,res)=>res.json(load().settings))
app.patch('/api/settings',(req,res)=>{const data=load();data.settings={...data.settings,...req.body};save(data);res.json(data.settings)})
app.get('/api/projects',(_,res)=>res.json(load().projects))
app.post('/api/projects',(req,res)=>{const data=load();const item={id:id(),title:req.body.title||'Untitled Project',type:req.body.type||'General',year:req.body.year||new Date().getFullYear().toString(),status:req.body.status||'Draft',description:req.body.description||'A new selected project.',image:req.body.image||''};data.projects.push(item);save(data);res.status(201).json(item)})
app.patch('/api/projects/:id',(req,res)=>{const data=load();const item=data.projects.find(p=>String(p.id)===String(req.params.id));if(!item)return res.status(404).json({error:'Project not found'});Object.assign(item,req.body);save(data);res.json(item)})
app.delete('/api/projects/:id',(req,res)=>{const data=load();data.projects=data.projects.filter(p=>String(p.id)!==String(req.params.id));save(data);res.status(204).end()})
app.get('/api/services',(_,res)=>res.json(load().services))
app.patch('/api/services/:id',(req,res)=>{const data=load();const item=data.services.find(s=>String(s.id)===String(req.params.id));if(!item)return res.status(404).json({error:'Service not found'});Object.assign(item,req.body);save(data);res.json(item)})
app.post('/api/inquiries',(req,res)=>{if(!req.body.name||!req.body.email||!req.body.message)return res.status(400).json({error:'Name, email and message are required'});const data=load();const item={id:id(),name:req.body.name,email:req.body.email,message:req.body.message,createdAt:new Date().toISOString()};data.inquiries.unshift(item);save(data);res.status(201).json({success:true,item})})
app.get('/api/inquiries',(_,res)=>res.json(load().inquiries))
app.delete('/api/inquiries',(_,res)=>{const data=load();data.inquiries=[];save(data);res.status(204).end()})

const dist = join(ROOT, 'dist')
if (existsSync(dist)) { app.use(express.static(dist)); app.get('*', (_, res) => res.sendFile(join(dist, 'index.html'))) }
app.listen(PORT,()=>console.log(`API running at http://localhost:${PORT}`))
