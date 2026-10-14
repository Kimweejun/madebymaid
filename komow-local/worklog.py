"""작업 로그: every job writes start / step / error / done here, so nobody has to ask "is it done?" (user decision 2026-10-15).

One line per event in 통합서버/logs/work.jsonl:
  {"n": 42, "t": "2026-10-15T01:02:03", "job": "EXP-1015-01", "by": "ram", "ev": "done", "msg": "result saved", "ref": "outputs/람/…"}
  ev: start | step | error | done | info      by: rem | ram | server | user
Read it with GET /api/local/log?after=<n>&wait=60 (returns as soon as something new happens, or after 60 s).
Write from anywhere:  python komow-local/worklog.py <job> <by> <ev> "<msg>" [ref]
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

FILE = Path(os.environ.get('MADEBYMAID_WORKLOG') or Path(__file__).resolve().parents[1] / 'logs' / 'work.jsonl')  # tests point this elsewhere
LOGS = FILE.parent
EVENTS = ('start', 'step', 'error', 'done', 'info')
_cond = threading.Condition()


def _last_n():
    """Read from the file every time: deck.py and agents append from other processes too."""
    n = 0
    if FILE.is_file():
        with FILE.open('rb') as f:
            f.seek(max(0, FILE.stat().st_size - 4096))
            for line in f.read().splitlines():
                try:
                    n = max(n, json.loads(line)['n'])
                except (ValueError, KeyError):
                    pass
    return n


def log(job, by, ev, msg, ref=''):
    """Append one event. Never raises: logging must not break the work it describes."""
    try:
        with _cond:
            LOGS.mkdir(exist_ok=True)
            n = _last_n() + 1
            if FILE.is_file() and FILE.stat().st_size > 5_000_000:  # rotate; numbering continues from n
                FILE.rename(LOGS / f'work-{time.strftime("%Y%m%d-%H%M%S")}.jsonl')
            e = {'n': n, 't': time.strftime('%Y-%m-%dT%H:%M:%S'), 'job': str(job)[:60], 'by': by,
                 'ev': ev if ev in EVENTS else 'info', 'msg': ' '.join(str(msg).split())[:300]}
            if ref:
                e['ref'] = str(ref)[:300]
            with FILE.open('a', encoding='utf-8') as f:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')
            _cond.notify_all()
            return e
    except OSError:
        return None


def read(after=0, job='', limit=200):
    if not FILE.is_file():
        return []
    out = []
    with FILE.open(encoding='utf-8') as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e['n'] > after and (not job or e['job'] == job):
                out.append(e)
    return out[-limit:]


def wait(after=0, job='', timeout=60):
    """New events after `after`, waiting up to `timeout` seconds for the first one (long poll)."""
    end = time.time() + max(0, min(timeout, 120))
    while True:
        events = read(after, job)
        left = end - time.time()
        if events or left <= 0:
            return events
        with _cond:
            if _last_n() <= after or job:
                _cond.wait(min(left, 5))  # 5 s re-check also catches lines written by other processes


def last(job):
    events = read(0, job, limit=1)
    return events[-1] if events else None


if __name__ == '__main__':
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    print(json.dumps(log(*sys.argv[1:6]), ensure_ascii=False))
