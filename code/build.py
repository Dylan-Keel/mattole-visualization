import rasterio, numpy as np, json, geopandas as gpd, os
from PIL import Image
from shapely.geometry import box
F=[ # id, file, label, date text, source, native res, note
 ('1941','master/full_1941.tif','1941','October 29, 1941','USDA flight CVL, 1:20,000, black and white. Full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: CVL-1B-63, CVL-1B-62','about 0.8 m',''),
 ('1948','master/full_1948.tif','1948','June 22, 1948','California Division of Forestry flight CDF2, 1:20,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: CDF2-13-141, CDF2-13-139, CDF2-13-152, CDF2-13-151','about 0.8 m',''),
 ('1954','master/full_1954.tif','1954','July 22, 1954','USDA flight CVL, 1:20,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: CVL-8N-100, CVL-8N-101, CVL-8N-99','about 0.8 m',''),
 ('1959','master/full_1959.tif','1959','May 10 and May 30, 1959','Humboldt County flight HS, about 1:12,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: HS04-11, HS04-10, HS3-10, HS3-09, HS3-08','about 0.5 m','Two flight lines flown 20 days apart'),
 ('1963','master/full_1963.tif','1963','August 14 and 15, 1963','Humboldt County flight HC-S, about 1:12,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: HC-S-2-3-8-11, HC-S-2-3-9A-11, HC-S-2-3-8-10, HC-S-2-3-8-12, HC-S-2-3-9A-12, HC-S-2-3-9A-10','about 0.5 m',''),
 ('1966','master/full_1966.tif','1966','September 2, 1966','Humboldt County flight HC-66, about 1:12,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: HC-66-9A-10, HC-66-8A-10, HC-66-9A-09, HC-66-8A-11, HC-66-8A-09','about 0.5 m','Northeast corner of the watershed view is not covered'),
 ('1970','master/full_1970.tif','1970','July 22 and September 9, 1970','Humboldt County flight CH-70, about 1:12,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: CH-70-8A-12, CH-70-9A-11, CH-70-9A-10, CH-70-9A-12, CH-70-8A-14, CH-70-8A-10','about 0.5 m','West and east lines flown seven weeks apart'),
 ('1974','master/full_1974.tif','1974','1974','Humboldt County flight HC74, about 1:12,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: HC74 2 9-11, HC74 2 9-12, HC74 2 9-13','about 0.5 m','East side only. I could not place the western flight line'),
 ('1981','master/full_1981.tif','1981','June 15, 1981','California Department of Forestry flight CDF ALL-EU, about 1:24,000, black and white. Mosaic of full-resolution scans (Cal Poly Humboldt), orthorectified here. Frames: CDF ALL-EU 4-6','about 1 m',''),
 ('1993','master/napp1993.tif','1993','June 12, 1993','USGS NAPP frame 6247-163, black and white, 1:40,000 (UCSB Library scan), orthorectified here','about 1.7 m',''),
 ('1998','master/napp1998.tif','1998','August 27, 1998','USGS NAPP frame 10488-21, black and white, 1:40,000 (UCSB Library scan), orthorectified here','about 1.7 m','West edge of the frame falls inside the watershed view'),
 ('2005','master/county_naip_2005.tif','2005','Summer 2005','USDA NAIP natural color (Humboldt County image service)','1 m',''),
 ('2009','master/county_naip_2009.tif','2009','Summer 2009','USDA NAIP natural color (Humboldt County image service)','1 m',''),
 ('2010','master/county_naip_2010.tif','2010','Summer 2010','USDA NAIP natural color (Humboldt County image service)','1 m',''),
 ('2012','master/naip_2012.tif','2012','June 10, 2012','USDA NAIP natural color','1 m',''),
 ('2014','master/naip_2014.tif','2014','June 7, 2014','USDA NAIP natural color','1 m',''),
 ('2016','master/naip_2016.tif','2016','June 19, 2016','USDA NAIP natural color','0.6 m',''),
 ('2018','master/naip_2018.tif','2018','September 20, 2018','USDA NAIP natural color','0.6 m',''),
 ('2020','master/naip_2020.tif','2020','July 18, 2020','USDA NAIP natural color','0.6 m',''),
 ('2022','master/naip_2022.tif','2022','July 10, 2022','USDA NAIP natural color','0.6 m',''),
 ('2024','master/naip_2024.tif','2024','May 31, 2024','USDA NAIP natural color','0.6 m',''),
 ('2025','master/esri_2025.tif','2025','July 19, 2025','Vantor WorldView-3 satellite (Esri World Imagery)','0.31 m',''),
]
MX0,MY1=392000,4459400
V={'w':dict(b=(392000,4456700,394400,4459400),res=1.0,name='Watershed'),
   'p':dict(b=(392580,4457500,393700,4459040),res=0.5,name='Parcel')}
