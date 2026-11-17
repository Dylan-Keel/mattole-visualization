import numpy as np, cv2, geopandas as gpd, zipfile, json
from shapely.geometry import shape, LineString
from rasterio import features
from rasterio.transform import from_origin
b=(392000,4456700,394400,4459400); T=from_origin(b[0],b[3],1,1)
m=(cv2.imread('p41_mask.png',0)>0).astype(np.uint8)
polys=[shape(s).buffer(0) for s,v in features.shapes(m,mask=m.astype(bool),transform=T)]
polys=[p.simplify(2).buffer(3).buffer(-3) for p in polys if p.area>=1000]
ws=gpd.read_file('watershed.geojson').geometry.iloc[0].buffer(0); parcel=gpd.read_file('parcel.geojson').to_crs(26910).geometry.iloc[0]
rows=[]
for p in polys:
    for q in getattr(p,'geoms',[p]):
        if q.area>=1000: rows.append(dict(geometry=q,acres=q.area/4046.86,in_c=q.intersection(ws).area/4046.86,on_p=q.intersection(parcel).area/4046.86))
G=gpd.GeoDataFrame(rows,crs=26910).sort_values('acres',ascending=False).reset_index(drop=True)
G['name']=[f'Open ground 1941 #{i+1} ({a:.1f} ac)' for i,a in enumerate(G.acres)]
print(len(G),'polygons; in view %.1f ac; in catchment %.1f of %.1f ac; on parcel %.1f of %.1f ac'%(G.acres.sum(),G.in_c.sum(),ws.area/4046.86,G.on_p.sum(),parcel.area/4046.86))
G.to_file('prairie_1941_full.geojson',driver='GeoJSON')
SL=json.load(open('streams.json'))
def sm(l,k=4):
    a=np.array(l,float); o=a.copy()
    for i in range(len(a)): o[i]=a[max(0,i-k):i+k+1].mean(0)
    o[0]=a[0]; o[-1]=a[-1]; return LineString(o)
ll=lambda g:gpd.GeoSeries([g],crs=26910).to_crs(4326).iloc[0]
W=G.to_crs(4326)
ring=lambda r:' '.join(f'{x:.7f},{y:.7f},0' for x,y,*_ in r.coords)
def poly(p):
    s='<Polygon><outerBoundaryIs><LinearRing><coordinates>'+ring(p.exterior)+'</coordinates></LinearRing></outerBoundaryIs>'
    for i in p.interiors: s+='<innerBoundaryIs><LinearRing><coordinates>'+ring(i)+'</coordinates></LinearRing></innerBoundaryIs>'
    return s+'</Polygon>'
k=['<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Wild Turkey Creek open ground, October 1941</name>',
'<description>Open ground (prairie and other unforested or sparsely treed cover) mapped from USDA frames CVL-1B-63 and CVL-1B-62, flown October 29, 1941. Full-resolution scans (about 0.8 m per pixel), orthorectified to the 10 m 3DEP elevation model with a fit of about 7 m. Classified by brightness and texture; openings under 0.25 acre are not mapped. Some polygons in mid-slope forest may be bright hardwood canopy, not grass.</description>',
'<Style id="open"><LineStyle><color>ff00d2ff</color><width>2</width></LineStyle><PolyStyle><color>5500d2ff</color></PolyStyle></Style>',
'<Style id="ws"><LineStyle><color>ffffd45f</color><width>3</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>',
'<Style id="pc"><LineStyle><color>ff3fd2ff</color><width>3</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>',
'<Style id="ck"><LineStyle><color>ffc8e89f</color><width>3</width></LineStyle></Style>','<Folder><name>Open ground 1941</name>']
for _,r in W.iterrows():
    k.append(f'<Placemark><name>{r["name"]}</name><description>{r.acres:.2f} ac total; {r.in_c:.2f} ac inside the catchment; {r.on_p:.2f} ac on APN 104-122-019</description><styleUrl>#open</styleUrl>{poly(r.geometry)}</Placemark>')
k.append('</Folder><Folder><name>Creeks</name>')
for nm,key in (('Wild Turkey Creek','main'),('Rana Creek','trib0')):
    k.append(f'<Placemark><name>{nm}</name><description>Channel line derived from the 10 m elevation model. Name supplied by the landowner.</description><styleUrl>#ck</styleUrl><LineString><coordinates>{ring(ll(sm(SL[key])))}</coordinates></LineString></Placemark>')
k.append('</Folder><Folder><name>Boundaries</name>')
for nm,geom,st in (('Wild Turkey Creek catchment (494 ac, from 10 m DEM)',ll(ws),'ws'),('Parcel APN 104-122-019 (county GIS)',ll(parcel),'pc')):
    for q in getattr(geom,'geoms',[geom]):
        if q.area>1e-9: k.append(f'<Placemark><name>{nm}</name><styleUrl>#{st}</styleUrl>{poly(q)}</Placemark>')
k.append('</Folder></Document></kml>')
open('doc.kml','w').write('\n'.join(k))
with zipfile.ZipFile('Wild_Turkey_Creek_open_ground_1941.kmz','w',zipfile.ZIP_DEFLATED) as z: z.write('doc.kml','doc.kml')
import xml.dom.minidom as md; md.parse('doc.kml'); print('kml ok')
