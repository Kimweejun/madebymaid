"""My workspace on top of the Komow copy: news feeds, skill library, my skills, experiment log.

Routes live under /api/local/ so they never collide with the original Komow API names.
"""
import base64
import email.utils
import hashlib
import ipaddress
import json
import os
import re
import socket
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
COLLECTION = ROOT.parent / 'a4ai-import'
LOCK = threading.Lock()
SLUG = re.compile(r'^[a-z0-9][a-z0-9-]{0,59}$')
DEFAULT_FEEDS = [
    {'title': 'GeekNews', 'url': 'https://news.hada.io/rss/news'},
    {'title': 'Hacker News', 'url': 'https://hnrss.org/frontpage'},
    {'title': 'Remotion 릴리스', 'url': 'https://github.com/remotion-dev/remotion/releases.atom'},
    {'title': 'HyperFrames 릴리스', 'url': 'https://github.com/heygen-com/hyperframes/releases.atom'},
    {'title': 'Mediabunny 릴리스', 'url': 'https://github.com/Vanilagy/mediabunny/releases.atom'},
]
FEED_CACHE = {}  # url -> (fetched_at, items, error)
FEED_TTL = 1800


def load_data(name, fallback):
    try:
        return json.loads((DATA / name).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def save_data(name, value):
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = DATA / (name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(DATA / name)


def front(content, key):
    m = re.search(r'^' + key + r':\s*(.+)$', content, re.M)
    return m[1].strip('"\' ') if m else ''


# ── skill library (SKILL.md files collected in a4ai-import/sources) ──
_library = None


def library():
    global _library
    if _library is None:
        try:
            repos = json.loads((COLLECTION / 'repositories.json').read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            repos = []
        files = [(r['repo'], p, COLLECTION / 'sources' / r['repo'].replace('/', '--') / p) for r in repos for p in r.get('skills', [])]
        sdk = COLLECTION / 'sources' / 'a4ai--ashen-seoul-sdk'
        files += [('a4ai/ashen-seoul-sdk', f.relative_to(sdk).as_posix(), f) for f in sdk.rglob('SKILL.md')] if sdk.exists() else []
        result = {}
        for repo, path, f in files:
            if not f.is_file():
                continue
            content = f.read_text(encoding='utf-8', errors='replace')
            sid = hashlib.sha256((repo + '/' + path).encode()).hexdigest()[:20]
            result[sid] = {'id': sid, 'name': front(content, 'name') or f.parent.name, 'repo': repo, 'path': path,
                           'description': front(content, 'description'), 'file': f}
        _library = result
    return _library


def skill_slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:60]


def save_skill(content, slug, overwrite=True):
    # Share the editor's naming/storage rules; imports exclusively create a new folder.
    if not SLUG.fullmatch(slug) or re.fullmatch(r'con|prn|aux|nul|com[1-9]|lpt[1-9]', slug):
        return {'error': '스킬 이름(name)을 영문·숫자로 정해 주세요. 예약된 이름은 사용할 수 없어요.'}, 400
    with LOCK:
        base = (DATA / 'skills').resolve()
        folder = base / slug
        target = folder / 'SKILL.md'
        if folder.resolve() != folder or target.resolve() != target:
            return {'error': '스킬 저장 경로가 올바르지 않습니다.'}, 400
        try:
            folder.mkdir(parents=True, exist_ok=overwrite)
            with target.open('w' if overwrite else 'x', encoding='utf-8', newline='') as out:
                out.write(content)
        except FileExistsError:
            return {'error': f'같은 이름의 스킬({slug})이 이미 있어요. 원본의 name을 바꾼 뒤 다시 등록해 주세요.'}, 409
    return {'slug': slug}, 201


def import_skill(file_id):
    if not isinstance(file_id, str) or not re.fullmatch(r'[0-9a-f]{64}', file_id):
        return {'error': '등록할 산출물의 file_id를 확인해 주세요.'}, 400
    meta, raw = file_bytes(file_id)
    if not meta:
        return {'error': '등록할 산출물 파일을 찾을 수 없어요.'}, 404
    if not meta['name'].lower().endswith('skill.md'):
        return {'error': '이름이 SKILL.md로 끝나는 파일만 등록할 수 있어요.'}, 400
    try:
        content = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return {'error': 'SKILL.md를 UTF-8 텍스트로 저장해 주세요.'}, 400
    if not content.strip() or len(content) > 200_000:
        return {'error': '스킬 내용은 비어 있지 않은 200,000자 이하 텍스트여야 해요.'}, 400
    header = re.match(r'\A---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)', content, re.M | re.S)
    if not header:
        return {'error': '파일 맨 위에 ---로 감싼 name·description 머리말이 필요해요.'}, 400
    fields = {}
    for key in ('name', 'description'):
        values = re.findall(r'^' + key + r':[ \t]*([^\r\n]*)', header[1], re.M)
        value = values[0].strip() if len(values) == 1 else ''
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                value = ''
            else:
                value = value[1:-1].strip()
        elif value.startswith(('#', '|', '>', '[', '{', '!', '&', '*')) or value.lower() in ('null', '~', 'true', 'false'):
            value = ''
        if not value:
            return {'error': f'머리말의 {key} 값은 비어 있지 않은 한 줄 텍스트로 한 번만 적어 주세요.'}, 400
        fields[key] = value
    result, code = save_skill(content, skill_slug(fields['name']), overwrite=False)
    import worklog
    no = EXP_NO.match(meta['name'])
    worklog.log(no[1] if no else 'skills', 'user', 'done' if code == 201 else 'error',
                f"skill import: {result.get('slug') or result.get('error')}", f"data/skills/{result.get('slug', '')}/SKILL.md" if code == 201 else meta['name'])
    return result, code


def my_skills():
    result = []
    for f in (DATA / 'skills').glob('*/SKILL.md'):
        content = f.read_text(encoding='utf-8', errors='replace')
        result.append({'slug': f.parent.name, 'name': front(content, 'name') or f.parent.name,
                       'description': front(content, 'description'),
                       'updated': datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()})
    return sorted(result, key=lambda s: s['updated'], reverse=True)


# ── feeds ──
def public_url(url):
    """Feed URLs must be http(s) to public addresses (blocks e.g. cloud metadata 169.254.169.254)."""
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80))
    except (OSError, ValueError):
        return False
    # ponytail: checked at resolve time only, DNS rebinding could slip past; pin the IP if this faces untrusted users
    return all(ipaddress.ip_address(i[4][0].split('%')[0]).is_global for i in infos)


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not public_url(newurl):
            raise OSError('redirect to non-public address blocked')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(SafeRedirect)