tot=0
for fid,path,*_ in F:
    if os.path.exists(f'site/frames/w_{fid}.jpg'):
        for k,v in V.items():
            x0,y0,x1,y1=v['b']; v['size']=(int((x1-x0)/v['res']),int((y1-y0)/v['res']))
        continue
    with rasterio.open(path) as s:
        a=s.read(); mres=s.transform.a
    a=a[:3] if a.shape[0]>=3 else np.repeat(a[:1],3,0)
    im=Image.fromarray(np.moveaxis(a,0,-1))
    if im.size!=(4800,5400): im=im.resize((4800,5400),Image.BICUBIC)
    for k,v in V.items():
        x0,y0,x1,y1=v['b']
        c=im.crop((int((x0-MX0)/0.5),int((MY1-y1)/0.5),int((x1-MX0)/0.5),int((MY1-y0)/0.5)))
        W,H=int((x1-x0)/v['res']),int((y1-y0)/v['res'])
        full=c.resize((W,H),Image.LANCZOS) if c.size!=(W,H) else c
        full.save(f'site/frames/{k}_{fid}.jpg',quality=84,optimize=True,progressive=True)
        full.resize((W//2,H//2),Image.LANCZOS).save(f'site/frames/{k}s_{fid}.jpg',quality=80,optimize=True,progressive=True)
        v['size']=(W,H)
for f in os.listdir('site/frames'): tot+=os.path.getsize('site/frames/'+f)
print('total MB',tot/1e6)
# overlays in pixel coords of each view
parcel=gpd.read_file('parcel.geojson').to_crs(26910).geometry.iloc[0]
ws=gpd.read_file('watershed.geojson').geometry.iloc[0].simplify(8)
nhd=gpd.read_file('nhd.geojson').to_crs(26910)
ov={}
for k,v in V.items():
    x0,y0,x1,y1=v['b']; r=v['res']; bb=box(x0,y0,x1,y1)
    def path(g):
        out=[]
        geoms=getattr(g,'geoms',[g])
        for gg in geoms:
            cs=gg.exterior.coords if gg.geom_type=='Polygon' else gg.coords
            out.append('M'+' L'.join(f'{(x-x0)/r:.1f} {(y1-y)/r:.1f}' for x,y,*_ in cs)+('Z' if gg.geom_type=='Polygon' else ''))
        return ' '.join(out)
    wsb=ws.buffer(0).intersection(bb); st=[g.intersection(wsb) for g in nhd.geometry if g.intersects(wsb)]
    sp=' '.join(path(g) for g in st if not g.is_empty and g.geom_type in('LineString','MultiLineString'))
    SL=json.load(open('streams.json'))
    def smooth(l,k=4):
        a=np.array(l,float); o=a.copy()
        for i in range(len(a)): o[i]=a[max(0,i-k):i+k+1].mean(0)
        o[0]=a[0]; o[-1]=a[-1]; return [tuple(p) for p in o]
    SL={n:smooth(l) for n,l in SL.items()}
    def lpath(l): return 'M'+' L'.join(f'{(x-x0)/r:.1f} {(y1-y)/r:.1f}' for x,y in l)
    def lab(l,frac):
        i=int(len(l)*frac); (xa,ya),(xb,yb)=l[max(i-6,0)],l[min(i+6,len(l)-1)]
        import math; ang=math.degrees(math.atan2(-(yb-ya),(xb-xa)))
        if ang>90: ang-=180
        if ang<-90: ang+=180
        return [round((l[i][0]-x0)/r,1),round((y1-l[i][1])/r,1),round(ang,1)]
    creeks=[dict(d=lpath(SL['main'])),dict(d=lpath(SL['trib0']))]
    FV=[f for f in json.load(open('fires_view.json'))[k] if f['share']>=0.005]
    wsc=ws.intersection(bb); wb=wsc.bounds; cx=ws.centroid.x if k=='w' else (x0+x1)/2
    shedlabel=[round((min(max(cx,x0+400*r),x1-400*r)-x0)/r,1), round((y1-(wb[3]-0.07*(wb[3]-wb[1])))/r,1)]
    ov[k]=dict(shedlabel=shedlabel,creeks=creeks,fires=FV,name=v['name'],w=v['size'][0],h=v['size'][1],res=r,bounds=v['b'],parcel=path(parcel),watershed=path(ws),streams=sp)
import r3d, shutil
gX,gY,gD=r3d.ground_map()
e3=box(*r3d.E3)
fires3=[]
fg=gpd.read_file('fires.geojson').set_crs(26910,allow_override=True)
import datetime
for _,f in fg.iterrows():
    geom=f.geometry.buffer(0)
    if geom.intersection(e3).area<20000: continue
    d=r3d.path3d(geom.boundary.intersection(e3),gD)
    if len(d)<40: continue
    dt=(datetime.datetime(1970,1,1)+datetime.timedelta(milliseconds=float(f.ALARM_DATE))).strftime('%B %-d, %Y')
    fires3.append(dict(year=int(f.YEAR_),name=f.FIRE_NAME.title(),date=dt,acres=round(float(f.GIS_ACRES)),d=d))
fires3.sort(key=lambda x:x['year'])
wsb3=ws.buffer(0)
st3=' '.join(r3d.path3d(g.intersection(wsb3),gD) for g in nhd.geometry if g.intersects(wsb3))
ov['d']=dict(name='3D',w=r3d.W,h=r3d.H,res=None,bounds=None,parcel=r3d.path3d(parcel,gD),watershed=r3d.path3d(ws,gD),streams=st3,fires=fires3,creeks=[])
for fid,*_ in F:
    im=Image.open(f'v3d/r_{fid}.jpg'); im.save(f'site/frames/d_{fid}.jpg',quality=86,optimize=True,progressive=True); im.resize((1200,900),Image.LANCZOS).save(f'site/frames/ds_{fid}.jpg',quality=80,optimize=True,progressive=True)
FCOL={(1955,'C. Gardner'):'#ff8a3d',(1964,'Mattole'):'#ff4d6d',(1960,'Beatty Escape'):'#d98cff',(1950,'Edward Helm'):'#8be28b',(1950,'James Bridges'):'#f2a6c8'}
for vv in ov.values():
    for f in vv['fires']: f['color']=FCOL.get((f['year'],f['name']),'#c9c9c9')
json.dump(dict(frames=[dict(id=f[0],label=f[2],date=f[3],source=f[4],res=f[5],note=f[6]) for f in F],views=ov),open('site/data.json','w'))
print(len(json.dumps(ov)))
