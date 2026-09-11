"""Background queue and JSONL history for dashboard LLM tasks."""
from __future__ import annotations
import json, os, time, traceback, uuid
from datetime import datetime, timezone
from pathlib import Path
from modules.blueprint.dashboard.reply import get_chart_insight_logic, get_compare_insight_logic
from modules.services.db import get_conn

TASK_ROOT = Path(__file__).resolve().parents[2] / 'tasks' / 'llm_tasks'
SENSITIVE_KEYS = {'api_key','authorization','password','token','patient_name','patient_id','medical_record_number'}

def _safe(value):
    if isinstance(value, dict): return {str(k): _safe(v) for k,v in value.items() if str(k).lower().replace('-','_') not in SENSITIVE_KEYS}
    if isinstance(value, list): return [_safe(v) for v in value]
    return value

def _dir(task_id): return TASK_ROOT / str(task_id)
def _write(task_id, filename, row):
    _dir(task_id).mkdir(parents=True, exist_ok=True)
    with (_dir(task_id)/filename).open('a', encoding='utf-8') as f: f.write(json.dumps(row, ensure_ascii=False, default=str)+'\n')
def _result(task_id):
    path=_dir(task_id)/'output.jsonl'
    if not path.exists(): return None
    rows=path.read_text(encoding='utf-8').splitlines()
    return json.loads(rows[-1]).get('result') if rows else None
def _row(cursor,row): return dict(zip([c[0] for c in cursor.description],row))

def create_llm_task(owner_id, task_type, payload):
    if task_type not in {'chart','compare'}: raise ValueError('Unsupported LLM task type')
    task_id=str(uuid.uuid4()); payload=_safe(payload)
    _write(task_id,'input.jsonl',{'item_id':task_id,'task_type':task_type,'payload':payload,'created_at':datetime.now(timezone.utc).isoformat()})
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("""INSERT INTO dbo.LLMTaskWorker (TaskID,OwnerID,TaskType,Status,ProgressCurrent,ProgressTotal,AttemptCount,PayloadJson,CreatedAt,UpdatedAt) VALUES (?,?,?,'queued',0,1,0,?,SYSDATETIMEOFFSET(),SYSDATETIMEOFFSET())""",(task_id,str(owner_id),task_type,json.dumps(payload,ensure_ascii=False,default=str))); conn.commit()
    finally: conn.close()
    return {'task_id':task_id,'status':'queued','progress_current':0,'progress_total':1}

def get_llm_task(task_id, owner_id):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("""SELECT TaskID,TaskType,Status,ProgressCurrent,ProgressTotal,AttemptCount,ErrorMessage,CreatedAt,StartedAt,CompletedAt,UpdatedAt,PayloadJson FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?""",(str(task_id),str(owner_id))); row=cur.fetchone()
        if not row:return None
        task=_row(cur,row); payload=json.loads(task.pop('PayloadJson') or '{}'); task['DocumentLabel']=payload.get('_document_label',''); task['TaskTitle']=payload.get('field_key') or payload.get('analysis_item') or 'LLM 分析'; task['result']=_result(task_id); return task
    finally: conn.close()

def list_llm_tasks(owner_id,limit=50):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("""SELECT TOP (?) TaskID,TaskType,Status,ProgressCurrent,ProgressTotal,AttemptCount,ErrorMessage,CreatedAt,StartedAt,CompletedAt,UpdatedAt,PayloadJson FROM dbo.LLMTaskWorker WHERE OwnerID=? ORDER BY CreatedAt DESC""",(min(max(int(limit),1),100),str(owner_id))); tasks=[]
        for row in cur.fetchall():
            task=_row(cur,row); payload=json.loads(task.pop('PayloadJson') or '{}'); task['DocumentLabel']=payload.get('_document_label',''); task['TaskTitle']=payload.get('field_key') or payload.get('analysis_item') or 'LLM 分析'; task['result']=_result(task['TaskID']); tasks.append(task)
        return tasks
    finally: conn.close()

def claim_next_llm_task(worker_id):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute(""";WITH candidate AS (SELECT TOP (1) * FROM dbo.LLMTaskWorker WITH (UPDLOCK,READPAST,ROWLOCK) WHERE (Status='queued' OR (Status='retrying' AND NextAttemptAt<=SYSDATETIMEOFFSET())) AND NOT EXISTS (SELECT 1 FROM dbo.LLMTaskWorker WITH (UPDLOCK,HOLDLOCK) WHERE Status='running') ORDER BY CreatedAt) UPDATE candidate SET Status='running',WorkerID=?,StartedAt=COALESCE(StartedAt,SYSDATETIMEOFFSET()),UpdatedAt=SYSDATETIMEOFFSET(),AttemptCount=AttemptCount+1 OUTPUT inserted.TaskID,inserted.TaskType,inserted.PayloadJson,inserted.AttemptCount;""",(worker_id,)); row=cur.fetchone(); conn.commit()
        return None if not row else {'task_id':str(row[0]),'task_type':row[1],'payload':json.loads(row[2]),'attempt_count':int(row[3])}
    finally: conn.close()

def _finish(task_id,status,error=None):
    conn=get_conn()
    try:
        cur=conn.cursor();cur.execute("""UPDATE dbo.LLMTaskWorker SET Status=?,ProgressCurrent=1,ErrorMessage=?,CompletedAt=CASE WHEN ? IN ('completed','failed') THEN SYSDATETIMEOFFSET() ELSE NULL END,UpdatedAt=SYSDATETIMEOFFSET() WHERE TaskID=?""",(status,error,status,task_id));conn.commit()
    finally: conn.close()

def process_next_llm_task(worker_id):
    task=claim_next_llm_task(worker_id)
    if not task:return None
    try:
        handler=get_chart_insight_logic if task['task_type']=='chart' else get_compare_insight_logic; result=handler(task['payload'])
        if not result.get('success'): raise RuntimeError(str(result.get('error') or 'LLM did not return a result'))
        _write(task['task_id'],'output.jsonl',{'item_id':task['task_id'],'result':result,'completed_at':datetime.now(timezone.utc).isoformat()});_finish(task['task_id'],'completed');return {'task_id':task['task_id'],'status':'completed'}
    except Exception as exc:
        error=str(exc);_write(task['task_id'],'error.jsonl',{'item_id':task['task_id'],'error_type':type(exc).__name__,'error':error,'traceback':traceback.format_exc(),'failed_at':datetime.now(timezone.utc).isoformat()})
        if task['attempt_count']<3:
            conn=get_conn()
            try:
                cur=conn.cursor();cur.execute("UPDATE dbo.LLMTaskWorker SET Status='retrying',ErrorMessage=?,NextAttemptAt=DATEADD(second,15*AttemptCount,SYSDATETIMEOFFSET()),UpdatedAt=SYSDATETIMEOFFSET() WHERE TaskID=?",(error,task['task_id']));conn.commit()
            finally:conn.close()
            return {'task_id':task['task_id'],'status':'retrying'}
        _finish(task['task_id'],'failed',error);return {'task_id':task['task_id'],'status':'failed'}

def run_worker(worker_id=None,poll_seconds=2):
    worker_id=worker_id or f"{os.environ.get('COMPUTERNAME','worker')}-{os.getpid()}"
    while True: process_next_llm_task(worker_id); time.sleep(poll_seconds)
def delete_llm_task(task_id, owner_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dbo.LLMTaskWorker WHERE TaskID = ? AND OwnerID = ?", (task_id, str(owner_id)))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