def parse_feed(raw):
    """RSS <item> and Atom <entry> -> [{title, link, date}]."""
    strip = lambda tag: tag.rsplit('}', 1)[-1]
    items = []
    for el in ET.fromstring(raw).iter():
        if strip(el.tag) not in ('item', 'entry'):
            continue
        item = {}
        for child in el:
            tag = strip(child.tag)
            if tag == 'title':
                item['title'] = (child.text or '').strip()
            elif tag == 'link' and 'link' not in item:
                item['link'] = (child.get('href') or child.text or '').strip()
            elif tag in ('pubDate', 'updated', 'published', 'date') and 'date' not in item:
                item['date'] = (child.text or '').strip()
        if item.get('title'):
            items.append(item)
    return items[:30]


def fetch_feed(feed, force=False):
    url = feed['url']
    cached = FEED_CACHE.get(url)
    if cached and not force and time.time() - cached[0] < FEED_TTL:
        return cached
    try:
        if not public_url(url):
            raise OSError('공개 인터넷 주소만 구독할 수 있습니다.')
        req = urllib.request.Request(url, headers={'User-Agent': 'KomowLocal-Feed/1.0'})
        with OPENER.open(req, timeout=8) as r:
            raw = r.read(3_000_001)
        if len(raw) > 3_000_000:
            raise OSError('피드가 너무 큽니다.')
        result = (time.time(), parse_feed(raw), '')
    except (OSError, ET.ParseError, ValueError) as error:
        result = (time.time(), cached[1] if cached else [], str(error) or '가져오기 실패')
    FEED_CACHE[url] = result
    return result


def feeds(force=False):
    subscribed = load_data('feeds.json', DEFAULT_FEEDS)
    with ThreadPoolExecutor(8) as pool:
        fetched = list(pool.map(lambda f: fetch_feed(f, force), subscribed))
    return {'feeds': [{**f, 'fetched': r[0], 'error': r[2], 'count': len(r[1])} for f, r in zip(subscribed, fetched)],
            'items': [{**i, 'source': f['title']} for f, r in zip(subscribed, fetched) for i in r[1]]}


# ── list helpers ──
def page(items, query, fields, sort_key, page_size=40):
    """Filter by ?q= (any field) and ?cat=, sort newest first, paginate with ?page=."""
    q = query.get('q', [''])[0].lower()
    cat = query.get('cat', [''])[0]
    rows = [i for i in items if (not cat or i.get('category') == cat)
            and (not q or q in ' '.join(str(i.get(k, '')) for k in fields).lower())]
    order = query.get('sort', [''])[0]
    if order == 'score':  # 추천순: highest score first, newest breaks ties
        rows.sort(key=lambda i: (i.get('score') or 0, str(i.get('date') or '')), reverse=True)
    elif order != 'keep':  # 'keep' = caller already ordered the rows
        rows.sort(key=lambda i: str(i.get(sort_key) or ''), reverse=True)
    try:
        n = max(0, int(query.get('page', ['0'])[0]))
    except ValueError:
        n = 0
    return {'total': len(rows), 'page': n, 'items': rows[n * page_size:(n + 1) * page_size]}


