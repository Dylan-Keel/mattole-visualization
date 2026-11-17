import numpy as np, cv2, json, sys, rasterio, os
from rasterio.transform import from_origin
import og, ortho, loc
B=(392000,4456700,394400,4459400); RES=2.0
def build(tag,frames,minres=None):
    """frames: list of (title, aid, x, y, mpp, rot). Returns mosaic at 2 m, coverage, used list"""
    W=int((B[2]-B[0])/RES); H=int((B[3]-B[1])/RES)
    X,Y=np.meshgrid(B[0]+(np.arange(W)+.5)*RES, B[3]-(np.arange(H)+.5)*RES)
    best=np.full((H,W),1e12); out=np.zeros((H,W),np.float32); used=[]; layers=[]
    for t,aid,x,y,mpp,rot in frames:
        fn=loc.preview(aid)
        if not fn: print(tag,t,'no preview'); continue
        try: f=og.fit(fn,x,y,mpp,rot,verbose=False)
        except Exception as e: print(tag,t,'fit error',str(e)[:80]); continue
        ok=f['inl']>=35 and f['score']>0.10
        print(tag,t,'inl',f['inl'],'med %.2f'%f['med'],'score %.3f'%f['score'],'cam %.0f %.0f %.0f'%f['cam'],'OK' if ok else 'REJECT',flush=True)
        if not ok: continue
        o=ortho.ortho(f['scan'],f['K'],f['d'],f['rv'],f['tv'],B,RES).astype(np.float32)
        # erode valid area so frame borders/fiducials are not used
        v=cv2.erode((o>0).astype(np.uint8),np.ones((15,15),np.uint8)).astype(bool)
        d2=(X-f['cam'][0])**2+(Y-f['cam'][1])**2
        layers.append((o,v,d2,t,f))
    if not layers: return None
    # radiometric match to the layer with most coverage
    layers.sort(key=lambda L:-L[1].sum()); ref_o,ref_v=layers[0][0],layers[0][1]
    for o,v,d2,t,f in layers:
        ov=v&ref_v
        if t!=layers[0][3] and ov.sum()>5000:
            a,b=o[ov].std(),ref_o[ov].std(); o[:]=(o-o[ov].mean())*(b/max(a,1e-3))+ref_o[ov].mean()
        m=v&(d2<best); out[m]=o[m]; best[m]=d2[m]; used.append(dict(title=t,inl=f['inl'],med=round(f['med'],2),score=round(f['score'],3),cam=[round(c) for c in f['cam']],mpp_native=None))
    cov=float((best<1e11).mean()); out=np.clip(out,0,255).astype(np.uint8)
    np.save(f'yr_{tag}.npy',out); json.dump(dict(tag=tag,coverage=cov,used=used),open(f'yr_{tag}.json','w'))
    cv2.imwrite(f'yr_{tag}.jpg',out); print(tag,'coverage %.2f'%cov,[u['title'] for u in used],flush=True)
    return out,cov,used
if __name__=='__main__':
    tag=sys.argv[1]; frames=json.load(open(sys.argv[2])); build(tag,[tuple(f) for f in frames])
