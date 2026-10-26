import json,urllib.request,urllib.parse
B="https://hindsightcricket.com/api/query/deliveries?"
def q(p):
    with urllib.request.urlopen(B+urllib.parse.urlencode(p,doseq=True),timeout=300) as r: return json.load(r)['data']
L=['IPL','BBL','PSL','CPL','SA20','T20 Blast','ILT20','MLC','BPL','LPL','Super Smash']
SC={'T20':dict(format='T20',start_date='2024-01-01',leagues=L,include_international='true',top_teams=12),
    'ODI':dict(format='ODI',start_date='2023-01-01',include_international='true',top_teams=12)}
MINB={'T20':{'bowl':600,'bat':300},'ODI':{'bowl':500,'bat':400}}
SPEC={'T20':{'bowl':[('wpa','Wins added',False,2),('dot_percentage','Dot balls %',False,1),('economy','Economy',True,2),('balls_per_dismissal','Balls per wicket',True,1)],
             'bat':[('wpa','Wins added',False,2),('strike_rate','Strike rate',False,1),('average','Average',False,1)]},
      'ODI':{'bowl':[('balls_per_dismissal','Balls per wicket',True,1),('dot_percentage','Dot balls %',False,1),('economy','Economy',True,2)],
             'bat':[('strike_rate','Strike rate',False,1),('average','Average',False,1)]}}
WANT={'T20':[('Marco Jansen','bowl'),('Marco Jansen','bat'),('Jasprit Bumrah','bowl'),('Abhishek Sharma','bat')],'ODI':[('Marco Jansen','bowl'),('Marco Jansen','bat')]}
def econ(rows):
    for r in rows:
        if r.get('balls'): r['economy']=r['runs']*6/r['balls']
    return rows
out={}
for f,lst in WANT.items():
    peers={}
    for role in ('bowl','bat'):
        grp='bowler' if role=='bowl' else 'batter'; persp='bowling' if role=='bowl' else 'batting'
        peers[role]=econ(q(dict(SC[f],metrics_perspective=persp,group_by=grp,min_balls=MINB[f][role],limit=5000)))
    for name,role in lst:
        grp='bowler' if role=='bowl' else 'batter'; persp='bowling' if role=='bowl' else 'batting'
        rows=peers[role]; me=[r for r in rows if r[grp]==name][0]
        ms=[]
        for k,label,lb,dp in SPEC[f][role]:
            vals=sorted(round(r[k],dp) for r in rows if r.get(k) is not None)
            v=me[k]; better=sum((x<v) if lb else (x>v) for x in vals)
            ms.append(dict(key=k,label=label,lower_better=lb,value=round(v,dp),rank=better+1,n=len(vals),peers=vals))
        base=dict(SC[f],metrics_perspective=persp); base['bowlers' if role=='bowl' else 'batters']=name
        yrs=econ(q(dict(base,group_by='year'))); ph=econ(q(dict(base,group_by='phase')))
        mt=q(dict(base,group_by=['match_id','match_date','batting_team' if role=='bowl' else 'bowling_team','competition']))
        mt=sorted(mt,key=lambda r:r['match_date'])[-8:]
        keep=['balls','runs','wickets','strike_rate','average','balls_per_dismissal','dot_percentage','economy','wpa','impact_per_innings','raa_per_100','raa','innings_count']
        out[f'{f}|{name}|{role}']=dict(balls=me['balls'],runs=me['runs'],wickets=me.get('wickets'),innings=me.get('innings_count'),metrics=ms,
            years=[{k:r.get(k) for k in ['year']+keep} for r in sorted(yrs,key=lambda r:r['year'])],
            phases=[{k:r.get(k) for k in ['phase']+keep} for r in ph],
            form=[{k:r.get(k) for k in ['match_date','batting_team','bowling_team','competition']+keep} for r in mt])
        print(f,name,role,[(m['label'],m['value'],m['rank'],m['n']) for m in ms])
        for r in out[f'{f}|{name}|{role}']['years']: print('   ',r['year'],r['balls'],r['runs'],r['wickets'],r['wpa'],round(r.get('economy') or 0,2),round(r['strike_rate'] or 0,1))
        for r in out[f'{f}|{name}|{role}']['phases']: print('   ph',r['phase'],r['balls'],round(r.get('economy') or 0,2),round(r['strike_rate'] or 0,1),r['dot_percentage'] and round(r['dot_percentage'],1),r['raa_per_100'],r['wickets'])
        for r in out[f'{f}|{name}|{role}']['form']: print('   m',r['match_date'],r['competition'],r['batting_team'] if role=='bowl' else r['bowling_team'],r['balls'],r['runs'],r['wickets'],r['raa'])
json.dump(out,open('data.json','w'),separators=(',',':'))
