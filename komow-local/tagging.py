"""AI 기술·분야 태그 (user decisions 2026-10-14).

Order: your own edit (data/tags_override.json) > hand-picked tool tags (tags.json "tools") > 렘's call for items the
rules could not place (data/tags_ai.json) > keyword rules (tags.json). Max 2 per axis. No tech tag -> "미분류".
Once a day the unclassified ones go to 렘 in one batch (runner.start_plain), never twice for the same item.
"""
import json
import re
import time
from pathlib import Path

import workspace

RULES = Path(__file__).with_name('tags.json')
NOT_AI, UNCLASSIFIED = 'AI 아님', '미분류'
BATCH = 100
_rules = {'mtime': None, 'value': None}


def rules():
    m = RULES.stat().st_mtime
    if _rules['mtime'] != m:
        _rules.update(mtime=m, value=json.loads(RULES.read_text(encoding='utf-8')))
    return _rules['value']


def labels():
    r = rules()
    return {'tech': list(r['tech']) + [NOT_AI], 'field': list(r['field'])}


def hits(text, words):
    """Short Latin words (mcp, gpu, ros) must stand alone; everything else is a plain case-insensitive substring."""
    low = text.lower()
    n = 0
    for w in words:
        if re.fullmatch(r'[a-z0-9.&-]{1,4}', w):
            n += bool(re.search(r'(?<![a-z0-9])' + re.escape(w) + r'(?![a-z0-9])', low))
        else:
            n += w in low
    return n


def by_rules(text):
    r, out = rules(), {}
    for axis in ('tech', 'field'):
        scored = sorted(((hits(text, words), tag) for tag, words in r[axis].items()), key=lambda s: -s[0])
        out[axis] = [tag for n, tag in scored if n][:r['max_per_axis']]
    return out


def attach(items, key, text, base=None):
    """Add item['tags'] = {'tech', 'field', 'src'} in place. key/text/base are functions of the item."""
    over, ai = workspace.load_data('tags_override.json', {}), workspace.load_data('tags_ai.json', {})
    for i in items:
        k = key(i)
        b = base(i) if base else None
        if k in over:
            t, src = over[k], 'manual'
        elif b:
            t, src = {'tech': b[0], 'field': b[1]}, 'base'
        else:
            t, src = by_rules(text(i)), 'rule'
            if not t['tech'] and k in ai:
                t, src = ai[k], 'ai'
        i['tags'] = {'tech': t.get('tech') or [UNCLASSIFIED], 'field': t.get('field') or [], 'src': src, 'key': k}
    return items


def validate(tech, field):
    ok = labels()
    tech = [t for t in tech if t in ok['tech']][:2]
    field = [f for f in field if f in ok['field']][:2]
    return tech, field


def set_override(key, tech, field):
    tech, field = validate(tech, field)
    with workspace.LOCK:
        over = workspace.load_data('tags_override.json', {})
        if tech or field:
            over[key] = {'tech': tech, 'field': field}
        else:
            over.pop(key, None)  # both empty = back to automatic
        workspace.save_data('tags_override.json', over)
    return {'tech': tech, 'field': field}


# ── everything that carries tags, in one place (for the tag window and the daily batch) ──
def tool_base(t):
    return rules()['tools'].get(t['slug'])


def everything():
    d = workspace.load_data('community_github.json', {})
    repos, seen = [], set()
    for r in [*d.get('trending_daily', []), *d.get('trending_weekly', []), *d.get('trending_monthly', []), *[x for v in d.get('search', {}).values() for x in v]]:
        if r.get('url') not in seen:
            seen.add(r.get('url')); repos.append(r)
    posts = list({p['url']: p for p in workspace.load_data('community_reddit.json', {}).get('posts', [])}.values())
    tools = json.loads((workspace.ROOT / 'app' / 'tools.json').read_text(encoding='utf-8'))
    exps = workspace.load_data('experiments.json', [])
    skills = [{k: v for k, v in s.items() if k != 'file'} for s in workspace.library().values()]
    mine = workspace.my_skills()
    text = lambda i: ' '.join(str(i.get(k) or '') for k in ('title', 'summary', 'name', 'description', 'repo', 'desc', 'input', 'sub', 'language'))
    attach(repos, lambda i: i['url'], text)
    attach(posts, lambda i: i['url'], text)
    attach(tools, lambda i: 'tool:' + i['slug'], text, tool_base)
    attach(exps, lambda i: 'exp:' + i['id'], text)
    attach(skills, lambda i: 'skill:' + i['id'], text)
    attach(mine, lambda i: 'myskill:' + i['slug'], text)
    return {'github': repos, 'reddit': posts, 'tools': tools, 'experiments': exps, 'skills': skills + mine}