def iso(value):
    """RFC 822 or ISO date -> ISO string, so string sort is chronological."""
    try:
        return email.utils.parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return value or ''


def categories(items):
    counts = {}
    for i in items:
        if i.get('category'):
            counts[i['category']] = counts.get(i['category'], 0) + 1
    return sorted(counts, key=counts.get, reverse=True)[:20]


# ── file storage for 산출물 정리 ──
FILES = lambda: DATA / 'files'


def file_list():
    result = []
    for meta in FILES().glob('*.json'):
        try:
            item = json.loads(meta.read_text(encoding='utf-8'))
            if (FILES() / (item['id'] + '.bin')).is_file():
                result.append(item)
        except (OSError, ValueError, KeyError):
            pass
    return sorted(result, key=lambda i: i['created'], reverse=True)


def store_file(raw, name, folder='', note=''):
    file_id = hashlib.sha256(raw).hexdigest()
    with LOCK:
        FILES().mkdir(parents=True, exist_ok=True)
        meta = FILES() / (file_id + '.json')
        if meta.exists():
            return {**json.loads(meta.read_text(encoding='utf-8')), 'duplicate': True}
        item = {'id': file_id, 'name': name, 'size': len(raw), 'created': datetime.now(timezone.utc).isoformat(),
                'folder': folder[:60], 'note': note[:2000]}
        (FILES() / (file_id + '.bin')).write_bytes(raw)
        no = EXP_NO.match(name)
        if no:
            item['experiment'] = no[1]
            web = re.search(rb'https://[^\s<>"]+', raw) if name.endswith('_웹주소.txt') else None
            if web:
                item['web'] = web[0].decode()
        meta.write_text(json.dumps(item, ensure_ascii=False), encoding='utf-8')
    if no:
        link_experiment(no[1], item)
    return item


# Anything 렘·람 save under 통합서버/outputs/ is filed into 산출물 정리 automatically.
# The first sub-folder becomes the 산출물 folder (outputs/렘/... -> 렘).
OUTBOX = ROOT.parent / 'outputs'
LAB = ROOT.parent / '실험실'

# ── 실험하기: 렘·람 hand-off. One number (EXP-MMDD-NN) ties the prompt, the result file and the record together. ──
EXP_NO = re.compile(r'(EXP-\d{4}-\d{2})')
MAID_DIR = {'rem': '렘', 'ram': '람'}
EXP_KINDS = {
    'try': ('써보기', '이 저장소·도구를 작업 폴더에서 직접 설치·실행해 보고, 우리 환경(Windows)에서 실제로 되는지와 쓸 만한지 판단해 줘.'),
    'skill': ('스킬로 만들기', '이 글·저장소의 방법을 우리가 다시 쓸 수 있는 스킬로 정리해 줘. SKILL.md 초안(맨 위에 name·description 머리말)을 보고서와 같은 폴더에 {no}_SKILL.md 로 따로 저장해.'),
    'review': ('적용 검토', 'A4AI 업무에 쓸 수 있는지 검토해 줘. 어디에 쓸지, 비용·위험, 추천 여부를 1쪽 분량으로.'),
    'ppt': ('PPT로 분석하기', '이 대상을 분석해서 8~12장 PPT로 만들고 웹 주소로 올려 줘. 스킬 {skill} 을 읽고 순서를 그대로 따라.'),
}
PPT_SKILL = DATA / 'skills' / 'madebymaid-ppt-analysis' / 'SKILL.md'
DECK = ROOT / 'ppt' / 'deck.py'
A4AI = 'A4AI = 경북·대구 기반 AI 기업 (한국어 음성 STT/TTS, 국방 AI·드론, GPU·온디바이스, 에이전트·자동화, 로봇·제조 AX, 푸드테크, 콘텐츠·영상 AI)'


def next_exp_no(items):
    day = datetime.now(timezone.utc).astimezone().strftime('%m%d')
    used = [int(i['no'][-2:]) for i in items if i.get('no', '').startswith(f'EXP-{day}-')]
    return f'EXP-{day}-{max(used, default=0) + 1:02d}'


