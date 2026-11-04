#!/usr/bin/env python3
"""Rebuild the portable browser data pack from versioned public-source snapshots."""
import json, re, hashlib
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
src = json.loads((ROOT/'source/inventory.json').read_text())
osm = json.loads((ROOT/'source/osm-roads.json').read_text())
categories = [
    dict(id='parking', name='停車場', color='#174b70', icon='P'),
    dict(id='entrance', name='車輛出入口', color='#d85a29', icon='E'),
    dict(id='crossing', name='行人穿越／停車場行人入口', color='#7a4db1', icon='↔'),
    dict(id='transit', name='公共運輸', color='#287c9c', icon='▣'),
    dict(id='public', name='公共空間與服務', color='#427747', icon='✦'),
    dict(id='utility', name='機電維護', color='#9c7020', icon='⚙'),
]
records=[]
for table,rows in src['datasets'].items():
    if table in ['路段範圍','補件清單']: continue
    for row in rows:
        kind=row['類別']; rid=row['編號']
        if table=='停車場': cat='parking'
        elif table=='車輛入口' or '車輛' in kind: cat='entrance'
        elif table in ['行穿線圖形','過街調查地點'] or '樓梯' in kind: cat='crossing'
        elif kind in ['YouBike','公車站位']: cat='transit'
        elif kind in ['公廁點位','公園綠地','橋下活動空間']: cat='public'
        else: cat='utility'
        geom=src['crossGeoms'].get(rid)
        if geom is None and isinstance(row.get('經度'),(int,float)) and isinstance(row.get('緯度'),(int,float)):
            geom={'type':'Point','coordinates':[row['經度'],row['緯度']]}
        if rid=='X-C076':
            geom={'type':'MultiLineString','coordinates':[[[121.51669,25.04898],[121.51656,25.04847]],[[121.51612,25.04908],[121.51669,25.04898]]]}
        history=table=='歷史圖說設備' or '歷史' in row.get('確認程度','')
        pending=history or geom is None or bool(re.search('待|推估|候選',row.get('確認程度','')+' '+row.get('範圍','')))
        segs=re.findall(r'S[0-8]',row.get('分段',''))
        members=row.get('所含編號','').split('、') if rid.startswith('G-') else []
        records.append(dict(id=rid,name=row['名稱'],category=cat,subtype=kind,table=table,
            segments=segs,geometry=geom,historical=history,pending=pending,
            isIndex=rid.startswith('G-'),parent=row.get('所屬編號',''),
            group=row.get('候選群編號',''),members=members,original=row))
access=json.loads((ROOT/'source/pedestrian-access.json').read_text())
for item in access['items']:
    row=dict(編號=item['id'],分段=item['segment'],名稱=item['name'],類別='停車場行人出入口（樓梯）' if item['groundDocumented'] else '停車場樓梯（地面連通待核）',
        地址或鄰近路口=item['location'],經度=None,緯度=None,座標依據='未取得入口座標；街景相機位置不作為設施座標',範圍='所屬停車場的行人設施，不自動視為道路穿越設施',
        確認程度='文件編號已核；'+(item['groundReview']['imageDate']+'街景已核，現況及定位待核' if item['groundReview'] else '現況及定位待核'),
        來源日期=item['document']['date'],查核日期=item['checkedAt'],來源連結=item['document']['url']+'#page='+str(item['document']['page']),待確認事項=item['limitations'],所屬編號=item['parent'])
    existing=next((r for r in records if r['id']==item['id']),None)
    if existing:
        # Reuse the historical facility ID; preserve the original snapshot as evidence history.
        existing.update(name=item['name'],subtype=row['類別'],historical=False,pending=True,currentSource=row,access=item)
    else:
        records.append(dict(id=item['id'],name=item['name'],category='crossing',subtype=row['類別'],table='停車場行人出入口',segments=[item['segment']],geometry=None,
            historical=False,pending=True,isIndex=False,parent=item['parent'],group='',members=[],original=row,access=item))
byid={r['id']:r for r in records}
assert len(byid)==len(records)
for r in records:
    if r['isIndex']:
        children=[byid[i] for i in r['members']]
        r['segments']=sorted(set(r['segments']).union(*(set(x['segments']) for x in children)))
        # Geometry of a search index means its constituent polygons, not an extra facility.
        r['geometry']={'type':'GeometryCollection','geometries':[x['geometry'] for x in children if x['geometry']]}
    if r['parent']: assert r['parent'] in byid, r['id']
    if r['group']: assert r['group'] in byid, r['id']
reviews=json.loads((ROOT/'source/reviews.json').read_text())
for review in reviews:
    assert review['indexId'] in byid and byid[review['indexId']]['isIndex']
    for rid in review['recordIds']:
        assert rid in byid
        byid[rid]['review']=review
    byid[review['indexId']]['name']=review['displayName']
segments=[]
for s in src['datasets']['路段範圍']:
    coords=[p for w in src['roads'] if w['seg']==s['分段'] for p in w['coords']]
    assert coords
    segments.append(dict(id=s['分段'],name=s['名稱'],west=s['西界'],east=s['東界'],
        note=s['範圍說明'],status=s['確認程度'],source=s['來源連結'],
        bounds=[[min(p[1] for p in coords),min(p[0] for p in coords)],[max(p[1] for p in coords),max(p[0] for p in coords)]],
        center=[sum(p[1] for p in coords)/len(coords),sum(p[0] for p in coords)/len(coords)]))
elevated=[]
for w in osm['elements']:
    if w.get('tags',{}).get('name')=='市民大道高架道路':
        elevated.append({'id':w['id'],'coords':[[p['lon'],p['lat']] for p in w['geometry']]})
assert len(elevated)==30
sources=sorted(set(r.get('currentSource',r['original']).get('來源連結','') for r in records if r['original'].get('來源連結')))
sources=sorted(set(sources).union(ref['url'] for rev in reviews for ref in rev['references']))
sources=sorted(set(sources).union(i['groundReview']['url'] for i in access['items'] if i['groundReview']))
for audit in access['audits']:
    items=[i for i in access['items'] if i['parent']==audit['parent']]
    audit['groundImageReviewed']=sum(bool(i['groundReview']) for i in items)
    audit['locatedCount']=sum(bool(byid[i['id']]['geometry']) for i in items)
pack=dict(version='1.1.1',date=src['date'],categories=categories,segments=segments,records=records,accessAudit=access['audits'],accessScope=access['scope'],
    roads=src['roads'],elevated=elevated,sources=sources,
    meta=dict(pedestrianAccessCount=len(access['items']),documentedGroundAccessCount=sum(i['groundDocumented'] for i in access['items']),accessImageReviewCount=sum(bool(i['groundReview']) for i in access['items']),imageReviewCount=len(reviews),recordCount=len(records),indexCount=sum(r['isIndex'] for r in records),
        categoryCounts=dict(Counter(r['category'] for r in records if not r['isIndex'])),
        snapshotSHA256=hashlib.sha256((ROOT/'source/inventory.json').read_bytes()).hexdigest(),
        roadsSource='OpenStreetMap contributors / ODbL',roadsDate=osm['osm3s']['timestamp_osm_base']))
encoded=json.dumps(pack,ensure_ascii=False,separators=(',',':'),allow_nan=False)
(ROOT/'docs/data/inventory.js').write_text('window.CIVIC_DATA = '+encoded+';\n')
(ROOT/'docs/data/catalog.json').write_text(json.dumps(dict(version=pack['version'],date=pack['date'],sources=sources,meta=pack['meta']),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(pack['meta'],ensure_ascii=False,indent=2))
