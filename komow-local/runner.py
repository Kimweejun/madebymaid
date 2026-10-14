"""맡기기: the site starts 렘 (Codex CLI) or 람 (Claude Code CLI) itself, headless, with the user's own logins (no API keys).

Limits (user decision 2026-10-14): write only to the experiment's 실험실 folder, outputs/ and the report repo;
no installs (the prompt says to stop and write "설치 필요"); internet stays on because the agent must read the source
and push the report — the CLIs cannot limit network to git alone.

Both CLIs stream JSON events; every meaningful step goes to the work log (worklog.py) as it happens, and the run log
(실험실/<job>/run-렘|람.log) gets the same steps in plain text plus the final answer.
"""
import glob
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import workspace
import worklog

MAID_NAME = {'rem': '렘', 'ram': '람'}
REPO = workspace.ROOT.parent / 'madebymaid-reports'
TIMEOUT = 45 * 60
PROCS = {}  # (job key, maid) -> Popen, only for runs this server started


def find_cli(maid):
    """Newest bundled binary: Codex Desktop ships codex.exe, the Claude app ships claude.exe (versioned folders)."""
    patterns = ([r'%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe'] if maid == 'rem' else
                [r'%APPDATA%\Claude\claude-code\*\*\claude.exe',  # inside the Store app's virtualized AppData
                 r'%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude-code\*\*\claude.exe'])  # real location
    found = [f for p in patterns for f in glob.glob(os.path.expandvars(p))]
    return max(found, key=os.path.getmtime) if found else None


def command(maid, cli, cwd):
    if maid == 'rem':
        return [cli, 'exec', '--json', '--skip-git-repo-check', '-C', str(cwd), '--sandbox', 'workspace-write',
                '--add-dir', str(workspace.OUTBOX), '--add-dir', str(REPO),
                '-c', 'sandbox_workspace_write.network_access=true', '--enable', 'image_generation', '-']
    tools = ['Read', 'Write', 'Edit', 'Glob', 'Grep', 'WebFetch', 'WebSearch',
             'Bash(python:*)', 'Bash(git:*)', 'Bash(curl:*)', 'Bash(mkdir:*)', 'Bash(ls:*)', 'Bash(cp:*)']
    return [cli, '-p', '--output-format', 'stream-json', '--verbose', '--permission-mode', 'acceptEdits',
            '--add-dir', str(workspace.OUTBOX), str(REPO),
            '--allowedTools', *tools, '--disallowedTools', 'Bash(pip:*)', 'Bash(npm:*)', 'Bash(winget:*)', 'Bash(choco:*)']


def short(v, n=90):
    return ' '.join(str(v).split())[:n]


def steps(maid, e):
    """One CLI event -> (kind, text): kind 'step' for progress, 'final' for the answer, 'error'. None to skip."""
    t = e.get('type')
    if maid == 'rem':  # codex exec --json
        item = e.get('item') or {}
        it = item.get('type')
        if t == 'item.started' and it == 'command_execution':
            return 'step', 'run: ' + short(item.get('command', ''))
        if t == 'item.completed' and it == 'web_search':
            return 'step', 'web: ' + short(item.get('query', ''))
        if t == 'item.completed' and it == 'file_change':
            return 'step', 'write: ' + ', '.join(Path(c.get('path', '')).name for c in item.get('changes', []))[:120]
        if t == 'item.completed' and it == 'agent_message':
            return 'final', item.get('text', '')
        if t in ('error', 'turn.failed'):
            return 'error', short((e.get('error') or {}).get('message') or e.get('message') or e, 200)
        return None
    # claude -p --output-format stream-json
    if t == 'assistant':
        for c in (e.get('message') or {}).get('content', []):
            if c.get('type') == 'tool_use':
                i, name = c.get('input') or {}, c.get('name', '')
                what = {'WebFetch': 'web: ' + short(i.get('url', '')), 'WebSearch': 'web: ' + short(i.get('query', '')),
                        'Read': 'read: ' + Path(i.get('file_path', '')).name, 'Write': 'write: ' + Path(i.get('file_path', '')).name,
                        'Edit': 'write: ' + Path(i.get('file_path', '')).name, 'Bash': 'run: ' + short(i.get('command', ''))}
                return 'step', what.get(name, name.lower())
        return None
    if t == 'result':
        return ('error' if e.get('is_error') else 'final'), e.get('result', '')
    return None