def exp_prompt(x, maid):
    label, goal = EXP_KINDS[x['kind']]
    name = re.sub(r'[^0-9A-Za-z가-힣]+', '-', x['title']).strip('-')[:40] or 'result'
    out = OUTBOX / MAID_DIR[maid] / f"{x['no']}_{name}.md"
    if x['kind'] == 'ppt':  # deck.py publish writes .pptx/.html/웹주소 into outputs and pushes to GitHub Pages (user approved auto-push)
        result = [f"결과: deck.json을 작업 폴더에 쓰고 python \"{DECK}\" publish deck.json 을 실행해 (deck.json의 no는 {x['no']}, maid는 {MAID_DIR[maid]}). "
                  f"PPT·웹 슬라이드가 git에 올라가고 {OUTBOX / MAID_DIR[maid]} 에 .pptx·.html·웹주소가 저장돼. git 올리기는 확인 없이 바로 해도 돼.",
                  '마지막에 나온 웹 주소를 알려 줘.']
    else:
        result = [f"결과: {out} 로 저장해 (파일 이름은 반드시 {x['no']}로 시작).",
                  f"보고서 형식(마크다운): # {x['no']} 제목 / 한 줄 결론 / ## 해 본 것 / ## 결과 / ## A4AI 적용 / ## 다음 단계"]
    return '\n'.join([
        f"[메이드 바이 메이드 실험 {x['no']}] {label}",
        f"먼저 {READ_FIRST} 를 읽고 그 규칙을 따라 (렘·람 공통).",
        f"대상: {x['title']}" + (f" — {x['url']}" if x.get('url') else ''),
        *([f"참고: {x['input'][:600]}"] if x.get('input') else []),
        f"목표: {goal.format(no=x['no'], skill=PPT_SKILL)}",
        f"배경: {A4AI}",
        f"작업 폴더: {LAB / x['no']} (없으면 만들고, 이 폴더 밖은 건드리지 마)",
        '규칙: 프로그램·패키지를 설치하지 마. 설치가 필요하면 멈추고 결과 파일에 "설치 필요: 무엇·왜"를 적어. 비밀번호·API 키는 쓰지 마. 쓰기는 작업 폴더·outputs·보고서 저장소에만.',
        *result,
    ])


READ_FIRST = ROOT.parent / 'AGENTS.md'  # shared read-first doc for 렘 (Codex) and 람 (Claude)
IMG_SKILL = DATA / 'skills' / 'madebymaid-image-gen' / 'SKILL.md'


def image_prompt(x, folder):
    """렘 (default image maker) fills the "이미지 생성 대기" slides, then republishes."""
    return '\n'.join([
        f"[메이드 바이 메이드 실험 {x['no']}] 그림 생성 (렘)",
        f"먼저 {READ_FIRST} 를 읽고 그 규칙을 따라 (렘·람 공통).",
        f"스킬 {IMG_SKILL} 을 읽고 순서를 그대로 따라.",
        f"생성할 그림 목록: {OUTBOX / folder / (x['no'] + '_이미지프롬프트.md')}",
        f"작업 폴더: {LAB / x['no']} — 그림은 images\\<슬라이드번호>.png 로 저장하고 deck.json의 visual을 file·generated로 바꿔.",
        f"그다음 python \"{DECK}\" publish deck.json 을 실행해 (git 올리기는 확인 없이). 마지막에 웹 주소를 알려 줘.",
        '사용자가 따로 준 지시(도구·화풍 등)가 있으면 그 지시를 따라.',
    ])


def link_experiment(no, f):
    """A stored file named EXP-…: attach it to that experiment's results (렘/람 by outputs folder)."""
    auto = False
    with LOCK:
        items = load_data('experiments.json', [])
        x = next((i for i in items if i.get('no') == no), None)
        if not x or any(r['id'] == f['id'] for r in x['results']):
            return
        if f['name'].endswith('_이미지프롬프트.md'):  # deck.py: images still to generate (or none left)
            _, raw = file_bytes(f['id'])
            x['image_task'] = '' if '생성할 그림 없음' in raw.decode('utf-8', 'replace') else image_prompt(x, f['folder'])
            auto = bool(x['image_task']) and not x.get('image_auto')
            import worklog
            worklog.log(no, 'server', 'info', 'images needed' if x['image_task'] else 'no images needed', f['name'])
            if auto:  # hand the pictures to 렘 once; if 렘 cannot fill them the card keeps a manual button (no loop)
                x['image_auto'] = 1
        else:
            maid = next((k for k, v in MAID_DIR.items() if v == f.get('folder')), '')
            x['results'].append({'id': f['id'], 'name': f['name'], 'maid': maid, 'at': f['created'], **({'web': f['web']} if f.get('web') else {})})
            if x['status'] in ('sent', 'running'):
                x['status'] = 'arrived'
            import worklog
            worklog.log(no, maid or 'server', 'done', 'result: ' + f['name'], f.get('web') or f'outputs/{f.get("folder", "")}/{f["name"]}')
        save_data('experiments.json', items)
    if auto:
        import runner
        runner.start(x, 'rem', x['image_task'], 'image')


def ingest_outbox():
    OUTBOX.mkdir(exist_ok=True)
    seen = load_data('outbox_seen.json', {})
    added = 0
    for f in OUTBOX.rglob('*'):
        if not f.is_file() or f.name.startswith(('.', '~$')):
            continue
        rel = f.relative_to(OUTBOX).as_posix()
        st = f.stat()
        key = f'{st.st_size}:{int(st.st_mtime)}'
        if seen.get(rel) == key or st.st_size > 20 * 1024 * 1024 or time.time() - st.st_mtime < 5:
            continue  # unchanged, too big, or still being written
        folder = rel.split('/')[0] if '/' in rel else '자동 보관'
        if not store_file(f.read_bytes(), f.name, folder, f'자동 보관 · outputs/{rel}').get('duplicate'):
            added += 1
            import worklog
            worklog.log('outputs', 'server', 'info', 'filed ' + rel)
        seen[rel] = key
    save_data('outbox_seen.json', seen)
    return added


