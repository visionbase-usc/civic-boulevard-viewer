/* 市民大道資料庫檢視器 — static, portable and source-backed. */
(() => {
'use strict';
const D=window.CIVIC_DATA, $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cats=new Map(D.categories.map(c=>[c.id,c])), records=new Map(D.records.map(r=>[r.id,r]));
const STUDY_BOUNDS=D.scope.viewBounds; // Context margin around the study corridor, not a formal road boundary.
const PUBLIC_URL='https://visionbase-usc.github.io/civic-boulevard-viewer/';
const state={layers:new Set(['parking','entrance']),confirmed:true,pending:true,historical:false,segment:'all',base:'photo',fade:60,labels:true,selected:null};
let restoring=false, resultLimit=60, resultMode='list', searchTimer, tileFailures=0, tilesLoaded=0, baseGeneration=0;
let camera=null;
function readHash(){
 const p=new URLSearchParams(location.hash.slice(1));
 if(p.has('layers')) state.layers=new Set(p.get('layers').split(',').filter(x=>cats.has(x)));
 for(const key of ['confirmed','pending','historical','labels']) if(p.has(key))state[key]=p.get(key)==='1';
 if(D.segments.some(s=>s.id===p.get('seg')))state.segment=p.get('seg');else state.segment='all';
 state.base=p.get('base')==='map'?'map':'photo';
 if(p.has('fade')&&Number.isFinite(Number(p.get('fade'))))state.fade=Math.max(0,Math.min(85,Number(p.get('fade'))));
 state.selected=records.has(p.get('id'))?p.get('id'):null;
 if(p.has('lat')&&p.has('lng')&&p.has('z')){
  const lat=Number(p.get('lat')),lng=Number(p.get('lng')),z=Number(p.get('z'));
  camera=Number.isFinite(lat)&&Number.isFinite(lng)&&Number.isFinite(z)&&lat>=STUDY_BOUNDS[0][0]&&lat<=STUDY_BOUNDS[1][0]&&lng>=STUDY_BOUNDS[0][1]&&lng<=STUDY_BOUNDS[1][1]&&z>=12&&z<=20?{lat,lng,z}:null;
 }
}
readHash();
const map=L.map('map',{zoomControl:false,preferCanvas:true,minZoom:12,maxZoom:20,maxBounds:STUDY_BOUNDS,maxBoundsViscosity:1,zoomSnap:.5,attributionControl:true});
L.control.zoom({position:'bottomright'}).addTo(map);
L.control.scale({position:'bottomright',imperial:false,maxWidth:90}).addTo(map);
map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
map.attributionControl.addAttribution('道路線形 © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>');
map.createPane('labels'); map.getPane('labels').style.zIndex=250;map.getPane('labels').style.pointerEvents='none';
map.createPane('corridor'); map.getPane('corridor').style.zIndex=350;map.getPane('corridor').style.pointerEvents='none';
map.createPane('routeNames');map.getPane('routeNames').style.zIndex=410;map.getPane('routeNames').style.pointerEvents='none';
const corridor=L.layerGroup().addTo(map), names=L.layerGroup().addTo(map), features=L.layerGroup().addTo(map), selection=L.layerGroup().addTo(map);
const allPoints=D.roads.flatMap(w=>w.coords.map(c=>[c[1],c[0]])).concat(D.elevated.flatMap(w=>w.coords.map(c=>[c[1],c[0]])));
const fullBounds=L.latLngBounds(allPoints);
const baseURL=layer=>`https://wmts.nlsc.gov.tw/wmts/${layer}/default/GoogleMapsCompatible/{z}/{y}/{x}`;
const attribution='© <a href="https://maps.nlsc.gov.tw/S09SOA/" target="_blank" rel="noopener">國土測繪中心</a>';
let baseLayer, labelLayer;
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,4000);}
function updateBaseMessage(){
 const box=$('map-message');
 if(!navigator.onLine){box.innerHTML='目前離線：盤點資料仍可查閱，底圖需要網路連線。';box.hidden=false;return;}
 if(tileFailures>0&&tilesLoaded===0){box.innerHTML='底圖暫時無法載入，資料圖層仍可使用。 <button id="retry-base">重試</button> <button id="switch-base">切換底圖</button>';box.hidden=false;$('retry-base').onclick=()=>setBase(state.base);$('switch-base').onclick=()=>setBase(state.base==='photo'?'map':'photo');}
 else if(tileFailures>3){box.textContent='部分底圖未載入；可縮放重試，資料圖層不受影響。';box.hidden=false;}
 else box.hidden=true;
}
function setBase(type){
 state.base=type;tileFailures=0;tilesLoaded=0;const gen=++baseGeneration;
 if(baseLayer)map.removeLayer(baseLayer);
 baseLayer=L.tileLayer(baseURL(type==='photo'?'PHOTO2':'EMAP'),{maxNativeZoom:19,maxZoom:20,minZoom:10,attribution,bounds:STUDY_BOUNDS,noWrap:true,keepBuffer:0,updateWhenIdle:true,updateWhenZooming:false});
 baseLayer.on('tileerror',()=>{if(gen===baseGeneration){tileFailures++;updateBaseMessage();}});
 baseLayer.on('tileload',()=>{if(gen===baseGeneration){tilesLoaded++;updateBaseMessage();}});
 baseLayer.addTo(map);
 document.documentElement.style.setProperty('--photo-filter',type==='photo'?'saturate(.45)':'saturate(.55)');
 for(const v of ['photo','map']){$('base-'+v).classList.toggle('active',v===type);$('base-'+v).setAttribute('aria-pressed',String(v===type));}
 updateLabels();updateBaseMessage();saveHash();
}
function updateLabels(){
 if(labelLayer)map.removeLayer(labelLayer);
 if(state.labels&&state.base==='photo')labelLayer=L.tileLayer(baseURL('EMAP2'),{pane:'labels',minZoom:15,maxNativeZoom:19,maxZoom:20,bounds:STUDY_BOUNDS,noWrap:true,keepBuffer:0,updateWhenIdle:true,updateWhenZooming:false}).addTo(map);
 drawRouteNames();
}
function updateFade(){document.documentElement.style.setProperty('--fade',state.fade/100);$('fade-value').textContent=state.fade+'%';$('fade').value=state.fade;}
function geometryPoints(g){
 if(!g)return[];if(g.type==='GeometryCollection')return g.geometries.flatMap(geometryPoints);
 const out=[];function walk(a){if(typeof a[0]==='number'){out.push([a[1],a[0]]);}else a.forEach(walk);}walk(g.coordinates);return out;
}
function fitBounds(bounds,detail=false){
 const narrow=innerWidth<700;
 map.fitBounds(bounds,{paddingTopLeft:narrow?[28,205]:[40,215],paddingBottomRight:narrow?[35,detail?innerHeight*.52+20:105]:[detail?405:75,90],maxZoom:18.5,animate:false});
}
function fitAll(){if(state.selected)closeDetail();state.segment='all';$('segment').value='all';updateSegmentInfo();fitBounds(fullBounds);saveHash();}
function setSegment(id,fit=true){
 if(fit&&!restoring&&state.selected)closeDetail();
 state.segment=id;$('segment').value=id;updateSegmentInfo();
 if(fit){if(id==='all')fitBounds(fullBounds);else{
  const s=D.segments.find(x=>x.id===id);const b=L.latLngBounds(s.bounds);
  D.records.filter(r=>r.segments.includes(id)&&r.segments.length>1).forEach(r=>geometryPoints(r.geometry).forEach(p=>b.extend(p)));
  fitBounds(b);
 }}
 drawCorridor();drawRouteNames();if(!$('results-panel').hidden&&resultMode==='list')renderResults();saveHash();
}
function updateSegmentInfo(){
 const s=D.segments.find(x=>x.id===state.segment), el=$('segment-info');el.hidden=!s;
 if(s)el.innerHTML=`<strong>${esc(s.id)} · ${esc(s.name)}</strong>${esc(s.west)} → ${esc(s.east)}<br><small>${esc(s.status)}</small>`;
 $('prev-segment').disabled=state.segment===D.segments[0].id;$('next-segment').disabled=state.segment===D.segments.at(-1).id;
}
function drawCorridor(){
 corridor.clearLayers();const z=map.getZoom()||12;
 // Draw lower road context thinly; only sourced elevated ways get the broad ribbon.
 for(const w of D.roads){const active=state.segment==='all'||state.segment===w.seg;
 L.polyline(w.coords.map(p=>[p[1],p[0]]),{pane:'corridor',color:active?'#019ba4':'#829ea0',weight:z>=17?5:2.8,opacity:active?.7:.32,interactive:false}).addTo(corridor);}
 for(const w of D.elevated)L.polyline(w.coords.map(p=>[p[1],p[0]]),{pane:'corridor',color:'#00b5bc',weight:z>=18?22:z>=16?14:7,opacity:.52,lineCap:'round',interactive:false}).addTo(corridor);
}
function drawRouteNames(){
 names.clearLayers();if(!map._loaded)return;
 const z=map.getZoom(), taken=[];
 for(const s of D.segments){
  const p=map.latLngToContainerPoint(s.center);if(!map.getBounds().contains(s.center))continue;
  const long=z>=15.5, width=long?200:120;
  let lift=0, maxLift=innerWidth<700?120:200;
  while(lift<maxLift&&taken.some(t=>Math.abs(t.x-p.x)<width&&Math.abs(t.y-(p.y-lift))<38))lift+=40;
  if(lift>=maxLift)continue;
  taken.push({x:p.x,y:p.y-lift});
  const label=s.name;
  L.marker(s.center,{pane:'routeNames',interactive:false,keyboard:false,icon:L.divIcon({className:'route-label',iconSize:[width,35],iconAnchor:[width/2,45+lift],html:`<span><b class="seg-code">${s.id}</b>${esc(label)}${long?`<small>${esc(s.west)}—${esc(s.east)}</small>`:''}</span>`})}).addTo(names);
 }
}
function allowed(r){return state.layers.has(r.category)&&(r.historical?state.historical:r.pending?state.pending:state.confirmed);}
function statusName(r){if(r.isIndex)return '派生查找索引';if(r.verification?.issues.length)return '官方來源已核／部分欄位待確認';if(r.historical)return '歷史資料';if(!r.geometry)return '官方來源可採用／未定位';return r.verification?'官方來源已核':'公開資料已列';}
function scopeRecords(){return D.records.filter(r=>allowed(r)&&(state.segment==='all'||r.segments.includes(state.segment)));}
function categoryIcon(c){return `<span class="category-icon" style="--color:${c.color}" aria-hidden="true">${c.icon}</span>`;}
function markerIcon(r,small=false){
 const c=cats.get(r.category);
 return L.divIcon({className:'marker-shell',iconSize:[24,24],iconAnchor:[12,12],html:`<span class="facility-marker ${r.category} ${r.pending?'pending':''} ${r.historical?'historical':''} ${r.id===state.selected?'selected':''} ${small?'small':''}" style="--color:${c.color}">${c.icon}</span>`});
}
function bindRecord(layer,r,permanent=false){layer.on('click',e=>{if(e.originalEvent)L.DomEvent.stopPropagation(e.originalEvent);selectRecord(r.id);});layer.bindTooltip(esc(r.name),{direction:'top',offset:[0,-12],permanent});return layer;}
function renderFeatures(){
 if(!map._loaded)return;features.clearLayers();const z=map.getZoom(),view=map.getBounds().pad(.2);
 const current=D.records.filter(r=>!r.isIndex&&allowed(r)&&r.geometry);
 const cells=new Map(), labelTaken=[];
 function labelFree(pt,name){const p=map.latLngToContainerPoint(pt),w=Math.min(220,20+name.length*11);if(labelTaken.some(b=>Math.abs(b.x-p.x)<(b.w+w)/2&&Math.abs(b.y-p.y)<33))return false;labelTaken.push({x:p.x,y:p.y,w});return true;}
 for(const r of current){
  const pts=geometryPoints(r.geometry),b=L.latLngBounds(pts);if(!view.intersects(b))continue;
  if(r.geometry.type!=='Point'&&z>=16){const c=cats.get(r.category);bindRecord(L.geoJSON(r.geometry,{style:{color:r.historical?'#8d928d':c.color,weight:r.geometry.type==='MultiLineString'?4:1.5,opacity:.9,fillOpacity:.22,dashArray:r.pending?'4 3':null}}),r).addTo(features);continue;}
  const pos=b.getCenter();
  if(z<16){const p=map.project(pos,z),k=[r.category,Math.floor(p.x/45),Math.floor(p.y/45)].join('/');if(!cells.has(k))cells.set(k,[]);cells.get(k).push({r,pos});}
  else{const permanent=z>=18&&r.category!=='crossing'&&labelFree(pos,r.name);bindRecord(L.marker(pos,{icon:markerIcon(r),title:r.name,keyboard:true}),r,permanent).addTo(features);}
 }
 for(const items of cells.values()){
  if(items.length===1){const {r,pos}=items[0];bindRecord(L.marker(pos,{icon:markerIcon(r),title:r.name}),r).addTo(features);}
  else{const c=cats.get(items[0].r.category),lat=items.reduce((a,x)=>a+x.pos.lat,0)/items.length,lng=items.reduce((a,x)=>a+x.pos.lng,0)/items.length;
   const m=L.marker([lat,lng],{icon:L.divIcon({className:'marker-shell',iconSize:[30,30],iconAnchor:[15,15],html:`<span class="cluster-marker" style="--color:${c.color}">${items.length}</span>`}),title:`${c.name}：${items.length} 筆資料（聚合）`});
   m.bindTooltip(`${esc(c.name)} · ${items.length} 筆資料，點選展開`);m.on('click',()=>fitBounds(L.latLngBounds(items.map(x=>x.pos))));m.addTo(features);
  }
 }
 // Audited crossing indexes identify an observed place without inventing surveyed boundaries
 // or adding their constituent polygons to the facility count a second time.
 for(const r of D.records.filter(r=>r.isIndex&&r.review&&allowed(r))){
  const pos=[r.original['緯度'],r.original['經度']];if(!view.contains(pos))continue;
  bindRecord(L.marker(pos,{icon:markerIcon(r),title:r.name,zIndexOffset:500}),r,r.id===state.selected).addTo(features);
 }
 // Observation markers locate the evidence camera, never the unmeasured entrance.
 for(const r of D.records.filter(r=>r.access?.groundReview&&allowed(r))){
  const xy=r.access.groundReview.observation,pos=[xy[1],xy[0]];if(!view.contains(pos))continue;
  const marker=L.marker(pos,{icon:L.divIcon({className:'marker-shell',iconSize:[38,28],iconAnchor:[19,14],html:`<span class="observation-marker" aria-hidden="true">◎<small>${esc(r.access.number)}</small></span>`}),title:r.name+'：街景觀察位置，非入口座標'});
  marker.on('click',()=>selectRecord(r.id)).bindTooltip(esc(r.name.replace('市民大道','').replace('停車場／','').replace('行人出入口（樓梯）',''))+' · 街景觀察點（非入口位置）',{permanent:r.id===state.selected,direction:'bottom',offset:[0,14]}).addTo(features);
 }
 const all=scopeRecords().filter(r=>!r.isIndex),missing=all.filter(r=>!r.geometry).length;
 $('visible-summary').textContent=`${state.segment==='all'?'研究範圍':state.segment} ${all.length} 筆資料${missing?` · ${missing} 筆未定位`:''}`;
 $('layer-count').textContent=state.layers.size;
 renderSelection();
}
function renderSelection(){
 selection.clearLayers();const r=records.get(state.selected);if(!r||!r.geometry)return;
 if(!allowed(r))return;
 if(r.geometry.type==='Point')L.marker([r.geometry.coordinates[1],r.geometry.coordinates[0]],{icon:markerIcon(r),zIndexOffset:1000,title:r.name}).on('click',()=>showDetail(r)).addTo(selection);
 else L.geoJSON(r.geometry,{interactive:false,style:{color:'#e8a22b',weight:5,fillOpacity:.12,dashArray:r.isIndex?'5 4':null}}).addTo(selection);
 const parent=records.get(r.parent);
 if(parent?.geometry?.type==='Point'&&r.geometry.type==='Point')L.polyline([[r.geometry.coordinates[1],r.geometry.coordinates[0]],[parent.geometry.coordinates[1],parent.geometry.coordinates[0]]],{color:'#c99442',weight:1.5,dashArray:'4 6',interactive:false}).bindTooltip('資料關聯示意，非通行路徑').addTo(selection);
}
function reveal(r){state.layers.add(r.category);if(r.historical)state.historical=true;else if(r.pending)state.pending=true;else state.confirmed=true;syncControls();}
function selectRecord(id,move=true){
 const r=records.get(id);if(!r)return;
 if(move){state.segment=r.segments.length===1?r.segments[0]:'all';updateSegmentInfo();drawCorridor();}
 state.selected=id;reveal(r);showDetail(r);closePanels();
 if(move){
  if(r.geometry){const pts=geometryPoints(r.geometry);const b=L.latLngBounds(pts);if(r.geometry.type==='Point')map.setView(b.getCenter(),Math.max(map.getZoom(),18),{animate:false});else fitBounds(b,true);
   if(innerWidth>=700&&r.geometry.type==='Point')map.panBy([(365+40)/2,0],{animate:false});
   if(innerWidth<700&&r.geometry.type==='Point')map.panBy([0,innerHeight*.14],{animate:false});
  }else if(r.access?.groundReview){const xy=r.access.groundReview.observation;map.setView([xy[1],xy[0]],18.5,{animate:false});if(innerWidth>=700)map.panBy([202,0],{animate:false});else map.panBy([0,innerHeight*.14],{animate:false});}else if(r.segments.length){const b=L.latLngBounds([]);r.segments.forEach(id=>b.extend(D.segments.find(s=>s.id===id).bounds));fitBounds(b,true);}
 }
 renderFeatures();saveHash();
}
function detailField(name,value){return value===null||value===undefined||value===''?'':`<dt>${esc(name)}</dt><dd>${esc(value)}</dd>`;}
function showDetail(r){
 $('detail').hidden=false;document.body.classList.add('detail-open');const c=cats.get(r.category),o=r.currentSource||r.original;
 $('detail-category').innerHTML=categoryIcon(c)+' '+esc(c.name);
 let body=`<h2>${esc(r.name)}</h2><div class="record-id">${esc(r.id)} · ${esc(r.segments.join(' / ')||'分段待核')}</div><div class="badges"><span class="badge ${r.historical?'historical':r.pending?'pending':''}">${statusName(r)}</span>${r.isIndex?'<span class="badge index">查找索引 · 不計為設施</span>':''}${r.category==='entrance'?'<span class="badge">出入口資料</span>':''}</div>`;
 if(r.verification){
  const v=r.verification;
  body+=`<section class="notice ${v.issues.length?'warning':''}"><strong>逐筆來源查核 · ${esc(v.checkedAt)}</strong><p>${esc(v.summary)}</p><p>${esc(v.position)}</p>${v.issues.map(x=>`<p><strong>待確認：</strong>${esc(x)}</p>`).join('')}<details><summary>核對欄位與來源值（${v.checks.length}項）</summary><dl>${v.checks.map(x=>detailField(x.field,(x.result==='match'?'已核對：':'差異：')+(typeof x.source==='object'?JSON.stringify(x.source):String(x.source)))).join('')}</dl><p>${esc(v.method)}<br>來源日期：${esc(v.sourceDate)}</p>${v.sources.map(url=>`<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">查核依據 ↗</a>`).join('')}</details></section>`;
 }
 if(r.review){
  body+=`<section class="notice"><strong>影像查核 · ${esc(r.review.checkedAt)}</strong><p>${esc(r.review.summary)}</p><p>${esc(r.review.limitation)}</p>${r.review.references.map(ref=>`<a class="source-link" href="${esc(ref.url)}" target="_blank" rel="noopener noreferrer">${esc(ref.label)} ↗</a>`).join('')}</section>`;
 }
 if(r.access){
  const a=r.access,g=a.groundReview;
  body+=`<section class="notice"><strong>停車場行人設施 · ${esc(a.number)} 號</strong><p>${a.groundDocumented?'官方地面層圖載明樓梯口。':'文件僅載明樓梯，尚未確認地面連通。'} 不等同已確認的過街動線。</p><p>文件第 ${a.document.page} 頁 · 查核 ${esc(a.checkedAt)}</p>${g?`<p>${esc(g.summary)}</p><a class="source-link" href="${esc(g.url)}" target="_blank" rel="noopener noreferrer">查看 ${esc(g.imageDate)} 地面街景 ↗</a><p>◎ 是街景相機觀察位置，入口座標尚未核實。</p>`:''}<p>${esc(a.limitations)}</p></section>`;
  if(r.table==='歷史圖說設備')body+=`<details><summary>原始歷史紀錄（保留同一設施編號）</summary><p>${esc(r.original['名稱'])} · ${esc(r.original['確認程度'])}</p><a href="${esc(r.original['來源連結'])}" target="_blank" rel="noopener">舊來源 ↗</a></details>`;
 }
 const audit=D.accessAudit.find(a=>a.parent===r.id);
 if(audit)body+=`<section class="notice"><strong>行人出入口 · 官方圖說</strong><p>${audit.documentedGroundCount===null?'尚無完整地面入口清冊':`已採用 ${audit.documentedGroundCount} 個文件載明地面樓梯口`}；${audit.groundImageReviewed} 個另有日期街景；${audit.locatedCount} 個有入口地理座標。</p><p>${esc(audit.note)}</p></section>`;
 if(r.scopeNote)body+=`<div class="notice">${esc(r.scopeNote)}</div>`;
 if(!r.geometry)body+='<div class="notice warning">尚無已核實的入口／設施座標。地圖僅顯示所屬分段或另標示街景觀察點，不將場站中心或相機位置當作入口位置。</div>';
 if(r.historical)body+=`<div class="notice warning">歷史參考，不計現況。${esc(o['來源日期'])}</div>`;
 if(r.table==='車輛入口')body+='<div class="notice">登錄入口位置。來源未確認出口、雙向通行或進出方向；不代表完整出入口清冊。</div>';
 if(r.category==='crossing')body+='<div class="notice">自行車通行性：未確認。行穿線、陸橋、地下通道或樓梯資料，不等同已確認的自行車穿越路徑。</div>';
 if(r.isIndex)body+=`<div class="notice">包含 ${r.members.length} 個候選圖形。此為空間分群索引，不是 ${r.members.length} 處已確認過街地點。</div>`;
 if(r.verification?.issues.length&&r.currentSource)body+=`<details><summary>保留原始登錄內容</summary><p>${esc(r.original['地址或鄰近路口'])}</p><p>${esc(r.original['確認程度'])}</p></details>`;
 body+='<dl>'+detailField('採用類別',o['類別'])+detailField('位置',o['地址或鄰近路口'])+detailField('範圍與歸屬',o['範圍'])+['場地數量','場地規格','附屬設施','開放時間（登錄）','場內廁所','使用性質'].map(k=>detailField(k,o[k])).join('')+detailField('確認程度',o['確認程度'])+detailField('座標依據',o['座標依據'])+detailField('座標（WGS84）',o['經度']!=null?`${o['緯度']}, ${o['經度']}`:null)+detailField('地上／地下',o['地上地下'])+detailField('管理屬性',o['公私屬性'])+detailField('小型車格／機車格',o['小型車格']!=null?`${o['小型車格']} / ${o['機車格']??'未載'}`:null)+detailField('來源列示數值（非定位數量）',o['來源數值'])+detailField('原始標線類別',o['原始標線類別'])+detailField('南北連接',o['南北連接'])+detailField('待確認事項',o['待確認事項'])+detailField('來源日期',o['來源日期'])+detailField('來源資料查核日期',o['查核日期'])+'</dl>';
 const relations=[...new Set([r.parent,r.group,...r.members,...(r.access?.related||[]),...D.records.filter(x=>x.access?.related?.includes(r.id)).map(x=>x.id),...D.records.filter(x=>x.parent===r.id).map(x=>x.id)].filter(id=>records.has(id)))];
 if(relations.length){body+='<h3>關聯資料</h3>';for(const id of relations){const x=records.get(id);body+=`<button class="relation-button" data-record="${esc(id)}">${esc(x.name)}${!x.geometry?' · 未定位':''}</button>`;}}
 const urls=(o['來源連結']||'').match(/https?:\/\/[^\s；、]+/g)||[];
 urls.forEach((url,i)=>body+=`<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">查看公開來源${urls.length>1?' '+(i+1):''} ↗</a>`);
 $('detail-content').innerHTML=body;$('detail').scrollTop=0;
 $('detail-content').querySelectorAll('[data-record]').forEach(el=>el.onclick=()=>selectRecord(el.dataset.record));
}
function closeDetail(){state.selected=null;$('detail').hidden=true;document.body.classList.remove('detail-open');renderFeatures();saveHash();}
function closePanels(){for(const id of ['layers-panel','results-panel','about-panel'])$(id).hidden=true;$('layers-button').setAttribute('aria-expanded','false');$('list-button').setAttribute('aria-expanded','false');}
function openPanel(id){const was=$(id).hidden;closePanels();$(id).hidden=!was;if(id==='layers-panel')$('layers-button').setAttribute('aria-expanded',String(was));if(id==='results-panel')$('list-button').setAttribute('aria-expanded',String(was));}
function renderResults(){
 const query=$('search').value.trim().toLowerCase();const all=resultMode==='audit'?D.records:resultMode==='access'?D.records.filter(r=>r.access):resultMode==='search'&&query?D.records.filter(r=>[r.name,r.original['名稱'],r.id,r.original['地址或鄰近路口'],r.subtype,r.segments.join(' '),r.original['範圍']].some(x=>String(x??'').toLowerCase().includes(query))):scopeRecords();
 // Missing coordinates remain immediately discoverable; index rows are explicitly separate.
 const ordered=[...all].sort((a,b)=>(resultMode==='audit'?Number(!!b.verification?.issues.length)-Number(!!a.verification?.issues.length):0)||Number(a.isIndex)-Number(b.isIndex)||Number(!!a.geometry)-Number(!!b.geometry)||a.id.localeCompare(b.id));
 const indexes=all.filter(r=>r.isIndex).length, missing=all.filter(r=>!r.geometry).length;
 $('results-title').textContent=resultMode==='audit'?'逐筆來源查核':resultMode==='access'?'停車場行人出入口核對清單':resultMode==='search'&&query?'搜尋結果':'資料清單';
 $('results-summary').textContent=`${all.length-indexes} 筆資料${indexes?`＋${indexes} 個查找索引`:''} · ${missing} 筆未定位。${resultMode==='search'&&query?'搜尋涵蓋隱藏圖層與歷史資料。':'依目前分段、圖層與狀態篩選。'}`;
 if(resultMode==='access')$('results-summary').textContent=`${D.meta.documentedGroundAccessCount} 個文件載明地面樓梯口＋${D.meta.pedestrianAccessCount-D.meta.documentedGroundAccessCount} 座地面連通待核樓梯；${D.meta.accessImageReviewCount} 個另有日期街景，${D.accessAudit.reduce((n,a)=>n+a.locatedCount,0)} 個已核實入口座標。採用官方圖說，入口精確定位另列缺口。包含全部相關紀錄，不受目前圖層與分段篩選影響。`;
 if(resultMode==='audit')$('results-summary').textContent=`${D.audit.recordCount} 筆已逐筆對照來源（含 ${D.meta.indexCount} 個派生索引）；${D.audit.issueCount} 筆有特定欄位問題，優先列出。官方來源可採用，缺座標不推算位置。`;
 $('results').innerHTML=ordered.slice(0,resultLimit).map(r=>`<button class="result" data-record="${esc(r.id)}">${categoryIcon(cats.get(r.category))}<strong>${esc(r.name)}</strong><small>${esc(r.segments.join('/'))} · ${esc(cats.get(r.category).name)} · ${statusName(r)}${r.isIndex?' · 查找索引':''}</small><small class="${r.geometry?'':'no-coordinate'}">${esc(r.id)}${r.geometry?'':' · 尚無可定位座標'}</small></button>`).join('')||'<div class="empty">沒有符合的資料。可調整分類或狀態，或輸入其他名稱查詢。</div>';
 if(ordered.length>resultLimit)$('results').insertAdjacentHTML('beforeend',`<button id="more-results">顯示更多（尚有 ${ordered.length-resultLimit} 筆）</button>`);
 $('results').querySelectorAll('[data-record]').forEach(el=>el.onclick=()=>selectRecord(el.dataset.record));
 if($('more-results'))$('more-results').onclick=()=>{resultLimit+=60;renderResults();};
}
function syncControls(){
 document.querySelectorAll('[data-layer]').forEach(input=>input.checked=state.layers.has(input.dataset.layer));
 for(const key of ['confirmed','pending','historical'])$('status-'+key).checked=state[key];
 $('road-labels').checked=state.labels;$('segment').value=state.segment;updateFade();$('layer-count').textContent=state.layers.size;
}
function changed(){
 if(state.selected&&!allowed(records.get(state.selected)))closeDetail();
 renderFeatures();if(!$('results-panel').hidden)renderResults();saveHash();
}
function saveHash(){
 if(restoring||!map._loaded)return;const center=map.getCenter();
 const p=new URLSearchParams({lat:center.lat.toFixed(6),lng:center.lng.toFixed(6),z:String(map.getZoom()),seg:state.segment,layers:[...state.layers].sort().join(','),confirmed:+state.confirmed,pending:+state.pending,historical:+state.historical,base:state.base,fade:state.fade,labels:+state.labels});
 if(state.selected)p.set('id',state.selected);
 try{history.replaceState(null,'','#'+p.toString());}catch{/* Some file browsers deny replaceState; the map still works. */}
}
function fillAbout(){
 const sourceGroups=new Map();for(const r of D.records){for(const url of (r.currentSource||r.original)['來源連結'].split('；')){if(!sourceGroups.has(url))sourceGroups.set(url,new Set());sourceGroups.get(url).add(r.table);}}
 const accessSummary=`<h3>停車場行人出入口查核</h3><p>${esc(D.accessScope)}</p>${D.accessAudit.map(a=>`<p><strong>${esc(a.name)}</strong><br>${esc(a.note)}<br>建檔 ${a.recordIds.length} 筆 · 街景 ${a.groundImageReviewed} 筆 · 已核實座標 ${a.locatedCount} 筆</p>`).join('')}`;
 $('about-content').innerHTML=`<p>研究範圍：西至中山北路、東至光復南路（S2–S4）。這是範圍內公開資料的查閱工具。以來源、位置與確認程度交叉閱讀；資料筆數不代表完整的現況設施總數。範圍內 ${D.audit.recordCount} 筆紀錄均有逐筆來源查核，官方資料與圖說直接支持的內容可採用；${D.audit.issueCount} 筆另有特定欄位問題。</p><div class="about-links"><a href="${PUBLIC_URL.replace('visionbase-usc.github.io/','github.com/visionbase-usc/')}" target="_blank" rel="noopener">GitHub</a><a href="https://github.com/visionbase-usc/civic-boulevard-viewer/archive/refs/heads/main.zip">下載整包</a></div><h3>逐筆查核</h3><button id="audit-button" class="relation-button">查看全部 ${D.audit.recordCount} 筆查核結果</button><a class="source-link" href="./data/record-audit.csv" download>下載逐筆查核表 CSV ↧</a><p>每筆列出核對欄位、來源值、來源日期與問題。${D.meta.indexCount} 個分群為派生查找索引，不視為官方路口。</p><h3>版本與時間</h3><p>v${esc(D.version)} · 資料查核 ${esc(D.date)}<br>底圖影像拍攝年代未核。影像及資料並非即時現況。</p><h3>如何閱讀</h3><ul><li>實心：公開資料已列；空心虛線：待確認；灰色：歷史。</li><li>聚合圓圈中的數字為資料筆數。放大或點擊即可展開。</li><li>青綠寬帶依高架線形繪製，細線為平面道路；不是正式路界。</li><li>停車場代表點不是基地邊界。金色虛線僅表示資料關聯，不是通行動線。</li><li>${D.records.filter(r=>r.table==='行穿線圖形').length} 個行穿線圖形、${D.meta.indexCount} 個候選分群分開呈現，分群不計為實際設施。</li><li>未定位資料可從清單或搜尋開啟。自行車通行性尚待個別確認。</li><li>保留 S2–S4 原分段編號；邊界設施保留關聯資料，分段起訖仍有待核部分。</li></ul><h3>底圖與線形</h3><p><a href="https://maps.nlsc.gov.tw/S09SOA/pro/Wmts_ajax_main.jsp" target="_blank" rel="noopener">國土測繪中心 WMTS</a>：PHOTO2／EMAP／EMAP2。底圖需要網路，不隨下載包離線封裝。瀏覽範圍限制於中山北路至光復南路路廊周邊，只載入目前視窗所需圖磚，拖曳停止後才更新；不預載全市。</p><p>道路線形 © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>，ODbL；快照 ${esc(D.meta.roadsDate)}。</p>${accessSummary}<h3>盤點來源</h3>${[...sourceGroups].map(([url,tables])=>`<div class="source-item"><a href="${esc(url)}" target="_blank" rel="noopener">${esc([...tables].join('／'))} ↗</a></div>`).join('')}`;
 $('audit-button').onclick=()=>{resultMode='audit';resultLimit=60;closePanels();$('results-panel').hidden=false;renderResults();};
}
$('version').textContent=`公開圖資 · ${D.date} · v${D.version}`;
D.segments.forEach(s=>{const op=document.createElement('option');op.value=s.id;op.textContent=`${s.id} · ${s.west}—${s.east}`;$('segment').append(op);});
$('layer-options').innerHTML=D.categories.map(c=>`<label class="layer-option"><input type="checkbox" data-layer="${c.id}" ${state.layers.has(c.id)?'checked':''}>${categoryIcon(c)}<span>${c.name}</span><span class="count" title="包含歷史與未定位資料，不含查找索引">${D.meta.categoryCounts[c.id]}</span></label>`).join('');
$('layer-options').querySelectorAll('input').forEach(input=>input.onchange=()=>{input.checked?state.layers.add(input.dataset.layer):state.layers.delete(input.dataset.layer);changed();});
for(const key of ['confirmed','pending','historical'])$('status-'+key).onchange=()=>{state[key]=$('status-'+key).checked;changed();};
$('all-layers').onclick=()=>{state.layers=new Set(D.categories.map(c=>c.id));syncControls();changed();};
$('no-layers').onclick=()=>{state.layers.clear();syncControls();changed();};
$('layers-button').onclick=()=>openPanel('layers-panel');
function openList(){resultMode='list';resultLimit=60;$('search').value='';renderResults();openPanel('results-panel');}
$('list-button').onclick=openList;$('visible-summary').onclick=openList;
$('access-button').onclick=()=>{resultMode='access';resultLimit=60;$('search').value='';renderResults();closePanels();$('results-panel').hidden=false;};
$('about-button').onclick=()=>openPanel('about-panel');
$('search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{resultMode='search';resultLimit=60;renderResults();closePanels();$('results-panel').hidden=false;},160);});
$('search').addEventListener('focus',()=>{if($('search').value){renderResults();closePanels();$('results-panel').hidden=false;}});
$('segment').onchange=()=>setSegment($('segment').value);
$('prev-segment').onclick=()=>setSegment(D.segments[state.segment==='all'?D.segments.length-1:Math.max(0,D.segments.findIndex(s=>s.id===state.segment)-1)].id);
$('next-segment').onclick=()=>setSegment(D.segments[state.segment==='all'?0:Math.min(D.segments.length-1,D.segments.findIndex(s=>s.id===state.segment)+1)].id);
$('full-extent').onclick=()=>{fitAll();drawCorridor();drawRouteNames();renderFeatures();};
$('base-photo').onclick=()=>setBase('photo');$('base-map').onclick=()=>setBase('map');
$('fade').oninput=()=>{state.fade=Number($('fade').value);updateFade();saveHash();};
$('road-labels').onchange=()=>{state.labels=$('road-labels').checked;updateLabels();saveHash();};
$('close-detail').onclick=closeDetail;
$('share-button').onclick=async()=>{saveHash();const url=(location.protocol==='file:'?PUBLIC_URL:location.href.split('#')[0])+location.hash;try{await navigator.clipboard.writeText(url);toast('已複製目前檢視網址');}catch{const input=document.createElement('textarea');input.value=url;input.style.position='fixed';input.style.top='-1000px';document.body.append(input);input.select();const ok=document.execCommand('copy');input.remove();toast(ok?'已複製目前檢視網址':'請從網址列複製目前檢視網址');}};
for(const button of document.querySelectorAll('[data-close]'))button.onclick=closePanels;
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closePanels();closeDetail();$('search').blur();}});
map.on('moveend',()=>{renderFeatures();drawRouteNames();saveHash();});map.on('zoomend',drawCorridor);
window.addEventListener('online',()=>setBase(state.base));window.addEventListener('offline',updateBaseMessage);
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{map.invalidateSize();renderFeatures();drawRouteNames();},150);});
window.addEventListener('hashchange',()=>{restoring=true;camera=null;readHash();syncControls();setBase(state.base);if(camera)map.setView([camera.lat,camera.lng],camera.z,{animate:false});else setSegment(state.segment,true);updateSegmentInfo();if(state.selected)selectRecord(state.selected,false);else closeDetail();restoring=false;drawCorridor();renderFeatures();saveHash();});
restoring=true;syncControls();fillAbout();setBase(state.base);
if(camera)map.setView([camera.lat,camera.lng],camera.z,{animate:false});else if(state.segment!=='all')setSegment(state.segment,true);else fitBounds(fullBounds);
updateSegmentInfo();drawCorridor();drawRouteNames();renderFeatures();if(state.selected)selectRecord(state.selected,false);restoring=false;saveHash();
})();
