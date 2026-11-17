import numpy as np, cv2, rasterio, json, re, os, sys, requests, time
from PIL import Image
G=30.0; BX=(385500,4450800,400500,4465800)   # search window around the parcel (15 km)
dem=rasterio.open('ref/dem10.tif').read(1)
def hillshade(az,alt):
    gy,gx=np.gradient(dem,10.0); a=np.radians(az); e=np.radians(alt)
    nx=-gx; ny=gy; nn=np.sqrt(nx*nx+ny*ny+1)
    return np.clip((nx*np.sin(a)*np.cos(e)+ny*np.cos(a)*np.cos(e)+np.sin(e))/nn,0,1).astype(np.float32)
hp=lambda a,s:cv2.GaussianBlur(a,(0,0),0.8)-cv2.GaussianBlur(a,(0,0),s)
def win(a,res):   # crop full 18 km raster (origin 384000,4468000) to BX and resample to G
    c=a[int((4468000-BX[3])/res):int((4468000-BX[1])/res),int((BX[0]-384000)/res):int((BX[2]-384000)/res)]
    return cv2.resize(c,(int((BX[2]-BX[0])/G),int((BX[3]-BX[1])/G)),interpolation=cv2.INTER_AREA)
REFS=None
def refs():
    global REFS
    if REFS is None:
        r05=rasterio.open('ref/ref2m.tif').read(1).astype(np.float32)
        REFS=[('hsE',hp(win(hillshade(110,45),10)*255,10)),('hsS',hp(win(hillshade(180,45),10)*255,10)),('hsW',hp(win(hillshade(250,45),10)*255,10)),('img05',hp(win(r05,2),10))]
    return REFS
SCALES=(7.2,8.4,9.8,11.4,13.2,15.3)
def crop(path):
    a=np.asarray(Image.open(path).convert('L')); h,w=a.shape; return a[int(h*.08):int(h*.92),int(w*.08):int(w*.92)]
_C={}
def coarse_refs(g):
    if g not in _C:
        def w2(a,res):
            c=a[int((4468000-BX[3])/res):int((4468000-BX[1])/res),int((BX[0]-384000)/res):int((BX[2]-384000)/res)]
            return cv2.resize(c,(int((BX[2]-BX[0])/g),int((BX[3]-BX[1])/g)),interpolation=cv2.INTER_AREA)
        s=300.0/g
        _C[g]=[(nm,hp(w2(hillshade(az,45),10)*255,s)) for nm,az in (('hs150',150),('hs215',215))]
    return _C[g]
def locate(a,g=50.0,scales=SCALES,drs=(-7,0,7),top=1):
    a=a.astype(np.float32); out=[]; s=300.0/g
    for mpp in scales:
        t=cv2.resize(cv2.GaussianBlur(a,(0,0),max(0.5,g/mpp/2.5)),None,fx=mpp/g,fy=mpp/g,interpolation=cv2.INTER_AREA)
        if min(t.shape)<28: continue
        for base in (0,90,180,270):
            tb=np.ascontiguousarray(np.rot90(t,base//90))
            for dr in drs:
                hh,ww=tb.shape; M=cv2.getRotationMatrix2D((ww/2,hh/2),dr,1.0)
                tr=hp(cv2.warpAffine(tb,M,(ww,hh),borderMode=cv2.BORDER_REFLECT),s); m=int(min(hh,ww)*0.1); tr=tr[m:-m,m:-m]
                for nm,R in coarse_refs(g):
                    res=cv2.matchTemplate(R,tr,cv2.TM_CCOEFF_NORMED); _,mx,_,lc=cv2.minMaxLoc(res)
                    z=(mx-res.mean())/(res.std()+1e-6)
                    out.append((float(z),float(mx),nm,mpp,base+dr,BX[0]+(lc[0]+tr.shape[1]/2)*g,BX[3]-(lc[1]+tr.shape[0]/2)*g))
    out.sort(reverse=True); zs=np.array([o[0] for o in out])
    return out[0],float(zs[0]-np.median(zs))
S=requests.Session(); S.headers['User-Agent']='Mozilla/5.0'
def preview(aid):
    fn=f'hc/pv/{aid}.jpg'
    if not os.path.exists(fn):
        for k in range(3):
            try:
                b=S.get(f'https://digitalcommons.humboldt.edu/hcapc_aerial/{aid}/preview.jpg',timeout=40).content
                if b[:2]==b'\xff\xd8': open(fn,'wb').write(b); break
            except Exception as e: time.sleep(1)
        else: return None
    return fn if os.path.exists(fn) else None
def catalog():
    R=[json.loads(l) for l in open('hc/oai.jsonl')]; out=[]
    for r in R:
        if not r['title'] or not r['identifier']: continue
        m=re.search(r'article/(\d+)/',r['identifier'][0])
        if m: out.append((r['title'][0],(r['date'][0][:10] if r['date'] else ''),m.group(1)))
    return out
if __name__=='__main__':
    os.makedirs('hc/pv',exist_ok=True)
    pat=sys.argv[1]; step=int(sys.argv[2]); outf=sys.argv[3]
    cat=[c for c in catalog() if re.match(pat,c[0])]
    seen=set(); cat=[c for c in cat if not (c[0] in seen or seen.add(c[0]))]
    key=lambda c:[int(x) if x.isdigit() else x for x in re.split(r'(\d+)',c[0])]
    cat=sorted(cat,key=key)[::step]; print(len(cat),'frames',flush=True)
    done=set(json.loads(l)['title'] for l in open(outf)) if os.path.exists(outf) else set()
    with open(outf,'a') as f:
        for t,d,aid in cat:
            if t in done: continue
            fn=preview(aid)
            if not fn: continue
            try: b,z=locate(crop(fn))
            except Exception as e: continue
            f.write(json.dumps(dict(title=t,date=d,aid=aid,z=round(b[0],2),ncc=round(b[1],3),ref=b[2],mpp=b[3],rot=b[4],x=round(b[5]),y=round(b[6]),dz=round(z,2)))+'\n'); f.flush()
