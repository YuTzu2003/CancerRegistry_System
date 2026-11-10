import csv, math, re, zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from lifelines import KaplanMeierFitter
from lifelines.utils import survival_table_from_events

import argparse
parser=argparse.ArgumentParser(description='Cancer survival analysis; only select_memo=15_納入統計人數')
parser.add_argument('--cases',required=True,help='Full case Excel .xlsx')
parser.add_argument('--rules',required=True,help='Official method Word .docx')
parser.add_argument('--output',default='results',help='Output folder')
args=parser.parse_args()
src=Path(args.cases)
if src.suffix.lower()!='.xlsx' or not src.is_file():raise ValueError('Select a real .xlsx case file')
if Path(args.rules).suffix.lower()!='.docx':raise ValueError('Select a .docx rules file')
OUT=Path(args.output);OUT.mkdir(parents=True,exist_ok=True)
doc=Document(args.rules)
raw=pd.read_excel(src,sheet_name='LF_8',dtype=str)
raw=raw.loc[raw.select_memo.eq('15_納入統計人數')].copy()
assert len(raw)==5532
raw['age']=pd.to_numeric(raw.age,errors='coerce')
raw['Surv_Months']=pd.to_numeric(raw.Surv_Months,errors='coerce')
raw['event']=raw.Status_OS.map({'death':1,'censor':0})
invalid=raw[raw[['age','Surv_Months','event','pri_site','didiag']].isna().any(axis=1) | raw.Surv_Months.lt(0)]
invalid[['pri_site','didiag','Status_OS','Surv_Months']].to_csv(OUT/'資料異常檢查.csv',index=False,encoding='utf-8-sig')
raw=raw.drop(index=invalid.index)
# Official 2013 national cancer-specific age weights, from Word table 0.
tbl=doc.tables[0]
names=['Oral cavity','Oropharynx','Hypopharynx','Nasopharynx','Colon and Rectum','Liver','Pancreas','Lung','Breast','Cervix','Esophagus','Stomach','Bladder','Corpus','Ovary','Prostate','Larynx']
weights={name:np.array([float(tbl.cell(r,c).text.strip())/100 for r in range(2,7)]) for c,name in enumerate(names,start=2)}
assert all(abs(sum(w)-1)<1e-9 for w in weights.values())
pd.DataFrame({'cancer':np.repeat(names,5),'age_group':list(range(1,6))*17,'weight':np.concatenate([weights[n] for n in names])}).to_csv(OUT/'官方標準權重.csv',index=False,encoding='utf-8-sig')

def km(d,times):
    if len(d)==0:return [math.nan]*len(times),([],[])
    fitter=KaplanMeierFitter().fit(d.Surv_Months.to_numpy(dtype=float),event_observed=d.event.to_numpy(dtype=int))
    ts=fitter.survival_function_.index.to_numpy(dtype=float).tolist()
    ss=fitter.survival_function_.iloc[:,0].to_numpy(dtype=float).tolist()
    vals=[]
    for t in times:
        if t>ts[-1] and ss[-1]>0:vals.append(math.nan)
        else:vals.append(ss[np.searchsorted(ts,t,side='right')-1])
    return vals,(ts,ss)

def life(d):
    # lifelines builds the event table; the actuarial n-w/2 estimate is
    # calculated below because a collapsed event table is not itself a life table.
    events=survival_table_from_events(d.Surv_Months.to_numpy(dtype=float),d.event.to_numpy(dtype=int))
    et=events.index.to_numpy(dtype=float)
    out=[];cum=1.
    for a in range(0,60,12):
        b=a+12; inside=(et>=a)&((et<=b) if b==60 else (et<b))
        n=int(d.Surv_Months.ge(a).sum())
        death=int(events.loc[inside,'observed'].sum())
        censor=int(events.loc[inside,'censored'].sum())
        effective=n-censor/2
        interval=1-death/effective if effective>0 else math.nan
        if n==0 or (d.Surv_Months.max()<b and cum!=0):cum=math.nan
        elif cum==0:pass
        else:cum*=interval
        out.append([a,b,n,death,censor,effective,interval,cum])
    return out

def merge_age(d,cancer):
    edges=[15,55,65,75,85,math.inf] if cancer=='Prostate' else [15,45,55,65,75,math.inf]
    groups=[]
    for a,b in zip(edges[:-1],edges[1:]):groups.append({'lo':a,'hi':b,'weight':weights[cancer][len(groups)],'d':d[d.age.ge(a)&d.age.lt(b)]})
    while len(groups)>1 and any(len(x['d'])<10 for x in groups):
        i=next(i for i,x in enumerate(groups) if len(x['d'])<10)
        j=1 if i==0 else len(groups)-2 if i==len(groups)-1 else (i-1 if len(groups[i-1]['d'])<=len(groups[i+1]['d']) else i+1)
        lo=min(i,j);hi=max(i,j)
        groups[lo]={'lo':groups[lo]['lo'],'hi':groups[hi]['hi'],'weight':groups[lo]['weight']+groups[hi]['weight'],'d':pd.concat([groups[lo]['d'],groups[hi]['d']])}
        groups.pop(hi)
    return groups

