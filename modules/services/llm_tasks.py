"""Background queue and JSONL history for dashboard LLM tasks."""
from __future__ import annotations
import json, os, shutil, time, traceback, uuid
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
def _rows(task_id, filename):
    path=_dir(task_id)/filename
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
def _row(cursor,row): return dict(zip([c[0] for c in cursor.description],row))
def _rewrite(task_id, filename, rows):
    path = _dir(task_id) / filename; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, default=str) + '\n' for row in rows), encoding='utf-8')

def create_llm_task(owner_id, task_type, payload):
    if task_type not in {'chart','compare','annual_report'}: raise ValueError('Unsupported LLM task type')
    task_id=str(uuid.uuid4()); payload=_safe(payload); progress_total=max(len(payload.get('items',[])),1) if task_type=='annual_report' else 1
    if task_type == 'annual_report':
        for item in payload.get('items', []):
            _write(task_id, 'input.jsonl', {
                'custom_id': item['item_id'], 'method': 'POST', 'url': '/v1/chat/completions',
                'body': {'task_type': 'chart_insight', 'payload': item}
            })
    else:
        _write(task_id,'input.jsonl',{'item_id':task_id,'task_type':task_type,'payload':payload,'created_at':datetime.now(timezone.utc).isoformat()})
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("""INSERT INTO dbo.LLMTaskWorker (TaskID,OwnerID,TaskType,Status,ProgressCurrent,ProgressTotal,AttemptCount,PayloadJson,CreatedAt,UpdatedAt) VALUES (?,?,?,'queued',0,?,0,?,SYSDATETIMEOFFSET(),SYSDATETIMEOFFSET())""",(task_id,str(owner_id),task_type,progress_total,json.dumps(payload,ensure_ascii=False,default=str))); conn.commit()
    finally: conn.close()
    return {'task_id':task_id,'status':'queued','progress_current':0,'progress_total':progress_total}

def _task(cursor,row):
    task=_row(cursor,row); payload=json.loads(task.pop('PayloadJson') or '{}')
    task['DocumentLabel']=payload.get('_document_label',''); task['TaskTitle']=payload.get('job_title') or payload.get('field_key') or payload.get('analysis_item') or 'LLM 分析'; task['result']=_rows(task['TaskID'],'output.jsonl'); return task

def get_llm_task_payload(task_id, owner_id):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("SELECT PayloadJson FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?",(str(task_id),str(owner_id))); row=cur.fetchone()
        return json.loads(row[0]) if row else None
    finally: conn.close()
def get_llm_task(task_id, owner_id):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("SELECT TaskID,TaskType,Status,ProgressCurrent,ProgressTotal,AttemptCount,ErrorMessage,CreatedAt,StartedAt,CompletedAt,UpdatedAt,PayloadJson FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?",(str(task_id),str(owner_id))); row=cur.fetchone()
        return _task(cur,row) if row else None
    finally: conn.close()

def list_llm_tasks(owner_id,limit=50):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("SELECT TOP (?) TaskID,TaskType,Status,ProgressCurrent,ProgressTotal,AttemptCount,ErrorMessage,CreatedAt,StartedAt,CompletedAt,UpdatedAt,PayloadJson FROM dbo.LLMTaskWorker WHERE OwnerID=? ORDER BY CreatedAt DESC",(min(max(int(limit),1),100),str(owner_id))); return [_task(cur,row) for row in cur.fetchall()]
    finally: conn.close()

def claim_next_llm_task(worker_id):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute(""";WITH candidate AS (SELECT TOP (1) * FROM dbo.LLMTaskWorker WITH (UPDLOCK,READPAST,ROWLOCK) WHERE (Status='queued' OR (Status='retrying' AND NextAttemptAt<=SYSDATETIMEOFFSET())) AND NOT EXISTS (SELECT 1 FROM dbo.LLMTaskWorker WITH (UPDLOCK,HOLDLOCK) WHERE Status='running') ORDER BY CreatedAt) UPDATE candidate SET Status='running',WorkerID=?,StartedAt=COALESCE(StartedAt,SYSDATETIMEOFFSET()),UpdatedAt=SYSDATETIMEOFFSET(),AttemptCount=AttemptCount+1 OUTPUT inserted.TaskID,inserted.TaskType,inserted.PayloadJson,inserted.AttemptCount;""",(worker_id,)); row=cur.fetchone(); conn.commit()
        return None if not row else {'task_id':str(row[0]),'task_type':row[1],'payload':json.loads(row[2]),'attempt_count':int(row[3])}
    finally: conn.close()

