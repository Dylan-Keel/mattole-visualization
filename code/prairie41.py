import numpy as np, cv2, geopandas as gpd, zipfile
from shapely.geometry import shape, box
from shapely.ops import unary_union
from rasterio import features
from rasterio.transform import from_origin
b=(392000,4456700,394400,4459400); T=from_origin(b[0],b[3],2,2)
o=np.load('o41_63_2m.npy'); g=cv2.GaussianBlur(o,(0,0),3)
m=(g>136).astype(np.uint8)
m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))
m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
polys=[shape(s).buffer(0) for s,v in features.shapes(m,mask=m.astype(bool),transform=T)]
polys=[p.simplify(4).buffer(6).buffer(-6) for p in polys if p.area>=1500]   # >= 0.15 ha
polys=[p for p in polys if not p.is_empty and p.area>=1500]
ws=gpd.read_file('watershed.geojson').geometry.iloc[0].buffer(0); parcel=gpd.read_file('parcel.geojson').to_crs(26910).geometry.iloc[0]
rows=[]
for p in polys:
    for q in getattr(p,'geoms',[p]):
        if q.area<1500: continue
        rows.append(dict(geometry=q,acres=q.area/4046.86,acres_in_catchment=q.intersection(ws).area/4046.86,acres_on_parcel=q.intersection(parcel).area/4046.86))
G=gpd.GeoDataFrame(rows,crs=26910).sort_values('acres',ascending=False).reset_index(drop=True)
G['name']=[f'Open ground 1941 #{i+1} ({a:.1f} ac)' for i,a in enumerate(G.acres)]
print(len(G),'polys; total ac in view',G.acres.sum().round(1),'in catchment',G.acres_in_catchment.sum().round(1),'of',round(ws.area/4046.86,1),'on parcel',G.acres_on_parcel.sum().round(1),'of',round(parcel.area/4046.86,1))
G.to_file('prairie_1941.geojson',driver='GeoJSON')
W=G.to_crs(4326); wsll=gpd.GeoSeries([ws],crs=26910).to_crs(4326).iloc[0]; pll=gpd.GeoSeries([parcel],crs=26910).to_crs(4326).iloc[0]
def ring(r): return ' '.join(f'{x:.7f},{y:.7f},0' for x,y in r.coords)
def poly(p): 
    s='<Polygon><outerBoundaryIs><LinearRing><coordinates>'+ring(p.exterior)+'</coordinates></LinearRing></outerBoundaryIs>'
    for i in p.interiors: s+='<innerBoundaryIs><LinearRing><coordinates>'+ring(i)+'</coordinates></LinearRing></innerBoundaryIs>'
    return s+'</Polygon>'
k=['<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Cooskie Ridge open ground, October 1941</name>',
 '<description>Open ground (prairie and other unforested cover) mapped from USDA AAA frame CVL-1B-63, flown October 29, 1941. Source was a low-resolution preview scan (about 13 m per pixel), orthorectified to the 10 m 3DEP elevation model. Provisional: edges are good to roughly 15 to 25 m and openings under 0.15 ha are not mapped.</description>',
 '<Style id="open"><LineStyle><color>ff00d2ff</color><width>2</width></LineStyle><PolyStyle><color>5500d2ff</color></PolyStyle></Style>',
 '<Style id="ws"><LineStyle><color>ffffd45f</color><width>3</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>',
 '<Style id="pc"><LineStyle><color>ff3fd2ff</color><width>3</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>',
 '<Folder><name>Open ground 1941</name>']
for _,r in W.iterrows():
    k.append(f'<Placemark><name>{r["name"]}</name><description>{r.acres:.2f} ac total; {r.acres_in_catchment:.2f} ac inside the catchment; {r.acres_on_parcel:.2f} ac on APN 104-122-019</description><styleUrl>#open</styleUrl>{poly(r.geometry)}</Placemark>')
k.append('</Folder><Folder><name>Boundaries</name>')
for nm,geom,st in (('Tributary catchment (494 ac, from 10 m DEM)',wsll,'ws'),('Parcel APN 104-122-019 (county GIS)',pll,'pc')):
    for q in getattr(geom,'geoms',[geom]):
        if q.area>1e-9: k.append(f'<Placemark><name>{nm}</name><styleUrl>#{st}</styleUrl>{poly(q)}</Placemark>')
k.append('</Folder></Document></kml>')
open('doc.kml','w').write('\n'.join(k))
with zipfile.ZipFile('Cooskie_open_ground_1941.kmz','w',zipfile.ZIP_DEFLATED) as z: z.write('doc.kml','doc.kml')
# check overlay
c=cv2.cvtColor(o,cv2.COLOR_GRAY2BGR)
for geom,col,w in [(q,(0,210,255),2) for q in G.geometry]+[(ws,(255,200,0),1),(parcel,(0,0,255),1)]:
    for q in getattr(geom,'geoms',[geom]):
        cv2.polylines(c,[np.array([[(x-b[0])/2,(b[3]-y)/2] for x,y in q.exterior.coords],np.int32)],True,col,w)
cv2.imwrite('prairie41_chk.jpg',c)