def file_bytes(file_id):
    if not re.fullmatch(r'[0-9a-f]{64}', file_id):
        return None, None
    meta, blob = FILES() / (file_id + '.json'), FILES() / (file_id + '.bin')
    if not (meta.is_file() and blob.is_file()):
        return None, None
    return json.loads(meta.read_text(encoding='utf-8')), blob.read_bytes()


TAG_TEXT = lambda i: ' '.join(str(i.get(k) or '') for k in ('title', 'summary', 'name', 'description', 'repo', 'desc', 'input', 'sub', 'language'))
NEWS_SOURCES = {'aitimes': 'aitimes.json', 'naver': 'naver.json', 'usnews': 'usnews.json'}
STAR_FIELDS = ('url', 'title', 'source', 'region', 'period', 'date')


def starred_support(stars, votes):
    """관심 공고: live version when still collected, saved snapshot otherwise. Open ones by deadline, closed ones last."""
    import scoring
    live = {i['url']: i for i in scoring.support_scored()}
    items = []
    for url, b in stars.items():
        i = {**b, **live.get(url, {'days_left': scoring.days_left(b)}), 'starred': True, 'vote': votes.get(url, '')}
        i['closed'] = i.get('days_left') is not None and i['days_left'] < 0
        items.append(i)
    left = lambda i: (i['days_left'] or 0) * (-1 if i['closed'] else 1)  # closed: most recently closed first
    items.sort(key=lambda i: (i['closed'], i.get('days_left') is None, left(i), -i.get('starred_at', 0)))
    return items


def collector_status(job):
    import collectors
    return collectors.STATUS.get(job, {})


