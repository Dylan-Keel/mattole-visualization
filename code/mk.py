import sys,json; sys.path.insert(0,'/home/claude/work')
import yb,loc
CAT=loc.catalog()
def aid(title,date):
    c=[a for t,d,a in CAT if t==title and d.startswith(date)]
    return c[0] if c else None
def run(tag,date,specs):
    fr=[]
    for t,x,y,mpp,rot in specs:
        a=aid(t,date)
        if a: fr.append((t,a,x,y,mpp,rot))
        else: print('missing',t,date)
    return yb.build(tag,fr)
if __name__=='__main__':
    jobs=json.load(open(sys.argv[1]))
    for j in jobs: run(j['tag'],j['date'],[tuple(s) for s in j['specs']])
