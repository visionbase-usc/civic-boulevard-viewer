"""Published study scope; source snapshots stay unchanged for traceability."""
SEGMENTS = ('S2', 'S3', 'S4')
NAME = '中山北路—光復南路'

def clip_line(coords, west, east):
    """Clip a road polyline to the study longitude envelope, keeping all parts."""
    parts=[]; part=[]
    for a,b in zip(coords,coords[1:]):
        dx=b[0]-a[0]; lo,hi=0.,1.
        if dx:
            t1,t2=sorted(((west-a[0])/dx,(east-a[0])/dx))
            lo,hi=max(lo,t1),min(hi,t2)
        elif not west<=a[0]<=east:
            lo,hi=1.,0.
        if lo>hi:
            if len(part)>1: parts.append(part)
            part=[];continue
        p=[a[j]+(b[j]-a[j])*lo for j in range(2)]
        q=[a[j]+(b[j]-a[j])*hi for j in range(2)]
        if p==q:continue
        if part and part[-1]!=p:
            if len(part)>1:parts.append(part)
            part=[]
        if not part:part=[p]
        part.append(q)
    if len(part)>1:parts.append(part)
    return parts

def select_records(records):
    byid={r['id']:r for r in records}
    keep={r['id'] for r in records if not r['isIndex'] and set(r['segments'])&set(SEGMENTS)}
    while True:
        before=set(keep)
        for rid in list(keep):
            r=byid[rid]
            keep.update(x for x in [r['parent'],r['group'],*r['members']] if x)
        # Preserve all registered children of a retained facility, including boundary entrances.
        keep.update(r['id'] for r in records if r['parent'] in keep)
        if keep==before:break
    selected=[r for r in records if r['id'] in keep]
    for r in selected:
        scope_segments=[s for s in r['segments'] if s in SEGMENTS]
        if set(r['segments'])-set(SEGMENTS):
            r['scopeNote']='邊界關聯資料：保留中山北路或光復南路端路口的完整圖形與關聯，不裁切路口設施。'
        if not scope_segments:
            linked=byid.get(r['parent'] or r['group'],{})
            scope_segments=[s for s in linked.get('segments',[]) if s in SEGMENTS]
            r['scopeNote']='邊界關聯資料：為保留範圍內設施或查找群的完整關聯而納入；不代表設施整體位於研究範圍內。'
        r['segments']=scope_segments
    return selected
