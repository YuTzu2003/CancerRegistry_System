# Open this script in RStudio, then click Source. Select original full case list.
for(p in c('readxl','survival','ggplot2')) if(!requireNamespace(p,quietly=TRUE)) install.packages(p,repos='https://cloud.r-project.org')
library(readxl);library(survival);library(ggplot2)
input <- file.choose() # select 2026存活率個案清單(3).xlsx, NOT a zip or .R file
stopifnot(tolower(tools::file_ext(input))=='xlsx')
raw <- as.data.frame(read_excel(input,sheet='LF_8',col_types='text'))
stopifnot(all(c('select_memo','pri_site','year','age','fnstage','didiag','death_d','Status_OS','Surv_Months') %in% names(raw)))
raw <- raw[trimws(raw$select_memo)=='15_納入統計人數',,drop=FALSE]
raw$months<-as.numeric(raw$Surv_Months);raw$age_num<-as.numeric(raw$age)
raw$event<-match(tolower(trimws(raw$Status_OS)),c('censor','death'))-1L
if(anyNA(raw$months)|anyNA(raw$event)|anyNA(raw$age_num)|any(raw$months<0)) stop('Check months, age, and status')
raw$year_num<-as.integer(raw$year)
raw$stage<-c('I','II','III','IV')[match(substr(raw$fnstage,1,1),as.character(1:4))]
weights<-read.csv('官方標準權重.csv',fileEncoding='UTF-8-BOM')
dir.create('R_驗證輸出',showWarnings=FALSE)

km <- function(d,times=c(12,24,36,48,60)) {
 if(nrow(d)==0) return(rep(NA_real_,length(times)))
 fit<-survfit(Surv(months,event)~1,data=d)
 v<-rep(NA_real_,length(times))
 for(i in seq_along(times)) {
   t<-times[i]
   ix<-which(fit$time<=t)
   if(t>max(d$months) && !any(fit$surv[ix]==0)) next
   v[i]<-if(length(ix))fit$surv[tail(ix,1)] else 1
 }
 v
}
life<-function(d) {
 acc<-1;ans<-list()
 for(a in seq(0,48,12)) {
   b<-a+12
   inside<-d$months>=a & if(b==60) d$months<=b else d$months<b
   n<-sum(d$months>=a);deaths<-sum(inside & d$event==1);censored<-sum(inside & d$event==0)
   effective<-n-censored/2
   p<-if(effective>0) 1-deaths/effective else NA_real_
   if(n==0 || (max(d$months)<b && !isTRUE(acc==0))) acc<-NA_real_
   else if(!isTRUE(acc==0)) acc<-acc*p
   ans[[length(ans)+1]]<-data.frame(start_month=a,end_month=b,entering=n,deaths=deaths,censored=censored,effective=effective,interval_survival=p,cumulative=acc)
 }
 do.call(rbind,ans)
}
merge_age<-function(d,cancer,w) {
 edges<-if(cancer=='Prostate')c(15,55,65,75,85,Inf) else c(15,45,55,65,75,Inf)
 g<-lapply(1:5,function(i) list(lo=edges[i],hi=edges[i+1],weight=w[i],d=d[d$age_num>=edges[i]&d$age_num<edges[i+1],,drop=FALSE]))
 while(length(g)>1 && any(vapply(g,function(x)nrow(x$d)<10,logical(1)))) {
  i<-which(vapply(g,function(x)nrow(x$d)<10,logical(1)))[1]
  j<-if(i==1)2 else if(i==length(g))i-1 else if(nrow(g[[i-1]]$d)<=nrow(g[[i+1]]$d))i-1 else i+1
  lo<-min(i,j);hi<-max(i,j)
  g[[lo]]<-list(lo=g[[lo]]$lo,hi=g[[hi]]$hi,weight=g[[lo]]$weight+g[[hi]]$weight,d=rbind(g[[lo]]$d,g[[hi]]$d))
  g<-g[-hi]
 }
 g
}
sumrows<-list();lifrows<-list();stdrows<-list();agerows<-list()
for(cancer in unique(raw$pri_site)) {
 d<-raw[raw$pri_site==cancer,,drop=FALSE]
 years<-if(cancer=='Pancreas')111:112 else if(cancer=='Cervix')110:112 else 108:112
 d<-d[d$year_num %in% years,,drop=FALSE]
 if(!nrow(d))next
 tag<-gsub('[^A-Za-z0-9]+','_',cancer)
 groups<-c(list(All=d),setNames(lapply(c('I','II','III','IV'),function(s)d[!is.na(d$stage)&d$stage==s,,drop=FALSE]),paste('Stage',c('I','II','III','IV'))))
 plotlist<-list()
 for(label in names(groups)) {
  z<-groups[[label]];v<-km(z)
  sumrows[[length(sumrows)+1]]<-data.frame(cancer=cancer,stage=label,n=nrow(z),year=1:5,OS=v)
  if(!nrow(z))next
  x<-life(z);x$cancer<-cancer;x$stage<-label;lifrows[[length(lifrows)+1]]<-x
  if(label!='All'){
   f<-survfit(Surv(months,event)~1,data=z)
   plotlist[[label]]<-data.frame(year=c(0,f$time)/12,survival=c(1,f$surv),stage=label)
  }
  ww<-weights$weight[weights$cancer==cancer]
  stopifnot(length(ww)==5,abs(sum(ww)-1)<1e-8)
  g<-merge_age(z,cancer,ww)
  mat<-do.call(rbind,lapply(g,function(a) km(a$d)))
  adjusted<-if(length(g)==1) rep(NA_real_,5) else vapply(1:5,function(t) if(anyNA(mat[,t])) NA_real_ else sum(vapply(g,`[[`,numeric(1),'weight')*mat[,t]),numeric(1))
  stdrows[[length(stdrows)+1]]<-data.frame(cancer=cancer,stage=label,n=nrow(z),merged_groups=length(g),year=1:5,age_adjusted_OS=adjusted)
  for(k in seq_along(g))agerows[[length(agerows)+1]]<-data.frame(cancer=cancer,stage=label,age_start=g[[k]]$lo,age_end_exclusive=g[[k]]$hi,n=nrow(g[[k]]$d),weight=g[[k]]$weight,year=1:5,OS=mat[k,],weighted_contribution=g[[k]]$weight*mat[k,])
 }
 if(length(plotlist)){
   p<-ggplot(do.call(rbind,plotlist),aes(year,survival,color=stage))+geom_step(direction='hv')+coord_cartesian(xlim=c(0,5),ylim=c(0,1))+theme_bw()+labs(title=paste(cancer,'KM'),x='Years',y='Overall survival')
   ggsave(file.path('R_驗證輸出',paste0(tag,'_KM.png')),p,width=8,height=5)
 }
}
write.csv(do.call(rbind,sumrows),'R_驗證輸出/KM_年度.csv',row.names=FALSE,fileEncoding='UTF-8')
write.csv(do.call(rbind,lifrows),'R_驗證輸出/生命表.csv',row.names=FALSE,fileEncoding='UTF-8')
write.csv(do.call(rbind,stdrows),'R_驗證輸出/年齡標準化.csv',row.names=FALSE,fileEncoding='UTF-8')
write.csv(do.call(rbind,agerows),'R_驗證輸出/年齡層明細.csv',row.names=FALSE,fileEncoding='UTF-8')
print(subset(do.call(rbind,stdrows),stage=='All' & year==5,c('cancer','n','age_adjusted_OS')))
message('完成：R_驗證輸出')