# ── routing: each returns (body, status) or None when the path is not ours ──
def get(path, query):
    q = lambda k: query.get(k, [''])[0]
    if path == '/api/local/news':
        source = q('source')
        names = [source] if source in NEWS_SOURCES else list(NEWS_SOURCES)
        import scoring
        votes = {e['url']: e['vote'] for e in load_data('feedback.json', []) if e['kind'] == 'news'}
        items = [{**i, 'vote': votes.get(i.get('url'), '')} for i in scoring.news_scored(names) if not i.get('excluded')]
        return {**page(items, query, ('title', 'summary', 'category', 'title_en'), 'date'),
                'categories': categories(items) if len(names) == 1 else [],
                'status': {n: collector_status(n) for n in NEWS_SOURCES},
                'counts': {n: len(load_data(NEWS_SOURCES[n], [])) for n in NEWS_SOURCES}}, 200
    if path == '/api/local/community/github':
        import tagging
        d = load_data('community_github.json', {})
        for rows in [d.get(k, []) for k in ('trending_daily', 'trending_weekly', 'trending_monthly')] + list(d.get('search', {}).values()):
            tagging.attach(rows, lambda i: i['url'], TAG_TEXT)
        return {**d, 'status': collector_status('github')}, 200
    if path == '/api/local/community/reddit':
        data = load_data('community_reddit.json', {})
        period = q('period') or 'day'
        import tagging
        posts = [{**p, 'score': round(100 * (1 - (p.get('rank', 1) - 1) / max(1, p.get('of', 1))))}  # rank within its subreddit's top list
                 for p in data.get('posts', []) if p.get('period', 'day') == period and (not q('sub') or p['sub'] == q('sub'))]
        tagging.attach(posts, lambda i: i['url'], TAG_TEXT)
        if q('tag'):
            posts = [p for p in posts if q('tag') in p['tags']['tech'] + p['tags']['field']]
        return {**page(posts, {**query, 'sort': ['score']}, ('title', 'summary', 'sub'), 'date'), 'failed': data.get('failed', []),
                'status': collector_status('reddit')}, 200
    if path == '/api/local/community/sources':
        import collectors
        return collectors.sources(), 200
    if path == '/api/local/feedback/report':
        import scoring
        return scoring.feedback_report(), 200
    if path == '/api/local/maids':
        import maids
        return maids.status(), 200
    if path == '/api/local/support':
        import scoring
        votes = {e['url']: e['vote'] for e in load_data('feedback.json', []) if e['kind'] == 'support'}
        stars = {b['url']: b for b in load_data('bookmarks.json', [])}
        everything = [{**i, 'vote': votes.get(i['url'], ''), 'starred': i['url'] in stars}
                      for i in scoring.support_scored() if not i.get('excluded')]
        area = q('area')  # '' all | 'dg' 대구·경북 | 'nation' 전국 기관 | 'other' 다른 지역 | 'soon' 마감 임박 | 'star' 관심 공고
        if area == 'star':
            items = starred_support(stars, votes)
            if q('sort') != 'score':
                query = {**query, 'sort': ['keep']}
        else:
            items = [i for i in everything if not area or (area == 'dg' and i.get('region') in ('대구', '경북'))
                     or (area == 'nation' and i.get('region') == '전국') or (area == 'other' and i.get('region') not in ('대구', '경북', '전국'))
                     or (area == 'soon' and i.get('deadline_soon'))]
        if area == 'soon' and q('sort') != 'score':  # 마감 임박: closest deadline first
            items.sort(key=lambda i: (i['days_left'], -(i.get('score') or 0)))
            query = {**query, 'sort': ['keep']}
        status = load_data('support_status.json', {})
        return {**page(items, query, ('title', 'source', 'region'), 'date'), 'categories': categories(items),
                'soon_count': sum(1 for i in everything if i.get('deadline_soon')), 'star_count': len(stars),
                'sources': {'total': len(status), 'ok': sum(1 for v in status.values() if v.get('ok')),
                            'failed': [{'id': k, 'name': v.get('name', k), 'home': v.get('home', ''), 'error': v.get('error'),
                                        'blocked': v.get('blocked', False), 'next_try': v.get('next_try', 0)}
                                       for k, v in status.items() if not v.get('ok')],
                            'robots_blocked': sum(1 for v in status.values() if v.get('robots_blocked')),
                            'at': max((v.get('at', 0) for v in status.values()), default=0)}}, 200
    if path == '/api/local/tools':
        import tagging
        tools = json.loads((ROOT / 'app' / 'tools.json').read_text(encoding='utf-8'))
        return {'tools': tagging.attach(tools, lambda i: 'tool:' + i['slug'], TAG_TEXT, tagging.tool_base)}, 200
    if path == '/api/local/files':
        return {'files': file_list()}, 200
    if path == '/api/local/feeds':
        return feeds(force=q('refresh') == '1'), 200
    if path == '/api/local/experiments':
        import runner
        import tagging
        return {'experiments': tagging.attach(runner.refresh(load_data('experiments.json', [])), lambda i: 'exp:' + i['id'], TAG_TEXT)}, 200
    if path == '/api/local/tags':  # 태그 창: one tag -> community, tools, experiments, skills
        import tagging
        return ({'tag': q('tag'), 'groups': tagging.search(q('tag'))} if q('tag') else
                {**tagging.labels(), 'counts': tagging.counts(), 'unclassified': len(tagging.unclassified())}), 200
    if path == '/api/local/home':  # 오늘 볼 것 한 화면: counts, top picks, deadlines, 렘·람 work, recent results
        import runner
        import scoring
        today = datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d')
        news = [i for i in scoring.news_scored(list(NEWS_SOURCES)) if not i.get('excluded')]
        support = [i for i in scoring.support_scored() if not i.get('excluded')]
        stars = {b['url']: b for b in load_data('bookmarks.json', [])}
        reddit = load_data('community_reddit.json', {}).get('posts', [])
        exps = runner.refresh(load_data('experiments.json', []))
        def top(rows, n=3):  # best scores, but one story once (the same news from 3 outlets is one pick)
            picked, seen = [], []
            for i in sorted(rows, key=lambda i: (i.get('score') or 0, str(i.get('date') or '')), reverse=True):
                words = set(re.findall(r'[0-9A-Za-z가-힣]{2,}', i.get('title', '')))
                if any(len(words & w) / max(1, len(words | w)) >= 0.3 for w in seen):
                    continue
                picked.append(i); seen.append(words)
                if len(picked) == n:
                    break
            return picked
        soon = sorted((i for i in support if i.get('deadline_soon')), key=lambda i: i['days_left'])[:5]
        return {'today': today,
                'news_by_source': {s: sum(1 for i in news if i.get('source') == s and str(i.get('date', '')).startswith(today)) for s in NEWS_SOURCES},
                'counts': {'news': sum(1 for i in news if str(i.get('date', '')).startswith(today)),
                           'support': sum(1 for i in support if str(i.get('date', '')).startswith(today)),
                           'github': len(load_data('community_github.json', {}).get('trending_daily', [])),
                           'reddit': sum(1 for p in reddit if p.get('period', 'day') == 'day')},
                'top_news': top(news), 'top_support': [{**i, 'starred': i['url'] in stars} for i in top(support)],
                'stars': [i for i in starred_support(stars, {}) if not i['closed']][:5], 'soon': soon,
                'work': [x for x in exps if x.get('maids')][:5],
                'reports': list({x['no']: {'no': x['no'], 'title': x['title'], 'web': r['web']} for x in reversed(exps)
                                 for r in x.get('results', []) if r.get('web')}.values())[::-1][:4],
                'files': [f for f in file_list() if not f['name'].endswith(('_이미지프롬프트.md', '_웹주소.txt'))][:4]}, 200
    if path == '/api/local/log':  # 작업 로그: waits up to `wait` s for something newer than `after` (no fast polling)
        import worklog
        try:
            after, wait = int(q('after') or 0), float(q('wait') or 0)
        except ValueError:
            raise ValueError
        events = worklog.wait(after, q('job'), wait) if wait else worklog.read(after, q('job'))
        return {'events': events, 'last': events[-1]['n'] if events else after}, 200
    if path == '/api/local/experiments/log':
        import runner
        return {'log': runner.log_tail(q('id'), q('maid'))}, 200
    if path == '/api/local/skills':
        if q('id'):
            s = library().get(q('id'))
            if not s:
                return {'error': '스킬을 찾을 수 없습니다.'}, 404
            return {**{k: v for k, v in s.items() if k != 'file'}, 'content': s['file'].read_text(encoding='utf-8', errors='replace')}, 200
        import tagging
        return {'skills': tagging.attach([{k: v for k, v in s.items() if k != 'file'} for s in library().values()], lambda i: 'skill:' + i['id'], TAG_TEXT)}, 200
    if path == '/api/local/my-skills':
        if not q('slug'):
            import tagging
            return {'skills': tagging.attach(my_skills(), lambda i: 'myskill:' + i['slug'], TAG_TEXT)}, 200
        f = DATA / 'skills' / q('slug') / 'SKILL.md'
        if not SLUG.match(q('slug')) or not f.is_file():
            return {'error': '스킬을 찾을 수 없습니다.'}, 404
        return {'slug': q('slug'), 'content': f.read_text(encoding='utf-8', errors='replace')}, 200
    return None


