import numpy as np, cv2, json, sys, os, rasterio
from rasterio.transform import from_origin
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
import og, ortho
B=(392000,4456700,394400,4459400); RES=0.5; CF=0.08; WFIT=1400
def fit_full(path,cx,cy,mpp_prev,rot):
    im=Image.open(path).convert('L'); W,H=im.size
    small=im.resize((WFIT,int(H*WFIT/W)),Image.LANCZOS); tmp='/tmp/fit_small.jpg'; small.save(tmp,quality=92)
    f=og.fit(tmp,cx,cy,mpp_prev*336.0/(WFIT*(1-2*CF)),rot,up=1,verbose=False,cropf=CF)
    a=np.asarray(im); a=a[int(H*CF):int(H*(1-CF)),int(W*CF):int(W*(1-CF))]
    s=a.shape[1]/f['scan'].shape[1]; sy=a.shape[0]/f['scan'].shape[0]
    K=f['K'].copy(); K[0,0]*=s; K[1,1]*=sy; K[0,2]*=s; K[1,2]*=sy
    f['K_full']=K; f['full']=a; f['gsd']=None
    return f
def build(tag,frames,minscore=0.10):
    W=int((B[2]-B[0])/RES); H=int((B[3]-B[1])/RES)
    X,Y=np.meshgrid(B[0]+(np.arange(W,dtype=np.float32)+.5)*RES, B[3]-(np.arange(H,dtype=np.float32)+.5)*RES)
    best=np.full((H,W),1e12,np.float32); out=np.zeros((H,W),np.float32); layers=[]; used=[]
    for path,cx,cy,mpp,rot in frames:
        t=os.path.basename(path)[5:-4]
        f=None
        for mf,dx,dy in ((1,0,0),(0.9,0,0),(1.1,0,0),(1,200,200),(1,-200,-200),(0.95,200,-200),(1.05,-200,200),(1.2,0,0),(0.82,0,0)):
            try: g=fit_full(path,cx+dx,cy+dy,mpp*mf,rot)
            except Exception as e: print(tag,t,'fit error',str(e)[:100],flush=True); continue
            if f is None or (g['inl'],g['score'])>(f['inl'],f['score']): f=g
            if f['inl']>=60 and f['score']>0.15: break
        if f is None: continue
        ok=f['inl']>=35 and f['score']>minscore
        print(tag,t,'inl',f['inl'],'med %.2f'%f['med'],'score %.3f'%f['score'],'cam %.0f %.0f %.0f'%f['cam'],'OK' if ok else 'REJECT',flush=True)
        if not ok: continue
        np.savez(f'full/pose_{tag}_{t.replace(" ","_")}.npz',K=f['K_full'],d=f['d'],rv=f['rv'],tv=f['tv'],cam=f['cam'])
        o=ortho.ortho(f['full'],f['K_full'],f['d'],f['rv'],f['tv'],B,RES).astype(np.float32)
        v=cv2.erode((o>0).astype(np.uint8),np.ones((41,41),np.uint8)).astype(bool)
        d2=(X-f['cam'][0])**2+(Y-f['cam'][1])**2
        layers.append([o,v,d2,t,f['inl'],f['med'],f['score']]); del f
    if not layers: return None
    layers.sort(key=lambda L:-L[1].sum()); ro,rv_=layers[0][0],layers[0][1]
    for o,v,d2,t,inl,med,sc in layers:
        ov=v&rv_
        if t!=layers[0][3] and ov.sum()>20000:
            a,b=o[ov].std(),ro[ov].std(); o[:]=(o-o[ov].mean())*(b/max(a,1e-3))+ro[ov].mean()
        m=v&(d2<best); out[m]=o[m]; best[m]=d2[m]; used.append(dict(title=t,inl=int(inl),med=round(float(med),2),score=round(float(sc),3)))
    cov=float((best<1e11).mean()); out=np.clip(out,0,255).astype(np.uint8); out[best>=1e11]=0
    with rasterio.open(f'master/full_{tag}.tif','w',driver='GTiff',width=W,height=H,count=1,dtype='uint8',crs='EPSG:26910',transform=from_origin(B[0],B[3],RES,RES),compress='deflate') as ds: ds.write(out,1)
    json.dump(dict(tag=tag,coverage=cov,used=used),open(f'full/yr_{tag}.json','w'))
    cv2.imwrite(f'full/yr_{tag}_th.jpg',cv2.resize(out,(W//4,H//4),interpolation=cv2.INTER_AREA)); print(tag,'coverage %.2f'%cov,[u['title'] for u in used],flush=True)
if __name__=='__main__':
    for j in json.load(open(sys.argv[1])): build(j['tag'],[tuple(s) for s in j['specs']])
