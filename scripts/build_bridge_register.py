#!/usr/bin/env python3
"""Render the partial bridge-column register without inferring missing IDs/coordinates."""
import csv, html, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/bridge-columns'
def build():
    data = json.loads((BASE/'column-register.json').read_text())
    rows = data['records']
    assert len({r['physicalIdentity'] for r in rows}) == len(rows)
    assert all(r['geometry'] is None for r in rows), 'Coordinates require a separate reviewed source.'
    assert data['verifiedWholeScopeTotal'] is None
    data['physicalColumnsObserved'] = len(rows)
    data['numberedPhysicalColumnsObserved'] = sum(bool(r['observedMark']) for r in rows)
    data['readableDistinctMarks'] = len({r['observedMark'] for r in rows if r['observedMark']})
    data['locatedRecords'] = 0
    for r in rows:
        r['countMeaning'] = '本筆為已區分的單一實體柱；同號的其他實體柱另列。'
    (BASE/'column-register.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    fields=['id','observedMark','side','locationDescription','imageryDate','checkedAt','streetviewUrl','finding','coordinateStatus','physicalIdentity']
    with (BASE/'column-register.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
    e=lambda v:html.escape(str(v or '未確認'),quote=True)
    body=''.join('<tr>'+''.join('<td>'+e(r.get(k))+'</td>' for k in ['id','observedMark','side','locationDescription','imageryDate','finding'])+'<td><a rel="noopener" target="_blank" href="'+e(r['streetviewUrl'])+'">原始街景</a></td></tr>' for r in rows)
    sections=json.loads((BASE/'section-reviews.json').read_text())['sections']
    sectiontext=''.join('<p>'+e(s['scope'])+'：已區分 '+str(s['physicalColumnCount'])+' 根；'+e(s['countBasis'])+'</p>' for s in sections)
    page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>市民大道橋柱查核清冊</title><style>body{font:16px/1.7 system-ui,sans-serif;color:#183343;background:#f5f7f8;margin:0;padding:24px}h1{font-size:24px}table{border-collapse:collapse;background:white;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}a{color:#006c82}aside{padding:16px;background:#fff3d5}.scroll{overflow:auto}</style><h1>市民大道橋柱查核清冊</h1>'''
    page+=f'<p>{e(data["scope"])}｜查核日期 {e(data["checkedAt"])}</p><aside><b>部分查核：已區分 {len(rows)} 根實體柱；其中 {data["numberedPhysicalColumnsObserved"]} 根可辨號、{data["readableDistinctMarks"]} 個不同柱號。全範圍總數未核定。</b><br>可靠柱位座標 0 筆，全部保留清冊、不落點。柱面文字不等於已核定官方管理墩號。</aside>'
    page+='<p>同號南北兩柱各列一筆，同柱不同視角不重複計數。未辨號視角另存，不加入實體柱數；不從連號、間距、相機座標補位置。</p>'+sectiontext
    page+='<div class="scroll"><table><thead><tr><th>實體暫編</th><th>柱面文字</th><th>南北側</th><th>位置敘述</th><th>影像日期</th><th>直接觀察</th><th>來源</th></tr></thead><tbody>'+body+'</tbody></table></div><p><a href="column-register.csv">CSV 清冊</a> · <a href="column-register.json">JSON 清冊</a> · <a href="unresolved-observations.json">未去重視角</a></p><p>影像日期與查核日期分開記錄。尚未完成中山北路至光復南路兩側全部逐柱核對。</p></html>'
    (BASE/'review.html').write_text(page)
    print(json.dumps({k:data[k] for k in ['physicalColumnsObserved','numberedPhysicalColumnsObserved','readableDistinctMarks','locatedRecords','verifiedWholeScopeTotal']},ensure_ascii=False))
if __name__=='__main__':build()
