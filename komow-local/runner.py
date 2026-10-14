"""맡기기: the site starts 렘 (Codex CLI) or 람 (Claude Code CLI) itself, headless, with the user's own logins (no API keys).

Limits (user decision 2026-10-14): write only to the experiment's 실험실 folder, outputs/ and the report repo;
no installs (the prompt says to stop and write "설치 필요"); internet stays on because the agent must read the source
and push the report — the CLIs cannot limit network to git alone.
"""
import glob
import os
import subprocess
import threading
import time
from pathlib import Path

import workspace

MAID_NAME = {'rem': '렘', 'ram': '람'}
REPO = workspace.ROOT.parent / 'madebymaid-reports'
TIMEOUT = 45 * 60
PROCS = {}  # (experiment id, maid) -> Popen, only for runs this server started


def find_cli(maid):
    """Newest bundled binary: Codex Desktop ships codex.exe, the Claude app ships claude.exe (versioned folders)."""
    patterns = ([r'%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe'] if maid == 'rem' else
                [r'%APPDATA%\Claude\claude-code\*\*\claude.exe',  # inside the Store app's virtualized AppData
                 r'%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude-code\*\*\claude.exe'])  # real location
    found = [f for p in patterns for f in glob.glob(os.path.expandvars(p))]
    return max(found, key=os.path.getmtime) if found else None


def command(maid, cli, cwd):
    if maid == 'rem':
        return [cli, 'exec', '--skip-git-repo-check', '-C', str(cwd), '--sandbox', 'workspace-write',
                '--add-dir', str(workspace.OUTBOX), '--add-dir', str(REPO),
                '-c', 'sandbox_workspace_write.network_access=true', '--enable', 'image_generation', '-']
    tools = ['Read', 'Write', 'Edit', 'Glob', 'Grep', 'WebFetch', 'WebSearch',
             'Bash(python:*)', 'Bash(git:*)', 'Bash(curl:*)', 'Bash(mkdir:*)', 'Bash(ls:*)', 'Bash(cp:*)']
    return [cli, '-p', '--permission-mode', 'acceptEdits', '--add-dir', str(workspace.OUTBOX), str(REPO),
            '--allowedTools', *tools, '--disallowedTools', 'Bash(pip:*)', 'Bash(npm:*)', 'Bash(winget:*)', 'Bash(choco:*)']


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
    """Start one headless run in the background. Returns an error string, or '' when started."""
    if (x['id'], maid) in PROCS and PROCS[(x['id'], maid)].poll() is None:
        return f'{MAID_NAME[maid]}가 이미 이 실험을 하고 있어요.'
    cli = find_cli(maid)
    if not cli:
        return f'{MAID_NAME[maid]} 명령줄 도구를 찾지 못했어요.'
    cwd = workspace.LAB / x['no']
    cwd.mkdir(parents=True, exist_ok=True)
    log = cwd / f'run-{MAID_NAME[maid]}.log'
    out = log.open('a', encoding='utf-8')
    out.write(f'\n===== {time.strftime("%Y-%m-%d %H:%M:%S")} 시작 ({task}) =====\n'); out.flush()
    try:
        proc = subprocess.Popen(command(maid, cli, cwd), cwd=cwd, stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except OSError as e:
        out.close()
        return f'{MAID_NAME[maid]}를 시작하지 못했어요: {e}'
    proc.stdin.write(prompt.encode('utf-8')); proc.stdin.close()
    PROCS[(x['id'], maid)] = proc
    set_run(x['id'], maid, state='running', task=task, started=int(time.time()), log=str(log))

    def wait():
        try:
            code = proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill(); code = 'timeout'
        out.write(f'\n===== 끝 (코드 {code}) =====\n'); out.close()
        text = log.read_text(encoding='utf-8', errors='replace')[-4000:]
        note = '로그인 필요' if 'Not logged in' in text or 'Please run /login' in text else ''
        set_run(x['id'], maid, state='done' if code == 0 else 'failed', ended=int(time.time()), code=code, note=note)
    threading.Thread(target=wait, daemon=True).start()
    return ''


def start_plain(maid, prompt, cwd, on_done=None):
    """A run that is not an experiment (e.g. the daily tag batch): same limits, log in cwd, on_done(code) afterwards."""
    if ('plain', str(cwd)) in PROCS and PROCS[('plain', str(cwd))].poll() is None:
        return '이미 실행 중이에요.'
    cli = find_cli(maid)
    if not cli:
        return f'{MAID_NAME[maid]} 명령줄 도구를 찾지 못했어요.'
    out = (Path(cwd) / f'run-{MAID_NAME[maid]}.log').open('a', encoding='utf-8')
    try:
        proc = subprocess.Popen(command(maid, cli, cwd), cwd=cwd, stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except OSError as e:
        out.close()
        return str(e)
    proc.stdin.write(prompt.encode('utf-8')); proc.stdin.close()
    PROCS[('plain', str(cwd))] = proc

    def wait():
        try:
            code = proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill(); code = 'timeout'
        out.close()
        if on_done:
            on_done(code)
    threading.Thread(target=wait, daemon=True).start()
    return ''


def refresh(items):
    """A run marked running that this server did not start (server restarted) is shown as ended."""
    for x in items:
        for maid, r in (x.get('runs') or {}).items():
            if r.get('state') == 'running' and (x['id'], maid) not in PROCS:
                r['state'] = 'ended'
    return items


def log_tail(exp_id, maid):
    x = next((i for i in workspace.load_data('experiments.json', []) if i['id'] == exp_id), None)
    path = Path(((x or {}).get('runs') or {}).get(maid, {}).get('log', ''))
    return path.read_text(encoding='utf-8', errors='replace')[-6000:] if path.is_file() else ''