def post(path, body):
    if path == '/api/local/tags':  # 직접 고치기 (both empty = back to automatic)
        import tagging
        key = str(body['key'])[:600]
        if not re.match(r'(https?://|tool:|exp:|skill:|myskill:)', key):
            raise ValueError
        t = tagging.set_override(key, list(body.get('tech') or []), list(body.get('field') or []))
        import worklog
        worklog.log('tags', 'user', 'info', f"edit {key[:80]}: {'/'.join(t['tech'] + t['field']) or 'auto'}")
        return t, 200
    if path == '/api/local/tags/classify':  # 미분류 -> 렘 now (the daily run does the same)
        import tagging
        n, err = tagging.classify_now()
        return ({'error': err}, 409) if err else ({'sent': n}, 202)
    if path == '/api/local/bookmarks':  # ★ 관심 공고 on/off; the snapshot comes from our own collected data, not the client
        import scoring
        url = str(body['url'])
        with LOCK:
            stars = [b for b in load_data('bookmarks.json', []) if b['url'] != url]
            if body.get('on'):
                item = next((i for i in scoring.support_scored() if i['url'] == url), None)
                if not item:
                    return {'error': '수집된 공고에서 찾을 수 없어요.'}, 404
                stars.append({**{k: item.get(k, '') for k in STAR_FIELDS}, 'starred_at': int(time.time())})
            save_data('bookmarks.json', stars)
        return {'ok': True, 'count': len(stars)}, 200
    if path == '/api/local/feedback':
        import scoring
        kind = str(body['kind'])
        if kind not in ('support', 'news') or body.get('vote') not in ('up', 'down', ''):
            raise ValueError
        item = {'url': str(body['url'])[:500], 'title': str(body.get('title', ''))[:300], 'score': body.get('score')}
        with LOCK:
            votes = scoring.add_feedback(kind, item, body.get('vote'))
        return {'ok': True, 'votes': len(votes)}, 200
    if path == '/api/local/collect':
        import collectors
        job = str(body.get('job', '*'))
        if job != '*' and job not in collectors.JOBS:
            raise ValueError
        threading.Thread(target=collectors.run, args=(job,), daemon=True).start()
        return {'ok': True, 'started': job}, 202
    if path == '/api/local/community/sources':
        import collectors
        kind, value = str(body['kind']), str(body['value']).strip()
        valid = {'reddit': r'[A-Za-z0-9_]{2,21}', 'github_keywords': r'[^\x00-\x1f]{1,40}'}
        if kind not in valid or not re.fullmatch(valid[kind], value):
            return {'error': '서브레딧 이름(영문·숫자·_) 또는 40자 이하 키워드를 입력하세요.'}, 400
        with LOCK:
            current = collectors.sources()
            if body.get('remove'):
                current[kind] = [v for v in current[kind] if v != value]
            elif value not in current[kind]:
                current[kind].append(value)
            save_data('community_sources.json', current)
        return current, 200
    if path == '/api/local/files':
        name = str(body['name']).replace('\\', '/').split('/')[-1][:200]
        raw = base64.b64decode(body['content'], validate=True)
        if not name or not raw or len(raw) > 20 * 1024 * 1024:
            return {'error': '파일 이름 또는 크기(20MB 이하)를 확인하세요.'}, 400
        item = store_file(raw, name, str(body.get('folder', '')), str(body.get('note', '')))
        return item, 200 if item.get('duplicate') else 201
    if path == '/api/local/my-skills':
        content = str(body['content'])
        if not content.strip() or len(content) > 200_000:
            raise ValueError
        slug = str(body.get('slug') or skill_slug(front(content, 'name')))[:60]
        return save_skill(content, slug)
    if path == '/api/local/experiments/import-skill':
        return import_skill(body.get('file_id'))
    if path == '/api/local/experiments':
        item = {'id': os.urandom(6).hex(), 'created': datetime.now(timezone.utc).isoformat()}
        for key in ('skill', 'title', 'input', 'result'):
            item[key] = str(body.get(key, ''))[:50_000]
        item['rating'] = max(0, min(5, int(body.get('rating', 0))))
        if not item['title'].strip():
            raise ValueError
        maids, kind = body.get('maids') or [], body.get('kind', '')
        if maids:  # 실험하기: numbered hand-off to 렘·람 (see data/skills/madebymaid-experiment/SKILL.md)
            if kind not in EXP_KINDS or not set(maids) <= set(MAID_DIR) or len(maids) != len(set(maids)):
                raise ValueError
            item.update(kind=kind, maids=maids, url=str(body.get('url', ''))[:500], status='sent', results=[])
        with LOCK:
            items = load_data('experiments.json', [])
            if maids:
                item['no'] = next_exp_no(items)
                item['prompts'] = {m: exp_prompt(item, m) for m in maids}
            save_data('experiments.json', [item] + items)
        if maids:
            import worklog
            worklog.log(item['no'], 'user', 'info', f"created {kind} for {'+'.join(maids)}: {item['title'][:80]}")
        if maids and body.get('run'):  # 맡기기: the server starts 렘·람 itself (runner.py)
            import runner
            item['run_errors'] = [e for e in (runner.start(item, m, item['prompts'][m]) for m in maids) if e]
        return item, 201
    if path == '/api/local/experiments/run':
        import runner
        x = next((i for i in load_data('experiments.json', []) if i['id'] == str(body['id'])), None)
        maid, task = str(body.get('maid', 'rem')), str(body.get('task', 'main'))
        prompt = (x or {}).get('image_task') if task == 'image' else ((x or {}).get('prompts') or {}).get(maid)
        if maid not in MAID_DIR or not prompt:
            return {'error': '맡길 지시문이 없어요.'}, 404
        err = runner.start(x, maid, prompt, task)
        return ({'error': err}, 409) if err else ({'ok': True}, 202)
    if path == '/api/local/experiments/rate':
        with LOCK:
            items = load_data('experiments.json', [])
            x = next((i for i in items if i['id'] == str(body['id'])), None)
            if not x:
                return {'error': '실험을 찾을 수 없어요.'}, 404
            x['rating'] = max(0, min(5, int(body.get('rating', 0))))
            x['result'] = str(body.get('result', ''))[:50_000]
            import worklog
            worklog.log(x.get('no') or x['id'], 'user', 'info', f"rated {x['rating']}")
            if x.get('status') in ('sent', 'arrived') and x['rating']:
                x['status'] = 'rated'
            save_data('experiments.json', items)
        return x, 200
    if path == '/api/local/feeds':
        url = str(body['url']).strip()
        if not public_url(url):
            return {'error': '공개 인터넷의 http(s) 피드 주소만 추가할 수 있습니다.'}, 400
        with LOCK:
            subscribed = load_data('feeds.json', DEFAULT_FEEDS)
            if not any(f['url'] == url for f in subscribed):
                subscribed.append({'title': str(body.get('title') or urlsplit(url).hostname)[:80], 'url': url})
                save_data('feeds.json', subscribed)
        return {'ok': True}, 201
    return None


