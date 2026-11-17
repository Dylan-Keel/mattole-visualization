import numpy as np, cv2, json, glob, os, rasterio, requests, io, collections
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
import ortho
E3=(391000,4455500,395500,4461000); R=2.0; W=int((E3[2]-E3[0])/R); H=int((E3[3]-E3[1])/R); CF=0.08
X,Y=np.meshgrid(E3[0]+(np.arange(W,dtype=np.float32)+.5)*R, E3[3]-(np.arange(H,dtype=np.float32)+.5)*R)
def historic(tag):
    layers=[]
    for pf in sorted(glob.glob(f'full/pose_{tag}_*.npz')):
        t=os.path.basename(pf)[len(f'pose_{tag}_'):-4]; z=np.load(pf)
        im=np.asarray(Image.open(f'full/all/{tag}_{t}.jpg').convert('L')); h,w=im.shape; a=im[int(h*CF):int(h*(1-CF)),int(w*CF):int(w*(1-CF))]
        a=cv2.GaussianBlur(a,(0,0),0.8)
        o=ortho.ortho(a,z['K'],z['d'],z['rv'],z['tv'],E3,R).astype(np.float32)
        v=cv2.erode((o>0).astype(np.uint8),np.ones((15,15),np.uint8)).astype(bool); d2=(X-z['cam'][0])**2+(Y-z['cam'][1])**2
        layers.append([o,v,d2])
    layers.sort(key=lambda L:-L[1].sum()); ro,rv=layers[0][0],layers[0][1]
    best=np.full((H,W),1e12,np.float32); out=np.zeros((H,W),np.float32)
    for i,(o,v,d2) in enumerate(layers):
        ov=v&rv
        if i>0 and ov.sum()>5000: o[:]=(o-o[ov].mean())*(ro[ov].std()/max(o[ov].std(),1e-3))+ro[ov].mean()
        m=v&(d2<best); out[m]=o[m]; best[m]=d2[m]
    out=np.clip(out,1,255).astype(np.uint8); out[best>=1e11]=0; return np.repeat(out[...,None],3,2)
def napp(nm):
    scan=np.asarray(Image.open(nm+'.tif').convert('L')).copy(); z=np.load(f'pose_{nm}.npz'); m=330
    scan[:m]=0; scan[-m:]=0; scan[:,:m]=0; scan[:,-m:]=0
    o=ortho.ortho(scan,z['K'],z['d'],z['rv'],z['tv'],E3,R); return np.repeat(o[...,None],3,2)
def county(y):
    for k in range(4):
        try:
            r=requests.get(f'https://webgis.co.humboldt.ca.us/arcgis/rest/services/NAIP_{y}/ImageServer/exportImage',params=dict(bbox=','.join(map(str,E3)),bboxSR=26910,imageSR=26910,size=f'{W},{H}',format='jpgpng',interpolation='RSP_BilinearInterpolation',f='image'),timeout=240)
            return np.asarray(Image.open(io.BytesIO(r.content)).convert('RGB'))
        except Exception as e: print('retry',y,str(e)[:60])
def esri():
    r=requests.get('https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export',params=dict(bbox=','.join(map(str,E3)),bboxSR=26910,imageSR=26910,size=f'{W},{H}',format='jpg',f='image'),timeout=240)
    return np.asarray(Image.open(io.BytesIO(r.content)).convert('RGB'))
def pc_all():
    import pystac_client, planetary_computer as pc
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_origin
    from pyproj import Transformer
    tr=Transformer.from_crs(26910,4326,always_xy=True); lo=tr.transform(E3[0],E3[1]); hi=tr.transform(E3[2],E3[3]); T=from_origin(E3[0],E3[3],R,R)
    c=pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
    by=collections.defaultdict(list)
    for it in c.search(collections=["naip"],bbox=[lo[0],lo[1],hi[0],hi[1]]).items(): by[it.datetime.year].append(it)
    for y,its in sorted(by.items()):
        if os.path.exists(f'v3d/tex_{y}.jpg'): continue
        out=np.zeros((3,H,W),'uint8')
        for it in its:
            with rasterio.open(it.assets['image'].href) as s:
                tmp=np.zeros((3,H,W),'uint8'); reproject(rasterio.band(s,[1,2,3]),tmp,dst_transform=T,dst_crs='EPSG:26910',resampling=Resampling.average)
                m=(tmp.sum(0)>0)&(out.sum(0)==0); out[:,m]=tmp[:,m]
        save(str(y),np.moveaxis(out,0,-1))
def save(tag,a):
    if a is None: print(tag,'FAILED'); return
    Image.fromarray(a).save(f'v3d/tex_{tag}.jpg',quality=90); print(tag,a.shape,'cov %.2f'%((a.sum(2)>0).mean()),flush=True)
if __name__=='__main__':
    for t in ('1941','1948','1954','1959','1963','1966','1970','1974','1981'): save(t,historic(t))
    save('1993',napp('napp1993')); save('1998',napp('napp1998'))
    save('2025',esri())
    for y in (2005,2009,2010): save(str(y),county(y))
    pc_all()
    open('v3d/wide.done','w').write('ok')