def search(tag):
    out = {}
    for group, items in everything().items():
        out[group] = [i for i in items if tag in i['tags']['tech'] or tag in i['tags']['field']][:40]
    return out


def counts():
    c = {}
    for items in everything().values():
        for i in items:
            for t in i['tags']['tech'] + i['tags']['field']:
                c[t] = c.get(t, 0) + 1
    return c


# ── daily batch: items the rules could not place go to 렘 once ──
def unclassified():
    asked = workspace.load_data('tags_ai_asked.json', {})
    items = []
    for group, rows in everything().items():
        for i in rows:
            if i['tags']['src'] == 'rule' and i['tags']['tech'] == [UNCLASSIFIED] and i['tags']['key'] not in asked:
                items.append({'key': i['tags']['key'], 'title': i.get('title') or i.get('name', ''),
                              'text': (i.get('summary') or i.get('description') or i.get('desc') or '')[:300], 'where': group})
    return items


def classify_now():
    """Hand up to BATCH unclassified items to 렘. Returns how many were sent ('' error string on failure)."""
    import runner
    items = unclassified()[:BATCH]
    if not items:
        return 0, ''
    day = time.strftime('%Y%m%d-%H%M')
    folder = workspace.LAB / f'TAGS-{day}'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'items.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
    ok = labels()
    prompt = '\n'.join([
        '[메이드 바이 메이드] 태그 분류 (렘)',
        f'먼저 {workspace.ROOT.parent / "AGENTS.md"} 를 읽고 그 규칙을 따라 (렘·람 공통).',
        f'스킬 {workspace.DATA / "skills" / "madebymaid-tagging" / "SKILL.md"} 을 따라.',
        f'작업 폴더: {folder}. items.json 의 항목마다 AI 기술 태그와 분야 태그를 골라 result.json 으로 저장해.',
        f'AI 기술(최대 2개, AI와 무관하면 "{NOT_AI}"): {", ".join(ok["tech"])}',
        f'분야(최대 2개, 맞는 게 없으면 빈 목록): {", ".join(ok["field"])}',
        '위 목록에 있는 이름만 그대로 써. 형식: {"<key>": {"tech": [...], "field": [...]}, ...} (모든 key 포함).',
        '인터넷 검색이나 설치는 하지 마. 제목과 설명만 보고 판단해. 쓰기는 작업 폴더에만.',
    ])
    with workspace.LOCK:
        asked = workspace.load_data('tags_ai_asked.json', {})
        asked.update({i['key']: day for i in items})
        workspace.save_data('tags_ai_asked.json', asked)
    err = runner.start_plain('rem', prompt, folder, lambda code: merge(folder))
    return (0, err) if err else (len(items), '')


def merge(folder):
    f = folder / 'result.json'
    try:
        result = json.loads(f.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return 0
    with workspace.LOCK:
        ai = workspace.load_data('tags_ai.json', {})
        for k, v in result.items():
            if isinstance(v, dict):
                tech, field = validate(v.get('tech') or [], v.get('field') or [])
                if tech or field:
                    ai[k] = {'tech': tech, 'field': field}
        workspace.save_data('tags_ai.json', ai)
    return len(result)


def daily():
    """Called from the 30-second outbox loop: once a day after 9 am."""
    st = workspace.load_data('tags_ai_status.json', {})
    today = time.strftime('%Y-%m-%d')
    if st.get('day') == today or time.localtime().tm_hour < 9:
        return
    workspace.save_data('tags_ai_status.json', {'day': today})
    classify_now()