def _update(task_id,status=None,current=None,error=None):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("UPDATE dbo.LLMTaskWorker SET Status=COALESCE(?,Status),ProgressCurrent=COALESCE(?,ProgressCurrent),ErrorMessage=?,CompletedAt=CASE WHEN ? IN ('completed','partial_failed','failed') THEN SYSDATETIMEOFFSET() ELSE CompletedAt END,UpdatedAt=SYSDATETIMEOFFSET() WHERE TaskID=?",(status,current,error,status,task_id)); conn.commit()
    finally: conn.close()

def process_next_llm_task(worker_id):
    task=claim_next_llm_task(worker_id)
    if not task:return None
    try:
        if task['task_type']=='annual_report':
            failures=0
            retry_path = _dir(task['task_id']) / 'retry.jsonl'; retrying = retry_path.exists()
            requests = _rows(task['task_id'], 'retry.jsonl' if retrying else 'input.jsonl')
            for index, request in enumerate(requests, start=1):
                item = request['body']['payload']
                result=get_chart_insight_logic(item)
                output={'custom_id':request['custom_id'],'field_key':item.get('field_key',''),'result':result}
                if retrying: _rewrite(task['task_id'],'output.jsonl',[row for row in _rows(task['task_id'],'output.jsonl') if row.get('custom_id') != request['custom_id']] + [output])
                else: _write(task['task_id'],'output.jsonl',output)
                failures += not result.get('success'); _update(task['task_id'],current=len(_rows(task['task_id'],'output.jsonl')))
            if retrying: retry_path.unlink(missing_ok=True)
            failures=sum(not row.get('result',{}).get('success') for row in _rows(task['task_id'],'output.jsonl'))
            status='partial_failed' if failures else 'completed'; _update(task['task_id'],status=status,error=f'{failures} failed insight(s)' if failures else None); return {'task_id':task['task_id'],'status':status}
        handler=get_chart_insight_logic if task['task_type']=='chart' else get_compare_insight_logic; result=handler(task['payload'])
        if not result.get('success'): raise RuntimeError(str(result.get('error') or 'LLM did not return a result'))
        _write(task['task_id'],'output.jsonl',{'item_id':task['task_id'],'result':result}); _update(task['task_id'],status='completed',current=1); return {'task_id':task['task_id'],'status':'completed'}
    except Exception as exc:
        error=str(exc); _write(task['task_id'],'error.jsonl',{'item_id':task['task_id'],'error_type':type(exc).__name__,'error':error,'traceback':traceback.format_exc(),'failed_at':datetime.now(timezone.utc).isoformat()}); _update(task['task_id'],status='failed',error=error); return {'task_id':task['task_id'],'status':'failed'}

def requeue_annual_report_item(task_id, owner_id, item_id):
    task_id, item_id = str(task_id), str(item_id)
    conn = get_conn()
    try:
        cur=conn.cursor(); cur.execute("SELECT TaskType,Status FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?",(task_id,str(owner_id))); row=cur.fetchone()
        if not row or row[0] != 'annual_report' or row[1] not in {'completed','partial_failed','failed'}: return False
        request=next((entry for entry in _rows(task_id,'input.jsonl') if entry.get('custom_id') == item_id),None)
        if not request: return False
        _rewrite(task_id,'retry.jsonl',[request]); _rewrite(task_id,'output.jsonl',[entry for entry in _rows(task_id,'output.jsonl') if entry.get('custom_id') != item_id])
        cur.execute("UPDATE dbo.LLMTaskWorker SET Status='queued',ProgressCurrent=?,ErrorMessage=NULL,WorkerID=NULL,NextAttemptAt=SYSDATETIMEOFFSET(),StartedAt=NULL,CompletedAt=NULL,UpdatedAt=SYSDATETIMEOFFSET() WHERE TaskID=? AND OwnerID=?",(len(_rows(task_id,'output.jsonl')),task_id,str(owner_id))); conn.commit(); return cur.rowcount == 1
    finally: conn.close()
def recover_running_llm_tasks():
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("UPDATE dbo.LLMTaskWorker SET Status='retrying',WorkerID=NULL,NextAttemptAt=SYSDATETIMEOFFSET(),UpdatedAt=SYSDATETIMEOFFSET() WHERE Status='running'"); conn.commit(); return cur.rowcount
    finally: conn.close()
def run_worker(worker_id=None,poll_seconds=2):
    worker_id=worker_id or f"{os.environ.get('COMPUTERNAME','worker')}-{os.getpid()}"; recover_running_llm_tasks()
    while True: process_next_llm_task(worker_id); time.sleep(poll_seconds)
def delete_llm_task(task_id,owner_id):
    conn=get_conn()
    try:
        cur=conn.cursor(); cur.execute("DELETE FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?",(task_id,str(owner_id))); conn.commit(); deleted=cur.rowcount>0
        if deleted: shutil.rmtree(_dir(task_id),ignore_errors=True)
        return deleted
    finally: conn.close()