def spawn(job, maid, prompt, cwd, task, on_end):
    """Start the CLI, stream its events into the work log and run log, call on_end(code, note) when it stops."""
    cli = find_cli(maid)
    if not cli:
        worklog.log(job, maid, 'error', f'{task}: cli not found')
        return f'{MAID_NAME[maid]} 명령줄 도구를 찾지 못했어요.'
    cwd = Path(cwd); cwd.mkdir(parents=True, exist_ok=True)
    out = (cwd / f'run-{MAID_NAME[maid]}.log').open('a', encoding='utf-8')
    out.write(f'\n===== {time.strftime("%Y-%m-%d %H:%M:%S")} start ({task}) =====\n'); out.flush()
    try:
        proc = subprocess.Popen(command(maid, cli, cwd), cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except OSError as e:
        out.close()
        worklog.log(job, maid, 'error', f'{task}: cannot start: {e}')
        return f'{MAID_NAME[maid]}를 시작하지 못했어요: {e}'
    proc.stdin.write(prompt.encode('utf-8')); proc.stdin.close()
    PROCS[(job, maid)] = proc
    worklog.log(job, maid, 'start', task, str(cwd))

    def pump():
        final, errors, raw_tail = '', [], []
        timer = threading.Timer(TIMEOUT, proc.kill); timer.start()
        for raw in proc.stdout:
            line = raw.decode('utf-8', 'replace').strip()
            if not line:
                continue
            try:
                ev = steps(maid, json.loads(line))
            except ValueError:  # plain text (e.g. "Not logged in")
                raw_tail = (raw_tail + [line])[-5:]; out.write(line + '\n'); out.flush()
                continue
            if not ev:
                continue
            kind, text = ev
            if kind == 'final':
                final = text
            else:
                (errors.append(text) if kind == 'error' else None)
                worklog.log(job, maid, kind, text)
                out.write(f'[{time.strftime("%H:%M:%S")}] {kind}: {text}\n'); out.flush()
        code = proc.wait(); timer.cancel()
        text = '\n'.join(raw_tail)
        note = '로그인 필요' if 'Not logged in' in text or 'Please run /login' in text else ''
        if final:
            out.write(final.strip() + '\n')
        out.write(f'===== end (code {code}) =====\n'); out.close()
        if code == 0 and not errors:
            worklog.log(job, maid, 'done', short(final, 200) or task)
        else:
            worklog.log(job, maid, 'error', note or (errors[-1] if errors else short(text, 200)) or f'exit {code}')
        on_end(code, note)
    threading.Thread(target=pump, daemon=True).start()
    return ''


def set_run(exp_id, maid, **state):
    with workspace.LOCK:
        items = workspace.load_data('experiments.json', [])
        x = next((i for i in items if i['id'] == exp_id), None)
        if not x:
            return
        x.setdefault('runs', {})[maid] = {**x.get('runs', {}).get(maid, {}), **state}
        running = any(r.get('state') == 'running' for r in x['runs'].values())
        if running and x.get('status') in ('sent', None):
            x['status'] = 'running'
        elif not running and x.get('status') == 'running':
            x['status'] = 'sent'  # ended without a result file yet
        workspace.save_data('experiments.json', items)


def start(x, maid, prompt, task='main'):
    """Start one headless run for an experiment. Returns an error string, or '' when started."""
    job = x['no']
    if (job, maid) in PROCS and PROCS[(job, maid)].poll() is None:
        return f'{MAID_NAME[maid]}가 이미 이 실험을 하고 있어요.'
    cwd = workspace.LAB / job
    log = cwd / f'run-{MAID_NAME[maid]}.log'

    def end(code, note):
        set_run(x['id'], maid, state='done' if code == 0 else 'failed', ended=int(time.time()), code=code, note=note)
    err = spawn(job, maid, prompt, cwd, task, end)
    if not err:
        set_run(x['id'], maid, state='running', task=task, started=int(time.time()), log=str(log))
    return err


def start_plain(maid, prompt, cwd, on_done=None):
    """A run that is not an experiment (e.g. the daily tag batch): same limits and logging."""
    job = Path(cwd).name
    if (job, maid) in PROCS and PROCS[(job, maid)].poll() is None:
        return '이미 실행 중이에요.'
    return spawn(job, maid, prompt, cwd, 'batch', lambda code, note: on_done and on_done(code))


def refresh(items):
    """A run marked running that this server did not start (server restarted) is shown as ended."""
    for x in items:
        for maid, r in (x.get('runs') or {}).items():
            if r.get('state') == 'running' and (x.get('no'), maid) not in PROCS:
                r['state'] = 'ended'
    return items


def log_tail(exp_id, maid):
    x = next((i for i in workspace.load_data('experiments.json', []) if i['id'] == exp_id), None)
    path = Path(((x or {}).get('runs') or {}).get(maid, {}).get('log', ''))
    return path.read_text(encoding='utf-8', errors='replace')[-6000:] if path.is_file() else ''
