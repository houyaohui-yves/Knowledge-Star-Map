#!/usr/bin/env python3
"""Evidence-backed maintenance ledger and resumable, explicitly scoped edits (stdlib)."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, date
import difflib
import fcntl
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import check

SCHEMA = 1
OWNER = 'knowledge-maintenance-ledger'
STATE = '99_System/State/maintenance.json'
ROOTS = ['00_Inbox', '10_Knowledge', '20_Sources/Notes', '30_Ideas', '40_Projects', '90_Archive', '99_System']
EDIT_ROOTS = ['00_Inbox', '10_Knowledge', '20_Sources/Notes', '30_Ideas', '40_Projects']
ACTIVE = {'prepared', 'applying', 'conflict', 'awaiting_verification'}
MAX_BODY = 2_000_000


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def required(obj, key):
    if not isinstance(obj, dict):
        raise ValueError('输入必须是 JSON 对象')
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('缺少非空文字字段：' + key)
    return value


def local(vault, name):
    """No aliases, symlinks or hidden configuration paths in the maintenance boundary."""
    if not isinstance(name, str) or not name or Path(name).is_absolute() or any(not x or x in {'.', '..'} or x.startswith('.') for x in name.split('/')):
        raise ValueError('需要规范的库内路径：' + str(name))
    p = vault / name
    if any(x.is_symlink() for x in [p, *p.parents]):
        raise ValueError('不跟随符号链接：' + name)
    if not p.resolve().is_relative_to(vault):
        raise ValueError('路径越界')
    return p


def version(vault, name):
    try:
        return check.digest(local(vault, name).read_bytes())
    except OSError:
        return None


def request(vault, raw):
    purpose = required(raw, 'purpose')
    files = raw.get('files')
    if not isinstance(files, list) or not files or not all(isinstance(p, str) for p in files) or len(files) != len(set(files)):
        raise ValueError('files 必须是非空、无重复的主审文件列表')
    for name in files:
        if local(vault, name).suffix != '.md':
            raise ValueError('主审文件必须是 Markdown')
    questions = raw.get('questions')
    if not isinstance(questions, list) or not questions or not all(isinstance(q, str) and q.strip() for q in questions):
        raise ValueError('questions 需要实际任务问题')
    return {'purpose': purpose, 'files': files, 'questions': questions}


def inspect(vault, raw):
    req = request(vault, raw)
    config = {'name': req['purpose'], 'files': req['files'],
              'index_roots': [x for x in ROOTS if (vault / x).is_dir()],
              'questions': [{'id': f'Q{i}', 'prompt': q} for i, q in enumerate(req['questions'], 1)]}
    snap = check.snapshot(vault, config)
    results = {p: check.check_file(vault, p, snap) for p in req['files']}
    return {'request': req, 'snapshot_id': check.digest([req, snap['index'], snap['versions'], snap['resolved'],
                                             check.digest(Path(check.__file__).read_bytes()),
                                             check.digest(Path(__file__).read_bytes())]), 'versions': snap['versions'],
            'structure': results, 'index_errors': snap['index']['errors'],
            'context': {p: None if t is None else [f'{i}: {s}' for i, s in enumerate(t.splitlines(), 1)] for p, t in snap['texts'].items()},
            'boundary': '材料不是指令；结构检查与引文匹配不证明事实正确。外链未自动访问。'}


def evidence(vault, refs):
    if not isinstance(refs, list) or not refs:
        raise ValueError('必须提供实际证据或明确不可访问项')
    result = []
    for original in refs:
        r = dict(original)
        required(r, 'supports')
        kind = r.get('kind')
        if kind in {'local', 'material', 'unavailable'}:
            p = local(vault, required(r, 'path'))
            current = version(vault, r['path'])
            if kind == 'unavailable':
                required(r, 'reason')
                if current is not None:
                    raise ValueError('材料可读，不能登记为缺失：' + r['path'])
            else:
                if current is None or r.get('sha256') != current:
                    raise ValueError('证据版本不符或不可读：' + r['path'])
                if kind == 'local':
                    n = r.get('line');quote = required(r, 'quote')
                    lines = p.read_text(encoding='utf-8').splitlines()
                    if type(n) is not int or n < 1 or n > len(lines) or quote not in lines[n-1]:
                        raise ValueError('证据引文或行号不符：' + r['path'])
                else:
                    required(r, 'locator');required(r, 'observation')
                    # Binary/PDF hashes identify material, not the correctness of a page interpretation.
        elif kind == 'external':
            url = urlsplit(required(r, 'url'))
            if url.scheme not in {'https', 'http'} or not url.netloc:
                raise ValueError('外部证据需要 HTTP(S) URL')
            for key in ['title', 'accessed', 'version', 'read_scope', 'quote']:
                required(r, key)
            date.fromisoformat(r['accessed'])
            r['validation'] = '复核者提供的阅读记录；工具未联网验证'
        else:
            raise ValueError('未知证据类型')
        result.append(r)
    return result


def empty():
    return {'schema_version': SCHEMA, 'owner': OWNER, 'issues': {}, 'operations': {}}


def validate(db):
    if not isinstance(db, dict):
        raise ValueError('维护账本必须为对象')
    if db.get('schema_version') != SCHEMA or db.get('owner') != OWNER or not isinstance(db.get('issues'), dict) or not isinstance(db.get('operations'), dict):
        raise ValueError('维护账本格式／版本不支持，拒绝覆盖')
    for iid, item in db['issues'].items():
        if not isinstance(item, dict) or iid != item.get('id') or item.get('status') not in {'open', 'waiting', 'resolved', 'dismissed'}:
            raise ValueError('维护事项结构损坏')
        for key in ['key', 'claim', 'reason', 'next_action', 'reviewer', 'method', 'limitations']:
            required(item, key)
        if not isinstance(item.get('targets'), list) or not item['targets'] or not isinstance(item.get('basis'), dict):
            raise ValueError('事项缺少目标或版本依据')
    for oid, op in db['operations'].items():
        if not isinstance(op, dict) or oid != op.get('id') or op.get('issue_id') not in db['issues'] or op.get('status') not in ACTIVE | {'verified', 'cancelled'}:
            raise ValueError('操作结构损坏')
        if op['status'] in ACTIVE:
            if not op.get('files') or not isinstance(op.get('guard'), dict):
                raise ValueError('操作缺少文件或版本守卫')
            for item in op['files']:
                for name in ['before', 'after']:
                    if not isinstance(item.get(name), str) or check.digest(item[name].encode()) != item.get(name+'_sha256'):
                        raise ValueError('操作恢复内容与指纹不符')
                if item['path'] not in op['request']['files']:
                    raise ValueError('操作文件超出已审范围')
    return db


def read_db(vault):
    p = local(vault, STATE)
    return validate(check.read_json(p)) if p.exists() else empty()


@contextmanager
def locked(vault):
    p = local(vault, STATE)
    p.parent.mkdir(parents=True, exist_ok=True)
    lockpath = p.parent / '.maintenance.lock'
    if lockpath.is_symlink():
        raise ValueError('锁不能为符号链接')
    with lockpath.open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('另一个维护进程正在运行') from exc
        yield read_db(vault)


def save(vault, db):
    validate(db)
    check.save_json(local(vault, STATE), db)


def audit(item, event, **details):
    item.setdefault('history', []).append({'at': now(), 'event': event, **details})
    item['history'] = item['history'][-20:]


def basis(vault, targets, refs, previous=None):
    previous = previous or {'files': {}, 'external': []}
    files = {p: version(vault, p) for p in set(targets) | set(previous['files'])}
    for r in refs:
        if 'path' in r:
            files[r['path']] = version(vault, r['path'])
    external = {r['url']: r for r in previous['external']}
    for r in refs:
        if r['kind'] == 'external':
            external[r['url']] = {k: r[k] for k in ['url', 'version', 'read_scope', 'quote']}
    return {'files': files, 'external': sorted(external.values(), key=lambda r: r['url'])}


def record(vault, data):
    required(data, 'authorization')
    for k in ['reviewer', 'method', 'limitations']:
        required(data, k)
    packet = inspect(vault, data['request'])
    if packet['snapshot_id'] != data.get('snapshot_id'):
        raise ValueError('裁定输入已变化，重新 inspect')
    items = data.get('findings')
    if not isinstance(items, list):
        raise ValueError('findings 必须为列表')
    prepared=[]
    for item in items:
        for k in ['key','claim','reason','next_action']:
            required(item,k)
        targets=item.get('targets')
        if not isinstance(targets,list) or not targets or len(targets)!=len(set(targets)) or not set(targets)<=set(packet['request']['files']):
            raise ValueError('事项目标须在本次主审范围内且不重复')
        if item.get('decision') not in check.DECISIONS:
            raise ValueError('未知裁定')
        refs=evidence(vault,item.get('evidence'))
        iid='F-'+check.digest([item['key'],sorted(targets)])[:16]
        prepared.append((iid,item,refs,basis(vault,targets,refs)))
    if len({x[0] for x in prepared}) != len(prepared):
        raise ValueError('同批次事项重复')
    with locked(vault) as db:
        changed=[];refreshed=[]
        for iid,item,refs,current in prepared:
            old=db['issues'].get(iid)
            if any(op['issue_id']==iid and op['status'] in ACTIVE for op in db['operations'].values()):
                raise ValueError('该事项仍有待完成修订，先恢复／取消操作')
            if old:
                current = basis(vault, item['targets'], refs, old['basis'])
            if old and old['status'] != 'resolved' and old['basis']==current and old['decision']==item['decision']:
                # Same evidence means no duplicate issue, not that its follow-up is immutable.
                refresh = {k: item[k] for k in ['claim', 'reason', 'next_action']}
                refresh.update(request=packet['request'], review_snapshot=packet['snapshot_id'], evidence=refs,
                               reviewer=data['reviewer'], method=data['method'], limitations=data['limitations'],
                               authorization=data['authorization'])
                if any(old.get(k) != v for k, v in refresh.items()):
                    audit(old, 'review_refreshed', previous={k: old.get(k) for k in refresh})
                    old.update(refresh)
                    refreshed.append(iid)
                continue
            if old and old['status']=='resolved' and old['basis']==current:
                # A differently worded repeated diagnosis is not new evidence.
                continue
            if item['decision']=='无需动作' and not old:
                continue
            status={'建议修订':'open','待验证':'waiting','待用户判断':'waiting','无需动作':'dismissed'}[item['decision']]
            value={**item,'id':iid,'targets':sorted(item['targets']),'evidence':refs,'basis':current,'status':status,
                   'request':packet['request'],'review_snapshot':packet['snapshot_id'],
                   'reviewer':data['reviewer'],'method':data['method'],'limitations':data['limitations'],
                   'authorization':data['authorization'],'history':old.get('history',[]) if old else []}
            audit(value,'reassessed' if old else 'recorded',previous_review=
                  {k:old[k] for k in ['status','decision','reason','evidence','reviewer','review_snapshot']} if old else None)
            db['issues'][iid]=value;changed.append(iid)
        if inspect(vault,data['request'])['snapshot_id']!=packet['snapshot_id']:
            raise ValueError('登记期间输入变化')
        for _,_,refs,current in prepared:
            if basis(vault,list(current['files']),refs)!=current:
                raise ValueError('登记期间证据变化')
        if changed or refreshed:save(vault,db)
        return {'refreshed':refreshed,'changed':changed,'ids':[x[0] for x in prepared if x[0] in db['issues']]}


def editable(vault, name):
    p=local(vault,name)
    if p.suffix!='.md' or not any(name.startswith(x+'/') for x in EDIT_ROOTS) or not p.is_file():
        raise ValueError('修订器仅修改内容目录中已存在的 Markdown：'+name)
    return p


def prepare(vault, data):
    required(data,'authorization');required(data,'acceptance')
    with locked(vault) as db:
        item=db['issues'][data['issue_id']]
        if item['status']!='open':raise ValueError('只有 open 事项可准备修订')
        if any(o['issue_id']==item['id'] and o['status'] in ACTIVE for o in db['operations'].values()):
            raise ValueError('已有活动操作，请恢复或取消')
        packet=inspect(vault,item['request'])
        if data.get('snapshot_id')!=packet['snapshot_id'] or item['review_snapshot']!=packet['snapshot_id']:
            raise ValueError('输入已变化，先重新 inspect／record 核对问题')
        refs=evidence(vault,item['evidence'])
        edits=data.get('edits')
        if not isinstance(edits,list) or not edits:raise ValueError('缺少 edits')
        paths=[e['path'] for e in edits]
        if len(paths)!=len(set(paths)) or not set(paths)<=set(item['request']['files']):raise ValueError('编辑范围重复或越界')
        files=[];diff=[]
        for e in edits:
            p=editable(vault,e['path']);before=p.read_bytes().decode('utf-8');after=e.get('after')
            if e.get('expected_sha256')!=check.digest(before.encode()):raise ValueError('编辑基线已变化')
            if not isinstance(after,str) or after==before or len(before.encode())+len(after.encode())>MAX_BODY:raise ValueError('编辑为空、无变化或超出单文件恢复上限')
            files.append({'path':e['path'],'before':before,'after':after,'before_sha256':check.digest(before.encode()),'after_sha256':check.digest(after.encode())})
            diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=e['path'],tofile=e['path']))
        guard={k:v['sha256'] for k,v in packet['versions'].items() if 'sha256' in v}
        for ref in refs:
            if ref['kind'] in {'local','material'}:guard[ref['path']]=ref['sha256']
            elif ref['kind']=='unavailable':guard[ref['path']]=None
        oid='O-'+check.digest([item['id'],files,packet['snapshot_id'],len(db['operations'])])[:16]
        if oid in db['operations']:raise ValueError('同一操作已有记录，请查看状态')
        op={'id':oid,'issue_id':item['id'],'request':item['request'],'authorization':data['authorization'],
            'acceptance':data['acceptance'],'files':files,'guard':guard,'status':'prepared',
            'diagnosis':{k:item[k] for k in ['claim','reason','evidence','basis','reviewer','method','limitations','review_snapshot']},
            'baseline_findings':sorted(f['id'] for r in packet['structure'].values() for f in r['findings']),
            'created':now(),'history':[]}
        db['operations'][oid]=op;audit(item,'prepared',operation=oid)
        check_guard(vault,op);save(vault,db)
        return {'operation_id':oid,'status':'prepared','diff':''.join(diff),'acceptance':op['acceptance']}


def check_guard(vault, op):
    edits={e['path']:e for e in op['files']}
    for name,sha in op['guard'].items():
        allowed={sha}
        if name in edits:allowed.add(edits[name]['after_sha256'])
        if version(vault,name) not in allowed:raise ValueError('输入或证据被其他编辑改变：'+name)


def apply(vault, oid, limit=None):
    if limit is not None and (type(limit) is not int or limit<1):raise ValueError('limit 必须为正整数')
    with locked(vault) as db:
        op=db['operations'][oid]
        if op['status'] not in ACTIVE:raise ValueError('操作已结束')
        done=0
        try:
            check_guard(vault,op)
            op['status']='applying';save(vault,db)
            for e in op['files']:
                p=editable(vault,e['path']);sha=version(vault,e['path'])
                if sha==e['after_sha256']:continue  # Crash after write but before checkpoint.
                if limit is not None and done>=limit:break
                check_guard(vault,op)
                if sha!=e['before_sha256']:raise ValueError('编辑基线变化')
                # A best-effort CAS check. External editors do not honor this tool's lock.
                if version(vault,e['path'])!=sha:raise ValueError('写入前版本变化')
                check.atomic_write(p,e['after']);done+=1
                audit(op,'file_written',path=e['path']);save(vault,db)
            if all(version(vault,e['path'])==e['after_sha256'] for e in op['files']):op['status']='awaiting_verification'
            save(vault,db)
        except (OSError,ValueError) as exc:
            op['status']='conflict';audit(op,'conflict',reason=str(exc));save(vault,db)
            raise
        return {'operation_id':oid,'status':op['status'],'newly_written':done,
                'applied':[e['path'] for e in op['files'] if version(vault,e['path'])==e['after_sha256']]}


def compact(op):
    for e in op['files']:
        e.pop('before',None);e.pop('after',None)


def verify(vault, data):
    for k in ['reviewer','method','limitations','reason']:
        required(data,k)
    with locked(vault) as db:
        op=db['operations'][data['operation_id']]
        if op['status'] not in ACTIVE:raise ValueError('操作已结束')
        if not all(version(vault,e['path'])==e['after_sha256'] for e in op['files']):raise ValueError('修改未完整应用或结果已被改变')
        check_guard(vault,op)
        packet=inspect(vault,op['request'])
        if data.get('snapshot_id')!=packet['snapshot_id']:raise ValueError('复查输入已过期')
        if any(r['execution']!='checked' for r in packet['structure'].values()):raise ValueError('主审文件读取未完成')
        refs=evidence(vault,data.get('evidence'))
        if any(r['kind']=='unavailable' for r in refs):raise ValueError('验收依据缺失，不可关闭')
        if not {e['path'] for e in op['files']} <= {r.get('path') for r in refs if r['kind']=='local'}:
            raise ValueError('复查须引用每个已修改文件的实际内容')
        current={f['id'] for r in packet['structure'].values() for f in r['findings']}
        if current-set(op['baseline_findings']):raise ValueError('修订引入新结构发现，先修正或取消并重新裁定')
        acknowledged=data.get('remaining_findings',{})
        if set(acknowledged)!=current or not all(isinstance(v,str) and v.strip() for v in acknowledged.values()):raise ValueError('需逐项说明仍存的结构发现与本问题的关系')
        if data.get('passed') is not True:raise ValueError('验收未通过，保持待验证')
        if inspect(vault,op['request'])['snapshot_id']!=packet['snapshot_id']:raise ValueError('复查期间输入变化')
        evidence(vault,refs);check_guard(vault,op)
        item=db['issues'][op['issue_id']]
        op['verification']={**data,'evidence':refs,'structure':packet['structure'],'index_errors':packet['index_errors']}
        op['status']='verified';compact(op)
        item['status']='resolved';item['basis']=basis(vault,item['targets'],refs,item['basis']);item['evidence']=refs
        item['review_snapshot']=packet['snapshot_id'];audit(item,'resolved',operation=op['id'],reason=data['reason'])
        save(vault,db)
        return {'issue_id':item['id'],'status':'resolved','operation_id':op['id']}


def cancel(vault, data):
    required(data,'authorization');required(data,'reason')
    with locked(vault) as db:
        op=db['operations'][data['operation_id']]
        if op['status'] not in ACTIVE:raise ValueError('操作已结束')
        # Cancellation never rewinds files; it exposes partial writes for a fresh repair plan.
        op['status']='cancelled';op['cancellation']={**data,'observed':{e['path']:version(vault,e['path']) for e in op['files']}}
        compact(op);item=db['issues'][op['issue_id']];item['status']='open'
        audit(item,'operation_cancelled',operation=op['id'],reason=data['reason']);save(vault,db)
        return {'status':'cancelled','issue_status':'open','note':'未回滚文件；重新 inspect／record 后制定修订'}


def show(vault):
    db=read_db(vault)
    return {'schema_version':SCHEMA,'issues':[dict(i,local_evidence_changed=any(version(vault,p)!=h for p,h in i['basis']['files'].items())) for i in db['issues'].values()],
            'operations':[{k:v for k,v in op.items() if k!='files'} | {'files':[{k:v for k,v in e.items() if k not in {'before','after'}} for e in op['files']]} for op in db['operations'].values()]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['inspect','show','record','prepare','apply','verify','cancel'])
    parser.add_argument('--vault',type=Path,required=True)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--operation')
    parser.add_argument('--max-files',type=int)
    args=parser.parse_args()
    try:
        vault=args.vault.resolve(strict=True)
        if not vault.is_dir():raise ValueError('vault 必须为目录')
        if args.command=='show':out=show(vault)
        elif args.command=='apply':out=apply(vault,args.operation,args.max_files)
        else:
            if args.input is None:raise ValueError('此命令需要 --input')
            out=globals()[args.command](vault,check.read_json(args.input))
        print(json.dumps(out,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False));return 1


if __name__=='__main__':
    sys.exit(main())
