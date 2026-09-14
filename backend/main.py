from __future__ import annotations
import json, os, re, shutil, subprocess, tempfile, threading, uuid, zipfile
from pathlib import Path
from typing import Any
import imageio_ffmpeg
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl

BASE_DIR=Path(__file__).resolve().parent.parent; UPLOAD_DIR=BASE_DIR/'uploads'; OUTPUT_DIR=BASE_DIR/'outputs'
for p in (UPLOAD_DIR,OUTPUT_DIR): p.mkdir(parents=True,exist_ok=True)
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe(); BIN=BASE_DIR/'.bin'; BIN.mkdir(exist_ok=True); local=BIN/'ffmpeg.exe'
if not local.exists():
    try: local.symlink_to(FFMPEG)
    except Exception:
        try: shutil.copy2(FFMPEG,local)
        except Exception: pass
os.environ['PATH']=str(BIN)+os.pathsep+str(Path(FFMPEG).parent)+os.pathsep+os.environ.get('PATH','')
ALLOWED={'.mp4','.mov','.mkv','.avi','.webm','.m4v'}; MAX_UPLOAD=2*1024*1024*1024
app=FastAPI(title='ClipForge AI',version='5.3.0',description='Local AI video repurposing studio')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
JOBS={}; LOCK=threading.Lock()

class ProcessOptions(BaseModel):
    num_clips:int=Field(5,ge=1,le=10); clip_duration:int=Field(30,ge=15,le=60)
    captions:bool=True; dynamic_captions:bool=True; model:str=Field('base',pattern=r'^(tiny|base|small|medium)$')
    smart_crop:bool=True; generate_metadata:bool=True; language:str=Field('auto',pattern=r'^(auto|en|hi|ta|te|ml|kn)$')
    caption_style:str=Field('bold',pattern=r'^(classic|bold|minimal)$'); crop_mode:str=Field('center',pattern=r'^(center|blur|fit|face)$')
    normalize_audio:bool=True; quality:str=Field('high',pattern=r'^(standard|high|max)$'); hook_overlay:bool=False; remove_filler:bool=True
class YouTubeRequest(BaseModel): url:HttpUrl; options:ProcessOptions=Field(default_factory=ProcessOptions)

def job(j,**v):
    with LOCK:
        if j in JOBS:JOBS[j].update(v)
