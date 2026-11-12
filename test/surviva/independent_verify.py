#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""獨立驗證 Surviva。只輸出彙總/匿名列號，不輸出姓名/病歷號/身分證/逐筆日期。"""
import sys, math, io
from pathlib import Path
import numpy as np, pandas as pd
from docx import Document
from lifelines import KaplanMeierFitter

BASE = Path('Surviva')
OUT = Path(r'C:/Users/user/AppData/Local/Temp/claude/e2ee30c1d7b3421d/b9c82edf-40df-4d81-96bb-8e9630617fe5/scratchpad/vout')
OUT.mkdir(parents=True, exist_ok=True)
log = io.StringIO()
def P(*a):
    s=' '.join(str(x) for x in a); print(s); log.write(s+'\n')

# ---------- load ----------
raw = pd.read_excel(BASE/'2026存活率個案清單.xlsx', sheet_name='LF_8', dtype=str)
raw = raw[raw.select_memo.str.strip().eq('15_納入統計人數')].copy()
P('納入筆數 select_memo==15 :', len(raw))
raw['age']=pd.to_numeric(raw.age,errors='coerce')
raw['Surv_Months']=pd.to_numeric(raw.Surv_Months,errors='coerce')
raw['event']=raw.Status_OS.str.strip().str.lower().map({'death':1,'censor':0})
raw['year']=raw.year.astype(int)

# ---------- Word 官方 102年標準人口權重 ----------
doc=Document(str(BASE/'1_115年癌症存活率回饋說明_2026092320261005090504.docx'))
tbl=doc.tables[0]
names=['Oral cavity','Oropharynx','Hypopharynx','Nasopharynx','Colon and Rectum','Liver','Pancreas','Lung','Breast','Cervix','Esophagus','Stomach','Bladder','Corpus','Ovary','Prostate','Larynx']
W={name:np.array([float(tbl.cell(r,c).text.strip())/100 for r in range(2,7)]) for c,name in enumerate(names,2)}
for n in names: assert abs(W[n].sum()-1)<1e-9

# ---------- KM 兩套實作 ----------
def km_own(months, event, t):
    """產品極限 KM（等同 R survfit / 舊 notebook），不外推：t 超過最後追蹤且 S>0 -> NaN。"""
    m=np.asarray(months,float); e=np.asarray(event,int)
    if len(m)==0: return math.nan
    o=np.argsort(m,kind='mergesort'); m,e=m[o],e[o]
    S=1.0; n=len(m); i=0; last=0.0
    while i<len(m):
        j=i
        while j<len(m) and m[j]==m[i]: j+=1
        d=int(e[i:j].sum())
        if d and n: S*=(n-d)/n
        last=m[i]; n-=(j-i); i=j
    # value at t = product over event times <= t
    m2=np.asarray(months,float); e2=np.asarray(event,int)
    o=np.argsort(m2,kind='mergesort'); m2,e2=m2[o],e2[o]
    S=1.0; n=len(m2); i=0
    while i<len(m2) and m2[i]<=t:
        j=i
        while j<len(m2) and m2[j]==m2[i]: j+=1
        d=int(e2[i:j].sum())
        if d and n: S*=(n-d)/n
        n-=(j-i); i=j
    if t>last and S>0: return math.nan
    return S

def km_ll(months, event, t):
    m=np.asarray(months,float); e=np.asarray(event,int)
    if len(m)==0: return math.nan
    f=KaplanMeierFitter().fit(m,e)
    ts=f.survival_function_.index.to_numpy(float); ss=f.survival_function_.iloc[:,0].to_numpy(float)
    if t>ts[-1] and ss[-1]>0: return math.nan
    return float(ss[np.searchsorted(ts,t,side='right')-1])

def life_cum(months,event,endmonth):
    """逐年(12月)精算生命表累積存活至 endmonth。"""
    m=np.asarray(months,float); e=np.asarray(event,int); cum=1.0
    for a in range(0,endmonth,12):
        b=a+12
        n=int((m>=a).sum())
        inside=(m>=a)&((m<=b) if b==endmonth else (m<b))
        death=int(e[inside].sum()); censor=int((inside).sum()-death)
        eff=n-censor/2
        p=1-death/eff if eff>0 else math.nan
        if n==0 or (m.max()<b and cum!=0): cum=math.nan
        elif cum==0: pass
        else: cum*=p
    return cum

# ================= Q6 口腔癌 =================
P('\n================ Q6 口腔癌(Oral cavity) 108-112 ================')
oral=raw[(raw.pri_site=='Oral cavity')&(raw.year.between(108,112))].copy()
P('口腔癌 108-112 筆數 =', len(oral), ' 死亡 =', int(oral.event.sum()), ' 設限 =', int((oral.event==0).sum()))
P('未加權 5年: KM(自寫)=%.4f  KM(lifelines)=%.4f  生命表=%.4f'%(
    km_own(oral.Surv_Months,oral.event,60)*100, km_ll(oral.Surv_Months,oral.event,60)*100, life_cum(oral.Surv_Months,oral.event,60)*100))

