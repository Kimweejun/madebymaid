"""렘(GPT)·람(Claude) live state, read-only from local logs.

람: ~/.clawdex/events.log, one JSON line per Claude Code hook event (written by clawdex).
렘: newest ~/.codex/sessions/**/rollout-*.jsonl (Codex task_started / task_complete / turn_aborted).
Sprite rows (192x208 cells): 0 idle, 3 waving, 5 failed, 6 waiting, 7 running, 8 review.
"""
import json
import time
from pathlib import Path

HOME = Path.home()
CLAUDE_LOG = HOME / '.clawdex' / 'events.log'
CODEX_SESSIONS = HOME / '.codex' / 'sessions'
QUIET = 600  # seconds without activity -> idle
STATES = {
    'idle': (0, '쉬는 중'), 'working': (7, '작업 중'), 'review': (8, '살펴보는 중'),
    'waiting': (6, '확인 필요'), 'done': (3, '완료 · 결과 확인'), 'failed': (5, '중단됨'),
}
READ_TOOLS = {'Read', 'Grep', 'Glob', 'WebFetch', 'WebSearch', 'LS'}


def tool_label(tool):
    if tool in ('Bash', 'PowerShell'):
        return '명령 실행'
    if tool in ('Edit', 'Write', 'NotebookEdit'):
        return '파일 수정'
    if tool in READ_TOOLS:
        return '자료 확인'
    if tool in ('Agent', 'Task', 'Workflow'):
        return '하위 작업'
    if 'Browser' in tool or 'chrome' in tool or 'playwright' in tool:
        return '브라우저 작업'
    return '도구 사용' if tool else ''


def tail_lines(path, size=65536):
    with open(path, 'rb') as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - size))
        return f.read().decode('utf-8', 'replace').splitlines()[1:] or []


def state(name, since, detail=''):
    if time.time() - since > QUIET and name != 'waiting':
        name = 'idle'
    row, label = STATES[name]
    return {'state': name, 'row': row, 'label': label, 'since': since, 'detail': detail}


def claude():
    try:
        lines = tail_lines(CLAUDE_LOG)
    except OSError:
        return {**state('idle', 0), 'available': False}
    for line in reversed(lines):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        kind, tool, ts = ev.get('event'), ev.get('tool') or '', ev.get('ts', 0) / 1000
        if kind == 'Notification':
            return {**state('waiting', ts, '권한 요청이나 답변을 기다리는 중'), 'available': True}
        if kind == 'Stop':
            return {**state('done', ts), 'available': True}
        if kind in ('SessionEnd', 'SessionStart'):
            return {**state('idle', ts), 'available': True}
        if kind == 'PreToolUse':
            return {**state('review' if tool in READ_TOOLS else 'working', ts, tool_label(tool)), 'available': True}
        if kind in ('UserPromptSubmit', 'PostToolUse', 'SubagentStop', 'PreCompact'):
            return {**state('review', ts, '생각하는 중'), 'available': True}
    return {**state('idle', 0), 'available': True}


def codex():
    try:
        days = sorted((p for p in CODEX_SESSIONS.glob('*/*/*') if p.is_dir()), reverse=True)[:3]
        newest = max((f for d in days for f in d.glob('rollout-*.jsonl')), key=lambda f: f.stat().st_mtime)
    except (OSError, ValueError):
        return {**state('idle', 0), 'available': False}
    mtime = newest.stat().st_mtime
    for line in reversed(tail_lines(newest, 262144)):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        kind = (ev.get('payload') or {}).get('type') if isinstance(ev.get('payload'), dict) else None
        if ev.get('type') == 'event_msg' and kind == 'task_complete':
            return {**state('done', mtime), 'available': True}
        if ev.get('type') == 'event_msg' and kind == 'turn_aborted':
            return {**state('failed', mtime), 'available': True}
        if ev.get('type') == 'event_msg' and kind == 'task_started':
            return {**state('working', mtime), 'available': True}
        if ev.get('type') == 'response_item' and kind in ('function_call', 'custom_tool_call', 'reasoning'):
            return {**state('working', mtime, '도구 실행' if kind != 'reasoning' else '생각하는 중'), 'available': True}
    return {**state('idle', mtime), 'available': True}


def status():
    return {'rem': {'name': '렘', 'engine': 'GPT', 'source': 'Codex', **codex()},
            'ram': {'name': '람', 'engine': 'Claude', 'source': 'Claude Code', **claude()}}


if __name__ == '__main__':
    print(json.dumps(status(), ensure_ascii=False, indent=1))