def delete(path, query):
    q = lambda k: query.get(k, [''])[0]
    with LOCK:
        if path == '/api/local/files':
            meta, _ = file_bytes(q('id'))
            if not meta:
                return {'error': '파일을 찾을 수 없습니다.'}, 404
            for ext in ('.json', '.bin'):
                (FILES() / (q('id') + ext)).unlink()
            (DATA / 'previews' / (q('id') + '.pdf')).unlink(missing_ok=True)  # 펼치기 cache
            return {'ok': True}, 200
        if path == '/api/local/my-skills':
            f = DATA / 'skills' / q('slug') / 'SKILL.md'
            if not SLUG.match(q('slug')) or not f.is_file():
                return {'error': '스킬을 찾을 수 없습니다.'}, 404
            f.unlink()
            if not any(f.parent.iterdir()):
                f.parent.rmdir()
            return {'deleted': q('slug')}, 200
        if path == '/api/local/experiments':
            save_data('experiments.json', [i for i in load_data('experiments.json', []) if i['id'] != q('id')])
            return {'ok': True}, 200
        if path == '/api/local/feeds':
            save_data('feeds.json', [f for f in load_data('feeds.json', DEFAULT_FEEDS) if f['url'] != q('url')])
            return {'ok': True}, 200
    return None