edges=[15,45,55,65,75,math.inf]; w=W['Oral cavity']
P('\n-- 逐年齡層 (Word 權重) --')
P('層 | 年齡 | Word權重 | 人數 | 死亡 | 5年KM')
layers=[]
for k,(a,b) in enumerate(zip(edges[:-1],edges[1:])):
    g=oral[(oral.age>=a)&(oral.age<b)]
    s=km_own(g.Surv_Months,g.event,60)
    layers.append({'lo':a,'hi':b,'w':w[k],'n':len(g),'d':int(g.event.sum()),'s5':s,'df':g})
    P('%d | %s-%s | %.3f | %d | %d | %s'%(k+1,a,('inf' if b==math.inf else int(b)),w[k],len(g),int(g.event.sum()),('%.4f'%s if not math.isnan(s) else 'NA')))

# 併組 <10（Word：上下相鄰，較小者；本程式假設 tie 取下方=較年輕側）
def merge_layers(lst):
    g=[dict(x) for x in lst]
    while len(g)>1 and any(x['n']<10 for x in g):
        i=next(i for i,x in enumerate(g) if x['n']<10)
        j=1 if i==0 else (len(g)-2 if i==len(g)-1 else (i-1 if g[i-1]['n']<=g[i+1]['n'] else i+1))
        lo,hi=min(i,j),max(i,j)
        g[lo]={'lo':g[lo]['lo'],'hi':g[hi]['hi'],'w':g[lo]['w']+g[hi]['w'],
               'df':pd.concat([g[lo]['df'],g[hi]['df']])}
        g[lo]['n']=len(g[lo]['df']); g[lo]['d']=int(g[lo]['df'].event.sum())
        g.pop(hi)
    return g
mg=merge_layers(layers)
P('\n-- 併組後 (Word 權重) --')
P('年齡 | 權重 | 人數 | 5年KM | 加權貢獻')
tot=0; ok=True
for x in mg:
    s=km_own(x['df'].Surv_Months,x['df'].event,60)
    contrib=x['w']*s if not math.isnan(s) else math.nan
    if math.isnan(s): ok=False
    tot+=contrib if not math.isnan(contrib) else 0
    P('%s-%s | %.3f | %d | %s | %s'%(x['lo'],('inf' if x['hi']==math.inf else int(x['hi'])),x['w'],x['n'],
        ('%.4f'%s if not math.isnan(s) else 'NA'),('%.4f'%contrib if not math.isnan(contrib) else 'NA')))
P('Word 權重年齡調整 5年 OS = %.4f%%  (官方回饋 62.03%%)'%(tot*100 if ok else math.nan))

# 本院權重（舊 notebook 法：以本院年齡層佔比為權重，無併組，S_at 會外推）
def km_extrap(months,event,t):
    m=np.asarray(months,float); e=np.asarray(event,int)
    if len(m)==0: return math.nan
    o=np.argsort(m,kind='mergesort'); m,e=m[o],e[o]
    S=1.0; n=len(m); i=0
    while i<len(m) and m[i]<=t:
        j=i
        while j<len(m) and m[j]==m[i]: j+=1
        d=int(e[i:j].sum())
        if d and n: S*=(n-d)/n
        n-=(j-i); i=j
    return S  # 不設 NaN -> 等於把最後一段水平延伸
def age_band_old(a):
    a=int(a)
    return 0 if a<45 else 1 if a<55 else 2 if a<65 else 3 if a<75 else 4
oral2=oral.dropna(subset=['age']).copy()
oral2['band']=oral2.age.apply(age_band_old)
hw=oral2.band.value_counts(normalize=True).sort_index()
P('\n-- 本院權重法(舊 notebook) --')
acc=0; wsum=0
P('層 | 本院權重 | 人數 | 5年KM(外推)')
for bnd in range(5):
    sub=oral2[oral2.band==bnd]
    wv=hw.get(bnd,0.0)
    if len(sub)<1 or wv==0: continue
    s=km_extrap(sub.Surv_Months,sub.event,60)
    acc+=wv*s; wsum+=wv
    P('%d | %.4f | %d | %.4f'%(bnd,wv,len(sub),s))
P('本院權重年齡調整 5年 OS = %.4f%%  (舊 notebook 約 57.21%%)'%(acc/wsum*100 if wsum>0 else math.nan))

# ================= Q3 端點敏感度 =================
P('\n================ Q3 Surv_Months vs (迄日-起日)/30.5 端點 ================')
def parse8(s):
    s=str(s).strip().split('.')[0]
    if len(s)<8 or not s[:8].isdigit(): return pd.NaT
    y,m,d=s[:4],s[4:6],s[6:8]
    if d=='99': d='15'
    if m=='99': m,d='07','01'
    try: return pd.Timestamp(f'{y}-{m}-{d}')
    except ValueError: return pd.NaT
