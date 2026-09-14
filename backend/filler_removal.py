from __future__ import annotations
from pathlib import Path
import re
import subprocess
from typing import Any

FILLER_RE = re.compile(r"\b(?:um+|uh+|erm+|hmm+|mm+|you know|i mean|basically|actually)\b", re.I)

def filler_ranges(segments: list[dict[str, Any]], min_pause: float = 0.65) -> list[tuple[float, float]]:
    ranges=[]
    for seg in segments:
        text=str(seg.get("text","")); s,e=float(seg.get("start",0)),float(seg.get("end",0))
        if e>s and FILLER_RE.search(text.strip()) and e-s<=3.0: ranges.append((s,e))
    for a,b in zip(segments,segments[1:]):
        gap=float(b.get("start",0))-float(a.get("end",0))
        if gap>=min_pause: ranges.append((float(a.get("end",0)),float(b.get("start",0))))
    return merge_ranges(ranges)

def merge_ranges(ranges):
    if not ranges:return []
    ranges=sorted((max(0,s),max(0,e)) for s,e in ranges if e>s); out=[ranges[0]]
    for s,e in ranges[1:]:
        ps,pe=out[-1]
        if s<=pe+0.08: out[-1]=(ps,max(pe,e))
        else: out.append((s,e))
    return out

def build_keep_ranges(start,end,remove,pad=0.06):
    cuts=merge_ranges([(max(start,s-pad),min(end,e+pad)) for s,e in remove if e>start and s<end]); keep=[]; cur=start
    for s,e in cuts:
        if s>cur+0.03: keep.append((cur,s))
        cur=max(cur,e)
    if end>cur+0.03:keep.append((cur,end))
    return keep

def _map_time(t,start,keep):
    t=max(start,t); removed=sum(max(0,min(t,e)-s) for s,e in keep if e<=t)
    return t-start-removed

def shift_segments(segments,start,keep):
    out=[]
    for seg in segments:
        s,e=float(seg.get("start",0)),float(seg.get("end",0))
        if e<=start or s>=start+sum(b-a for a,b in keep): continue
        mapped=dict(seg); ns,ne=_map_time(s,start,keep),_map_time(e,start,keep)
        if ne<=ns+0.03:continue
        mapped["start"],mapped["end"]=ns,ne
        words=[]
        for word in seg.get("words") or []:
            ws,we=float(word.get("start",s)),float(word.get("end",e))
            if we<=start or ws>=max(b for _,b in keep):continue
            w=dict(word);w["start"],w["end"]=_map_time(ws,start,keep),_map_time(we,start,keep);words.append(w)
        mapped["words"]=words;out.append(mapped)
    return out

def render_without_fillers(ffmpeg,source,output,start,end,segments):
    cuts=filler_ranges(segments);keep=build_keep_ranges(start,end,cuts)
    if not cuts or len(keep)<=1:return False,[]
    inputs=[];filters=[]
    for i,(s,e) in enumerate(keep):
        inputs += ["-ss",f"{s:.3f}","-to",f"{e:.3f}","-i",str(source)]
        filters.append(f"[{i}:v:0][{i}:a:0]setpts=PTS-STARTPTS,asetpts=PTS-STARTPTS[v{i}][a{i}]")
    joined="".join(f"[v{i}][a{i}]" for i in range(len(keep)));filters.append(f"{joined}concat=n={len(keep)}:v=1:a=1[v][a]")
    cmd=[ffmpeg,"-hide_banner","-loglevel","error",*inputs,"-filter_complex",";".join(filters),"-map","[v]","-map","[a]","-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","160k","-movflags","+faststart","-y",str(output)]
    try:
        r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=600)
        return (r.returncode==0 and output.exists() and output.stat().st_size>1024,shift_segments(segments,start,keep)) if r.returncode==0 else (False,[])
    except Exception:return False,[]