def ff(args,timeout=None):
    r=subprocess.run([FFMPEG,*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
    if r.returncode: raise RuntimeError(r.stderr[-6000:] or 'FFmpeg failed')
    return r

def probe(p):
    r=subprocess.run([FFMPEG,'-hide_banner','-i',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    m=re.search(r'Duration:\s*(\d+):(\d+):([\d.]+)',r.stderr)
    if not m: raise RuntimeError('Could not read video duration')
    d=int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3)); v=re.search(r'Stream #.*?: Video:.*?(\d{2,5})x(\d{2,5})',r.stderr)
    return d,bool(re.search(r'Stream #.*?: Audio:',r.stderr)),(int(v.group(1)),int(v.group(2))) if v else (1920,1080)

def transcribe(p,model,lang):
    try:
        import whisper
        kw={'fp16':False,'verbose':False,'temperature':0,'condition_on_previous_text':True,'word_timestamps':True}
        if lang!='auto':kw['language']=lang
        r=whisper.load_model(model).transcribe(str(p),**kw)
        if not r.get('text','').strip():raise RuntimeError('Whisper returned an empty transcript')
        return {'text':r.get('text',''),'segments':r.get('segments',[]),'language':r.get('language','unknown')}
    except Exception as e:return {'text':'','segments':[],'language':'unknown','error':str(e)}

HOOK={'amazing','important','secret','mistake','problem','solution','best','worst','never','always','how','why','truth','tip','tips','learn','learned','money','success','failure','hack','easy','hard','avoid','key','reason','idea','powerful','actually','real','wrong','simple','nobody','everyone','first','only','instead','remember','warning','free','shocking','crazy','story','lesson','because','result','change'}
def score(t):
    w=re.findall(r"[a-zA-Z0-9']+",t.lower()); u=set(w)
    if not w:return 0
    s=38+min(30,sum(4 for x in HOOK if x in u))+10*('?' in t)+6*('!' in t)+6*(len(w)>=18)+5*(len(w)>=35)+5*any(x.isdigit() for x in w)
    return round(max(1,min(100,s)),1)
def candidates(tr,d,target,n,remove):
    seg=[s for s in tr.get('segments',[]) if str(s.get('text','')).strip()]
    if not seg:return []
    w=min(float(n),d); out=[]
    for i,s in enumerate(seg):
        a=float(s.get('start',0)); st=max(0,a-min(6,w*.2)); st=min(st,max(0,d-w)); en=min(d,st+w)
        near=[x for x in seg if float(x.get('end',0))>=st and float(x.get('start',0))<=en]; text=' '.join(str(x.get('text','')).strip() for x in near)
        sc=score(text)
        if remove and len(re.findall(r'\b(?:um|uh|erm|hmm)\b',text.lower()))>=3:sc-=8
        out.append({'start':st,'end':en,'text':text,'score':max(1,sc),'anchor':i})
    out.sort(key=lambda x:(x['score'],len(x['text'])),reverse=True); sel=[]
    for x in out:
        if any(x['start']<y['end'] and x['end']>y['start'] for y in sel):continue
        sel.append(x)
        if len(sel)>=target:break
    return sorted(sel,key=lambda x:x['start'])
def fallback(d,target,n):
    n=min(float(n),d); c=min(target,max(1,int((d+n-1)//n))); usable=max(0,d-n); starts=[0] if c==1 else [usable*i/(c-1) for i in range(c)]
    return [{'start':s,'end':min(d,s+n),'text':'','score':50,'anchor':i} for i,s in enumerate(starts)]

def metadata(text,num):
    words=re.findall(r'[a-zA-Z0-9]+',text.lower()); stop={'the','and','that','this','with','from','your','have','what','when','then','they','will','about','just','into','are','you','for'}; f={}
    for w in words:
        if len(w)>3 and w not in stop:f[w]=f.get(w,0)+1
    top=[w for w,_ in sorted(f.items(),key=lambda x:x[1],reverse=True)[:7]]
    title=(' '.join(text.split()[:10]) or f'AI Short #{num}').strip('.,!?;:')[:72]
    return {'title':title,'description':text[:500],'hashtags':['#Shorts','#ClipForgeAI']+['#'+w.title() for w in top],'keywords':top}

def vf(opt,face=None):
    if not opt.smart_crop or opt.crop_mode=='fit':return 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2'
    if opt.crop_mode=='blur':return 'split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=18:2[blur];[fg]scale=1080:1920:force_original_aspect_ratio=decrease[main];[blur][main]overlay=(W-w)/2:(H-h)/2'
    if opt.crop_mode=='face' and face is not None:return f'scale=-2:1920,crop=1080:1920:max(0,min(iw-iw*9/16,iw*{face}-iw*9/32)):0'
    return 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920'

def subtitle_file(tr,start,end,dynamic,style):
    from dynamic_captions import make_dynamic_ass
    ext='.ass' if dynamic else '.srt'; p=Path(tempfile.mktemp(suffix=ext))
    if dynamic and make_dynamic_ass(tr,start,end,p,style):return p,'ass'
    rows=['1'];
    for s in tr.get('segments',[]):
        a,b=float(s.get('start',0)),float(s.get('end',0))
        if b<=start or a>=end:continue
        def ts(x):
            x=max(0,x); ms=int(x*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); sec,ms=divmod(ms,1000); return f'{h:02}:{m:02}:{sec:02},{ms:03}'
        rows += [ts(max(0,a-start))+' --> '+ts(min(end-start,b-start)),str(s.get('text','')).strip(),'']
    p.write_text('\n'.join(rows),encoding='utf-8'); return p,'srt'

def render_short(src,out,start,dur,tr,opt,face):
    temp=None; source=src; local_tr=tr
    if opt.remove_filler and tr.get('segments'):
        from filler_removal import render_without_fillers
        temp=Path(tempfile.mktemp(suffix='.mp4')); ok,shifted=render_without_fillers(FFMPEG,src,temp,start,start+dur,tr.get('segments',[]))
        if ok: source=temp; start=0; dur=probe(temp)[0]; local_tr={'segments':shifted,'text':tr.get('text',''),'language':tr.get('language','unknown')}
    filters=[vf(opt,face)]
    sub=None
    try:
        if opt.captions and local_tr.get('segments'):
            sub,kind=subtitle_file(local_tr,start,start+dur,opt.dynamic_captions,opt.caption_style); s=str(sub).replace('\\','/').replace(':','\\:'); filters.append(('ass=' if kind=='ass' else 'subtitles=')+s)
        crf={'standard':'26','high':'23','max':'20'}[opt.quality]; args=['-y','-ss',f'{start:.3f}','-i',str(source),'-t',f'{dur:.3f}','-vf',','.join(filters),'-c:v','libx264','-preset','veryfast','-crf',crf,'-pix_fmt','yuv420p','-c:a','aac','-b:a','160k']
        if opt.normalize_audio:args += ['-af','loudnorm=I=-14:TP=-1.5:LRA=11']
        args += ['-movflags','+faststart',str(out)]; ff(args,600)
    finally:
        if sub:sub.unlink(missing_ok=True)
        if temp:temp.unlink(missing_ok=True)

def process_file(src,jid,opt):
    job(jid,progress=35,message='Inspecting video and audio…'); d,a,res=probe(src); job(jid,progress=48,message=f'Transcribing with local Whisper ({opt.model})…'); tr=transcribe(src,opt.model,opt.language) if a else {'text':'','segments':[],'language':'unknown','error':'No audio stream found'}
    job(jid,progress=62,message='Finding hooks and removing filler…'); hs=candidates(tr,d,opt.num_clips,opt.clip_duration,opt.remove_filler) or fallback(d,opt.num_clips,opt.clip_duration)
    face=None
    if opt.smart_crop and opt.crop_mode=='face':
        try:
            from face_framing import detect_speaker_center; face=detect_speaker_center(src,FFMPEG)
        except Exception:pass
    clips=[]
    for i,h in enumerate(hs,1):
        start=float(h['start']); actual=min(float(opt.clip_duration),d-start); out=OUTPUT_DIR/f'{jid}_clip_{i}.mp4'; render_short(src,out,start,actual,tr,opt,face)
        clips.append({'clip_number':i,'title':metadata(h['text'],i)['title'],'score':h['score'],'text':h['text'],'start':round(start,2),'end':round(start+actual,2),'duration':round(actual,2),'download_url':f'/download/{out.name}','metadata':metadata(h['text'],i),'format':'9:16','resolution':'1080x1920','framing':'face-aware' if face is not None and opt.crop_mode=='face' else opt.crop_mode})
        job(jid,progress=min(95,70+int(i/max(1,len(hs))*25)),message=f'Rendered clip {i}/{len(hs)}')
    man={'job_id':jid,'source':src.name,'source_duration':d,'source_resolution':f'{res[0]}x{res[1]}','settings':opt.model_dump(),'face_center':face,'automatic_filler_removal':opt.remove_filler,'clips':clips}; mp=OUTPUT_DIR/f'{jid}_manifest.json'; mp.write_text(json.dumps(man,indent=2,ensure_ascii=False),encoding='utf-8'); zp=OUTPUT_DIR/f'{jid}_shorts.zip'
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for c in clips:z.write(OUTPUT_DIR/Path(c['download_url']).name,Path(c['download_url']).name)
        z.write(mp,mp.name)
    return {'job_id':jid,'status':'completed','duration':d,'transcript':tr.get('text',''),'transcript_language':tr.get('language','unknown'),'transcription_error':tr.get('error'),'clips':clips,'download_all_url':f'/download-all/{jid}','manifest_url':f'/download/{mp.name}'}

def run_job(jid,src,opt):
    try:job(jid,status='processing'); r=process_file(src,jid,opt); job(jid,status='completed',progress=100,message='Done',result=r)
    except Exception as e:job(jid,status='failed',progress=100,message=str(e),error=str(e))
    finally:src.unlink(missing_ok=True)

@app.get('/')
def root():return {'name':'ClipForge AI','version':'5.3.0','format':'9:16','resolution':'1080x1920','automatic_filler_removal':True,'face_aware_framing':True}
@app.get('/health')
def health():return {'status':'ok','version':'5.3.0','ffmpeg':Path(FFMPEG).name,'whisper':_module('whisper'),'opencv':_module('cv2'),'features':['local-whisper','hook-ranking','automatic-filler-removal','silence-trimming','dynamic-word-captions','face-aware-framing','9:16','1080x1920','audio-normalization','metadata','zip-export']}
def _module(n):
    try:__import__(n);return True
    except Exception:return False
@app.post('/process')
async def process(background_tasks:BackgroundTasks,file:UploadFile=File(...),options:str='{}'):
    suf=Path(file.filename or 'video.mp4').suffix.lower()
    if suf not in ALLOWED:raise HTTPException(400,'Unsupported video format')
    try:o=ProcessOptions.model_validate_json(options)
    except Exception as e:raise HTTPException(400,f'Invalid options: {e}')
    jid=str(uuid.uuid4()); p=UPLOAD_DIR/f'{jid}{suf}'
    with p.open('wb') as out:
        size=0
        while chunk:=await file.read(1024*1024):
            size+=len(chunk)
            if size>MAX_UPLOAD:p.unlink(missing_ok=True);raise HTTPException(413,'Video exceeds 2 GB limit')
            out.write(chunk)
    with LOCK:JOBS[jid]={'job_id':jid,'status':'queued','progress':5,'message':'Video uploaded…'}
    background_tasks.add_task(run_job,jid,p,o);return {'job_id':jid}
@app.post('/process-url')
async def process_url(req:YouTubeRequest,background_tasks:BackgroundTasks):
    url=str(req.url)
    if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)(/|$)',url,re.I):raise HTTPException(400,'Only YouTube URLs are supported')
    jid=str(uuid.uuid4());p=UPLOAD_DIR/f'{jid}.mp4';JOBS[jid]={'job_id':jid,'status':'downloading','progress':8,'message':'Downloading YouTube video…'}
    def work():
        try:
            import yt_dlp
            opts={'format':'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]','outtmpl':str(p.with_suffix(''))+'.%(ext)s','merge_output_format':'mp4','noplaylist':True,'ffmpeg_location':FFMPEG}
            try:
                if subprocess.run(['deno','--version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:opts['js_runtimes']={'deno':{}}
            except Exception:pass
            with yt_dlp.YoutubeDL(opts) as y: y.download([url])
            produced=max(p.parent.glob(p.stem+'*'),key=lambda x:x.stat().st_size); shutil.move(str(produced),str(p)); run_job(jid,p,req.options)
        except Exception as e:job(jid,status='failed',progress=100,message=str(e),error=str(e));p.unlink(missing_ok=True)
    background_tasks.add_task(work);return {'job_id':jid}
@app.get('/jobs/{jid}')
def status(jid):
    if jid not in JOBS:raise HTTPException(404,'Job not found')
    return JOBS[jid]
@app.get('/download/{filename}')
def download(filename):
    p=OUTPUT_DIR/Path(filename).name
    if not p.is_file():raise HTTPException(404,'File not found')
    return FileResponse(p)
@app.get('/download-all/{jid}')
def all_download(jid):
    p=OUTPUT_DIR/f'{jid}_shorts.zip'
    if not p.is_file():raise HTTPException(404,'ZIP not found')
    return FileResponse(p,filename=p.name,media_type='application/zip')
@app.get('/transcript/{jid}')
def transcript(jid):
    if jid not in JOBS:raise HTTPException(404,'Job not found')
    r=JOBS[jid].get('result',{});return {'job_id':jid,'language':r.get('transcript_language','unknown'),'text':r.get('transcript',''),'error':r.get('transcription_error')}