r3=raw.dropna(subset=['Surv_Months','event']).copy()
r3['start']=r3.didiag.apply(parse8)
r3['end']=np.where(r3.event.eq(1), r3.death_d.apply(parse8).values, pd.Timestamp('2025-12-31'))
r3['end']=pd.to_datetime(r3['end'])
r3['m_recalc']=(r3['end']-r3['start']).dt.days/30.5
bad=r3.m_recalc.isna().sum()
P('可重算日期筆數 =', int(r3.m_recalc.notna().sum()), ' 日期不可解析 =', int(bad))
d=r3.dropna(subset=['m_recalc'])
diff=(d.m_recalc-d.Surv_Months)
P('兩種月數差 (m_recalc - Surv_Months): 平均 %.3f 中位 %.3f 絕對值>0.1 筆數 %d  最大 %.2f'%(
    diff.mean(),diff.median(),int((diff.abs()>0.1).sum()),diff.abs().max()))
P('端點 | 跨端點不一致筆數 (一版>=t 另一版<t) | 佔比')
for t in [12,24,36,48,60]:
    a=d.Surv_Months>=t; b=d.m_recalc>=t
    flip=int((a!=b).sum())
    P('%d月 | %d | %.2f%%'%(t,flip,100*flip/len(d)))

# ================= Q5 Python(lifelines) vs R-equiv(自寫KM) =================
P('\n================ Q5 Python(lifelines) vs R-equiv(自寫KM) 全癌別×期別×年度 ================')
rows=[]; maxdiff=0; ndiff=0
for cancer in names:
    z=raw[raw.pri_site.eq(cancer)].copy()
    yrs=(111,112) if cancer=='Pancreas' else (110,112) if cancer=='Cervix' else (108,112)
    z=z[z.year.between(*yrs)]
    if len(z)==0: continue
    z['stage']=z.fnstage.str.extract(r'^([1-4])',expand=False).map({'1':'I','2':'II','3':'III','4':'IV'})
    for label,g in [('All',z)]+[('Stage '+i,z[z.stage.eq(i)]) for i in ['I','II','III','IV']]:
        if len(g)==0: continue
        for yi,t in enumerate([12,24,36,48,60],1):
            a=km_ll(g.Surv_Months,g.event,t); b=km_own(g.Surv_Months,g.event,t)
            av=math.nan if a is None else a; bv=math.nan if b is None else b
            dd=0 if (math.isnan(av) and math.isnan(bv)) else (abs(av-bv) if not(math.isnan(av) or math.isnan(bv)) else 9)
            if dd>1e-9: ndiff+=1; maxdiff=max(maxdiff,dd if dd<9 else maxdiff)
            rows.append([cancer,label,yi,len(g),av,bv,dd])
cmp=pd.DataFrame(rows,columns=['癌別','期別','年','人數','Python_KM','R_equiv_KM','差'])
cmp.to_csv(OUT/'Q5_python_vs_Requiv.csv',index=False,encoding='utf-8-sig')
P('比較格數 =', len(cmp), ' 不一致(>1e-9)格數 =', ndiff, ' 最大數值差 =', '%.2e'%maxdiff)
P('(R 未安裝於本機；R-equiv 為 verify_in_RStudio.R 同演算法之獨立 Python 產品極限實作)')

# 全癌別 All 5年：未加權 KM vs Word加權 vs 官方對照用
P('\n-- 各癌別 All 5年：未加權KM / Word加權 (供對照) --')
P('癌別 | 區間 | 人數 | 未加權5yKM% | Word加權5y% | 合併組數')
summ=[]
for cancer in names:
    z=raw[raw.pri_site.eq(cancer)].copy()
    yrs=(111,112) if cancer=='Pancreas' else (110,112) if cancer=='Cervix' else (108,112)
    z=z[z.year.between(*yrs)]
    if len(z)==0: continue
    unw=km_own(z.Surv_Months,z.event,60)
    ed=[15,55,65,75,85,math.inf] if cancer=='Prostate' else [15,45,55,65,75,math.inf]
    L=[]
    for k,(a,b) in enumerate(zip(ed[:-1],ed[1:])):
        gg=z[(z.age>=a)&(z.age<b)]; L.append({'lo':a,'hi':b,'w':W[cancer][k],'n':len(gg),'df':gg})
    mgc=merge_layers(L); valid=len(mgc)>1
    vals=[km_own(x['df'].Surv_Months,x['df'].event,60) for x in mgc]
    wadj=sum(x['w']*v for x,v in zip(mgc,vals)) if valid and all(x['n']>=10 and not math.isnan(v) for x,v in zip(mgc,vals)) else math.nan
    summ.append([cancer,'%d-%d'%yrs,len(z),unw*100,wadj*100 if not math.isnan(wadj) else math.nan,len(mgc)])
    P('%s | %s | %d | %.2f | %s | %d'%(cancer,'%d-%d'%yrs,len(z),unw*100,('%.2f'%(wadj*100) if not math.isnan(wadj) else 'NA'),len(mgc)))
pd.DataFrame(summ,columns=['癌別','區間','人數','未加權5yKM%','Word加權5y%','合併組數']).to_csv(OUT/'各癌別All_5年.csv',index=False,encoding='utf-8-sig')

open(OUT/'verify_log.txt','w',encoding='utf-8').write(log.getvalue())
P('\n輸出目錄:', OUT)
