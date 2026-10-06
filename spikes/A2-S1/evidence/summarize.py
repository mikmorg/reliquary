import json,re,sys
out={}
for v in ("default","soft"):
    t=open(f'bench-kem-{v}.txt').read()
    loads=re.findall(r'load: ([\d.]+)',t)
    blocks=re.split(r'== round \d+ load: [^\n]*\n',t)[1:]
    kem={}
    for b in blocks:
        for k,x in json.loads(b).items():
            c=kem.setdefault(k,{"header_len":x["header_len"],"gen_us_best":1e9,"open_us_best":1e9})
            c["gen_us_best"]=min(c["gen_us_best"],x["gen_us"]); c["open_us_best"]=min(c["open_us_best"],x["open_us"])
    t=open(f'bench-obj-{v}.txt').read()
    loads+=re.findall(r'load: ([\d.]+)',t)
    parts=re.split(r'== size (\d+) round \d+ load: [^\n]*\n',t)[1:]
    obj={}
    for i in range(0,len(parts),2):
        s=int(parts[i]); j=json.loads(parts[i+1])
        for k in ("x25519x1","pqx1","pqx2"):
            obj.setdefault(s,{}).setdefault(k,0); obj[s][k]=max(obj[s][k],j[k]["MB_per_s"])
    for s,d in obj.items():
        d["pq1_loss_pct"]=round(100*(1-d["pqx1"]/d["x25519x1"]),1); d["pq2_loss_pct"]=round(100*(1-d["pqx2"]/d["x25519x1"]),1)
    out[v]={"kem":kem,"obj_MBps_best_of_3":obj,"load1_range":[min(map(float,loads)),max(map(float,loads))]}
json.dump(out,open('summary.json','w'),indent=1); print(json.dumps(out,indent=1))
