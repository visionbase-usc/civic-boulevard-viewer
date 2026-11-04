#!/usr/bin/env python3
"""Extract only referenced official records from downloaded snapshots.

Usage: python extract_official_audit.py SNAPSHOT_DIRECTORY
Requires pyshp, pyproj, shapely. Keeps field evidence and source hashes,
not the full city datasets. Run before audit_records.py, then build_data.py.
"""
import csv, gzip, json, sys
from pathlib import Path
from collections import defaultdict
import shapefile
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform

ROOT=Path(__file__).resolve().parents[1]
p=Path(sys.argv[1])
pack=json.loads((ROOT/'docs/data/inventory.js').read_text().split(' = ',1)[1].rstrip(';\n'))
records=pack['records']
park=json.loads((p/'parking.json').read_text())['data']
parks={x['id']:x for x in park['park']}
bikes={x['sno']:x for x in json.loads((p/'youbike.json').read_text())}
bus=json.loads(gzip.decompress((p/'GetStop.gz').read_bytes()))
stops=defaultdict(list)
for x in bus['BusInfo']:stops[str(x['stopLocationId'])].append(x)
toilets=list(csv.DictReader((p/'toilets.csv').read_text(encoding='utf-8-sig').splitlines()))
xy=Transformer.from_crs(3826,4326,always_xy=True).transform
cross={}
needed={r['id'] for r in records if r['table']=='行穿線圖形'}
for f in p.glob('crossings/**/*.shp'):
    reader=shapefile.Reader(str(f))
    for item in reader.iterShapeRecords():
        raw=item.record.as_dict(); rid=f"C-{f.stem.split('_')[1]}-{raw['keyid']}"
        if rid not in needed:continue
        geom=transform(xy,shape(item.shape.__geo_interface__))
        fields=['keyid','licode','rditcd','rdcode','liarea','rddate','edittime','rdlblg','rdlbwt','zlocation']
        cross[rid]={'layer':f.stem,'fields':{k:str(raw[k]) if raw[k] is not None else None for k in fields},'geometry':mapping(geom)}
out={}
for r in records:
    rid=r['id'];o=r['original']
    if r['category']=='parking':
        raw=parks.get(rid[2:]); row={'dataset':'parking','sourceDate':park['UPDATETIME'],'key':rid[2:],'raw':raw}
        if raw:row['registeredPosition']=xy(float(raw['tw97x']),float(raw['tw97y']))
    elif r['table']=='車輛入口' or rid.startswith('F-TPE'):
        pid=r['parent'][2:];raw=parks.get(pid)
        row={'dataset':'parking','sourceDate':park['UPDATETIME'],'key':pid,'raw':raw}
    elif rid.startswith('Y-'):
        raw=bikes.get(rid[2:]); row={'dataset':'youbike','sourceDate':raw['srcUpdateTime'] if raw else None,'key':rid[2:],'raw':raw}
    elif rid.startswith('B-'):
        row={'dataset':'bus','sourceDate':bus['EssentialInfo']['UpdateTime'],'key':rid[2:],'raw':stops.get(rid[2:],[])}
    elif rid.startswith('T-'):
        raw=[x for x in toilets if x['公廁名稱']==o['名稱'] and x['公廁地址']==o['地址或鄰近路口']]
        row={'dataset':'toilets','sourceDate':'2026-08-24 10:59:06（資料集檔案更新）','key':{'公廁名稱':o['名稱'],'公廁地址':o['地址或鄰近路口']},'raw':raw}
    elif rid in needed:
        row={'dataset':'crossings','sourceDate':'SHP壓縮檔2024-07-12；資料頁2026-03-19','key':rid,'raw':cross.get(rid)}
    else:continue
    out[rid]=row
# Avoid publishing unrelated citywide rows or personal editor names from GIS fields.
result={'checkedAt':'2026-11-04','scope':pack['scope']['name'],'manifest':json.loads((p/'manifest.json').read_text()),'records':out}
(ROOT/'source/official-records.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
print(f'Extracted {len(out)} individually keyed source records')