summary=[];lrows=[];arows=[]; checks=[]
period=[]
for cancer in names:
    z=raw[raw.pri_site.eq(cancer)].copy()
    if cancer=='Pancreas':z=z[z.year.astype(int).between(111,112)]
    elif cancer=='Cervix':z=z[z.year.astype(int).between(110,112)]
    else:z=z[z.year.astype(int).between(108,112)]
    if len(z)==0:continue
    period.append([cancer,len(z),int(z.year.astype(int).min()),int(z.year.astype(int).max())])
    # Stage is the supplied merged fnstage; broad I-IV from first digit.
    z['stage']=z.fnstage.str.extract(r'^([1-4])',expand=False).map({'1':'I','2':'II','3':'III','4':'IV'})
    slug=re.sub('[^A-Za-z0-9]+','_',cancer)
    z['end_date']=np.where(z.event.eq(1),z.death_d,'20251231')
    imp=z[['didiag','end_date','fnstage','age','event','Surv_Months']].copy()
    imp.columns=['存活率計算起日','存活率計算迄日','Stage','age','生存狀態(death:1,alive:0)','Surv_Months']
    imp.to_csv(OUT/f'{slug}_資料匯入範本.csv',index=False,encoding='utf-8-sig')
    fig=plt.figure(figsize=(10,8),layout='constrained')
    axes=fig.subplots(2,1,height_ratios=[1.2,3.3]);table_ax,ax=axes
    table_ax.axis('off');report_rows=[];cancer_life=[]
    for label,g in [('All',z)]+[(f'Stage {i}',z[z.stage.eq(i)]) for i in 'I II III IV'.split()]:
        if len(g)==0:
            report_rows.append([label,'0',*(['—']*5)])
            continue
        rates,(t,s)=km(g,[12,24,36,48,60])
        summary.append([cancer,label,len(g),*rates])
        report_rows.append([label,str(len(g)),*[f'{100*v:.1f}' if math.isfinite(v) else 'NA' for v in rates]])
        for a,b,n,death,censor,effective,interval,cum in life(g):
            lrows.append([cancer,label,a,b,n,death,censor,effective,interval,cum])
            cancer_life.append([label,f'{a}–{b}',str(n),str(death),str(censor),f'{cum*100:.1f}%' if math.isfinite(cum) else 'NA'])
        if label!='All':ax.step(np.array(t)/12,s,where='post',label=f'{label} (n={len(g)})')
    table_ax.set_title(f'{cancer} — annual Kaplan–Meier observed survival (%)',fontsize=12,pad=8)
    tab=table_ax.table(cellText=report_rows,colLabels=['AJCC Stage','Cases','1-yr','2-yr','3-yr','4-yr','5-yr'],loc='center',cellLoc='center',bbox=[0,0,1,.9])
    tab.auto_set_font_size(False);tab.set_fontsize(9)
    ax.set(xlim=(0,5),ylim=(0,1),xlabel='Years since diagnosis',ylabel='Observed survival',title=f'{cancer} — survival by broad stage')
    ax.legend(loc='best',fontsize=8);ax.grid(alpha=.2)
    fig.savefig(OUT/f'{slug}_KM表與存活曲線.png',dpi=200);fig.savefig(OUT/f'{slug}_KM表與存活曲線.pdf');plt.close(fig)
    lf,la=plt.subplots(figsize=(10,max(4,len(cancer_life)*.25+1.2)))
    la.axis('off');la.set_title(f'{cancer} — 12-month actuarial life table',pad=12)
    lt=la.table(cellText=cancer_life,colLabels=['Stage','Months','At risk','Deaths','Censored','Cumulative survival'],cellLoc='center',bbox=[0,0,1,.95])
    lt.auto_set_font_size(False);lt.set_fontsize(8)
    lf.savefig(OUT/f'{slug}_生命表.png',dpi=170,bbox_inches='tight');plt.close(lf)
    for label,g in [('All',z)]+[(f'Stage {i}',z[z.stage.eq(i)]) for i in 'I II III IV'.split()]:
        if len(g)==0:continue
        merged=merge_age(g,cancer)
        rates=[];detail=[]
        for k,x in enumerate(merged,1):
            r,_=km(x['d'],[12,24,36,48,60]);rates.append(r)
            detail.append((k,x,r))
        valid=len(merged)>1
        adjusted=[]
        for yr in range(5):
            val=sum(x['weight']*r[yr] for _,x,r in detail) if valid and all(len(x['d'])>=10 and not math.isnan(r[yr]) for _,x,r in detail) else math.nan
            adjusted.append(val)
        arows.append([cancer,label,len(g),len(merged),*adjusted])
        for k,x,r in detail:checks.append([cancer,label,k,x['lo'],x['hi'],len(x['d']),x['weight'],*r,x['weight']*r[4]])

pd.DataFrame(period,columns=['癌別','個案數','診斷民國年起','診斷民國年迄']).to_csv(OUT/'分析期間與人數.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(summary,columns=['癌別','期別','個案數','1年OS','2年OS','3年OS','4年OS','5年OS']).to_csv(OUT/'各癌別_KM存活率.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(lrows,columns=['癌別','期別','開始月','結束月','進入人數','死亡','設限','有效風險數','區間存活率','累積存活率']).to_csv(OUT/'各癌別_生命表.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(arows,columns=['癌別','期別','個案數','合併年齡組數','1年加權OS','2年加權OS','3年加權OS','4年加權OS','5年加權OS']).to_csv(OUT/'各癌別_年齡標準化OS.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(checks,columns=['癌別','期別','併組序','年齡起','年齡迄未含','人數','合併權重','1年OS','2年OS','3年OS','4年OS','5年OS','5年加權貢獻']).to_csv(OUT/'加權年齡併組明細.csv',index=False,encoding='utf-8-sig')
print(pd.DataFrame(arows,columns=['癌別','期別','個案數','合併年齡組數','1年加權OS','2年加權OS','3年加權OS','4年加權OS','5年加權OS']).query("期別=='All'")[['癌別','個案數','5年加權OS']].to_string(index=False))
