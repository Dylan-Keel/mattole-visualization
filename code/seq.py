import json,sys,re
rows=[json.loads(l) for l in open(sys.argv[1])]; zmin=float(sys.argv[2])
key=lambda r:(r['date'],[int(x) if x.isdigit() else x for x in re.split(r'(\d+)',r['title'])])
for r in sorted(rows,key=key):
    if r['z']>=zmin and not (r['x']<389000 and r['y']<4454500):
        half=r['mpp']*170; near=abs(r['x']-393200)<half+300 and abs(r['y']-4458050)<half+300
        print(r['title'],r['date'],r['aid'],'z',r['z'],'mpp',r['mpp'],'rot',r['rot'],r['x'],r['y'],'<<<' if near else '')
