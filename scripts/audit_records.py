#!/usr/bin/env python3
"""Reproducible per-record comparisons with official evidence, no network required.

The downloaded source subset is versioned in source/official-records.json.
Manual document/page observations are versioned separately. This audit validates
source support, not unobserved present-day physical conditions or completeness.
"""
import csv, json, math
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
pack=json.loads((ROOT/'docs/data/inventory.js').read_text().split(' = ',1)[1].rstrip(';\n'))
evidence=read('source/official-records.json')
manual=read('source/document-audit.json')
rows=[]
def close(a,b,tol=1e-7):return isinstance(a,(int,float)) and isinstance(b,(int,float)) and abs(a-b)<=tol
def equal_geom(a,b):
    # Geometry vertex coordinates are compared independently of ring start/direction.
    def pts(x):
        if isinstance(x,list) and len(x)>=2 and isinstance(x[0],(int,float)):return [tuple(round(v,9) for v in x[:2])]
        return [p for y in x for p in pts(y)]
    return a['type']==b['type'] and set(pts(a['coordinates']))==set(pts(b['coordinates']))
for r in pack['records']:
    rid=r['id'];o=r['original'];ev=evidence['records'].get(rid)
    a={'id':rid,'checkedAt':evidence['checkedAt'],'method':'官方資料逐欄比對','result':'official','checks':[],'issues':[],'sources':[], 'updates':{}}
    def check(field,actual,expected,ok=None):
        good=actual==expected if ok is None else ok
        a['checks'].append({'field':field,'result':'match' if good else 'difference','inventory':actual,'source':expected})
        if not good:a['issues'].append(field+'與重新取得的官方來源不一致')
    if ev:
        a['sourceDate']=ev['sourceDate']; a['sourceKey']=ev['key'];a['dataset']=ev['dataset']
        a['sources']=[o['來源連結']];raw=ev['raw']
        if not raw:
            a['result']='unresolved';a['issues'].append('未在本次官方快照找到對應紀錄');rows.append(a);continue
        if r['category']=='parking':
            for field,key in [('名稱','name'),('地址或鄰近路口','address'),('原始管理類型','type2'),('小型車格','totalcar'),('機車格','totalmotor')]:check(field,o.get(field),raw[key])
            for field,val in zip(['經度','緯度'],ev['registeredPosition']):check(field,o[field],val,close(o[field],val))
            check('停車場編號',rid[2:],raw['id'])
            a['position']='官方場站代表點；不是場站邊界或個別入口'
            a['summary']='停車場編號、名稱、地址、管理類型、汽機車格數及轉換座標逐欄一致。'
        elif r['table']=='車輛入口':
            entries=raw.get('EntranceCoord',{}).get('EntrancecoordInfo',[])
            n=int(rid.rsplit('-',1)[1])-1
            ent=entries[n] if n<len(entries) else None
            if ent is None:a['result']='unresolved';a['issues'].append('來源未列此序號入口')
            else:
                check('所屬停車場',r['parent'],'P-'+raw['id'])
                check('名稱',o['名稱'],raw['name']+'／'+ent['Address'])
                lon,lat=float(ent['Ycod']),float(ent['Xcod'])
                check('經度',o['經度'],lon,close(o['經度'],lon));check('緯度',o['緯度'],lat,close(o['緯度'],lat))
                a['sourceKey']={'park':raw['id'],'entranceOrdinal':n+1}
                a['position']='官方登錄入口位置（來源欄位 Xcod 為緯度、Ycod 為經度）'
                if not (121.4<lon<121.7 and 24.9<lat<25.3):
                    a['result']='official-with-issue';a['issues'].append('官方座標為0,0或超出臺北範圍，不採用為地圖位置');a['position']='官方入口紀錄可採用；座標無效，未定位'
            a['summary']='逐筆核對所屬停車場、入口序號與登錄座標；來源未載的出口、進出方向及完整口數維持未知。'
        elif rid.startswith('F-TPE'):
            check('所屬停車場',r['parent'],'P-'+raw['id']);check('充電樁數量',o['來源數值'],float(raw['ChargingStation']))
            a['sources'].append('https://data.taipei/dataset/detail?id=d5c0656b-5250-4179-a491-c94daa56ef2c')
            a['position']='場站層級數量；官方資料未提供每支充電樁座標'
            a['summary']='ChargingStation 數值與所屬場站一致；資料集欄位定義為充電樁數量。'
        elif rid.startswith('Y-'):
            for field,key in [('名稱','sna'),('地址或鄰近路口','ar'),('經度','longitude'),('緯度','latitude')]:check(field,o.get(field),raw[key])
            # Display names intentionally omit the provider prefix.
            if a['checks'][0]['result']=='difference' and o['名稱']==raw['sna'].replace('YouBike2.0_',''):
                a['checks'][0]['result']='match';a['issues'].remove('名稱與重新取得的官方來源不一致')
            a['position']='官方站點座標';a['summary']='依站號核對站名、地址及站點座標；即時借還車數不作為固定盤點屬性。'
        elif rid.startswith('B-'):
            check('站位識別碼',rid[2:],str(raw[0]['stopLocationId']))
            for field,key in [('名稱','nameZh'),('地址或鄰近路口','address')]:check(field,o[field],raw[0][key],any(o[field]==x[key] for x in raw))
            for field,key in [('經度','longitude'),('緯度','latitude')]:check(field,o[field],float(raw[0][key]),any(close(o[field],float(x[key])) for x in raw))
            a['position']='官方 stopLocationId 站位座標；同名不同站位分列'
            a['summary']='逐筆核對 stopLocationId、站名、座標及原始地址；路線停靠資料依站位合併。'
            if rid in ['B-1222','B-1501','B-1001120']:
                a['result']='official-with-issue'
                a['issues'].append({'B-1222':'官方地址「林森北路573號」與市民林森路口站名、座標所在路段不一致。','B-1501':'官方地址「台北市向陽路」與市民延吉街口站名、座標所在路段不一致。','B-1001120':'官方地址門牌與「微風廣場大門口」描述及座標疑有不一致，門牌暫不作定位依據。'}[rid])
                a['updates']={'地址或鄰近路口':'依官方站名及登錄座標查找；原始地址疑有誤，見查核紀錄','確認程度':'官方站名及登錄座標已核；地址文字待確認','待確認事項':a['issues'][-1]+' 原始文字保留於來源紀錄。'}
        elif rid.startswith('T-'):
            if len(raw)!=1:a['result']='unresolved';a['issues'].append('名稱＋地址配對不唯一')
            else:
                raw=raw[0]
                for field,key in [('名稱','公廁名稱'),('地址或鄰近路口','公廁地址')]:check(field,o[field],raw[key])
                for field in ['經度','緯度']:check(field,o[field],float(raw[field]),close(o[field],float(raw[field])))
                check('來源座數',o['來源數值'],int(raw['座數']))
            a['position']='官方公廁場所登錄點；不是每個廁間的精確位置'
            a['summary']='依名稱＋地址唯一配對，再核對經緯度及座數；T編號是盤點編號，不冒充官方識別碼。'
        elif r['table']=='行穿線圖形':
            check('圖層',o['圖層'],raw['layer']);check('原始keyid',str(o['原始keyid']),raw['fields']['keyid'])
            check('幾何逐頂點',True,equal_geom(r['geometry'],raw['geometry']))
            check('原始編修日期',o['原始編修日期'],raw['fields']['edittime'])
            a['position']='官方SHP完整圖形轉WGS84；不是完整南北穿越路徑'
            a['summary']='圖層、keyid、幾何頂點及編修日期與重新下載的官方SHP一致。'
            a['updates']={'類別':'行穿線圖形（官方圖資）','確認程度':'官方圖形逐筆核對；完整通行關係未載'}
            if r.get('review'):
                a['result']='official-with-issue';a['issues'].append('已有街景顯示穿越設施，但官方局部圖形不足以表達完整穿越範圍；保留來源幾何，不補畫推測邊界。')
    elif r.get('access'):
        item=r['access'];a['method']='官方PDF頁面逐口目視核對';a['result']='document'
        a['sourceDate']=item['document']['date'];a['sources']=[item['document']['url']+'#page='+str(item['document']['page'])]
        a['sourceKey']={'page':item['document']['page'],'number':item['number'],'parent':r['parent']}
        a['checks']=[{'field':k,'result':'match','source':v} for k,v in [('梯號',item['number']),('所屬停車場',r['parent']),('相對位置',item['location']),('設施性質','地面層樓梯口')]]
        a['summary']='官方地面層圖載明此編號樓梯、所屬場站與相對位置，採用為行人出入口資料。'
        a['position']='圖說相對位置可採用；無地理座標，保留在清單中'
    elif r['isIndex']:
        a['result']='index';a['method']='逐群檢查成員與來源圖形關聯';a['sourceDate']='2026-11-04（派生查找索引）'
        a['sources']=[o['來源連結']];a['sourceKey']=r['members']
        ok=all(x in evidence['records'] and evidence['records'][x]['raw'] for x in r['members'])
        check('全部成員可回查官方圖形',True,ok)
        a['summary']=f"{len(r['members'])} 個成員均保留獨立官方圖形；此群為查找用派生索引，不是官方路口紀錄。"
        a['position']='成員幾何集合；不新增設施數量'
    else:
        assert rid in manual['records'],f'Unreviewed record: {rid}'
        a.update(manual['records'][rid]);a['id']=rid;a['checkedAt']=evidence['checkedAt']
    if any(c['result']=='difference' for c in a['checks']):a['result']='official-with-issue'
    rows.append(a)
assert len({a['id'] for a in rows})==len(pack['records'])
out={'checkedAt':evidence['checkedAt'],'scope':pack['scope']['name'],'policy':'官方公開資料或圖說直接支持的欄位可採用；未知欄位不推定，派生索引不計設施。','summary':dict(Counter(a['result'] for a in rows)),'records':rows}
(ROOT/'source/record-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out['summary'],ensure_ascii=False))
for a in rows:
    if a['issues']:print(a['id'],a['issues'])
