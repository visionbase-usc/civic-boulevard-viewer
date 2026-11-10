"""Expose reviewed physical observations separately from the audited facility inventory."""
import json
from pathlib import Path

def load_columns(root):
    source=json.loads((root/'research/bridge-columns/column-register.json').read_text())
    items=source['records']
    assert len({i['physicalIdentity'] for i in items})==len(items)
    assert all(i['geometry'] is None for i in items)
    records=[]
    for i in items:
        side={'north':'北排','south':'南排'}.get(i['side'],'側別待核')
        name=f"橋柱 {i['observedMark'] or '柱號未辨'} · {side}"
        # These are textual road-section associations, not inferred coordinates.
        seg='S4' if i['id'] in {'BC-OBS-002','BC-OBS-003','BC-OBS-004','BC-OBS-005','BC-OBS-006','BC-OBS-008'} else 'S2'
        row={'編號':i['id'],'名稱':name,'類別':'高架橋實體柱（部分清冊）','地址或鄰近路口':i['locationDescription'],
             '範圍':f"{side}；{i['finding']}",'確認程度':'街景柱面已讀；官方墩號對照及座標未核' if i['observedMark'] else '街景實體已區分；柱號及座標未核',
             '來源日期':i['imageryDate'],'查核日期':i['checkedAt'],'來源連結':i['streetviewUrl'],
             '座標依據':'尚無可靠柱位依據；不以街景相機位置或示意圖比例落點',
             '待確認事項':'正式柱號對照、柱位座標、全範圍完整清點及影像日期後現況仍待核。'}
        records.append(dict(id=i['id'],name=name,category='bridge',subtype=row['類別'],table='橋柱街景清冊',segments=[seg],geometry=None,
             historical=False,pending=True,isIndex=False,parent='',group='',members=[],original=row,bridgeColumn=i))
    return dict(status='partial-inventory-not-complete',verifiedWholeScopeTotal=None,physicalColumnsObserved=len(items),
        numberedPhysicalColumnsObserved=sum(bool(i['observedMark']) for i in items),readableDistinctMarks=len({i['observedMark'] for i in items if i['observedMark']}),
        locatedRecords=0,checkedAt=source['checkedAt'],records=records,
        sections=json.loads((root/'research/bridge-columns/section-reviews.json').read_text())['sections'],
        officialReferences=json.loads((root/'research/bridge-columns/official-cctv/sources.json').read_text()))
