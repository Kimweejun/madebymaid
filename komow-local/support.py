"""지원사업 collector: every board in support_sources.json, parsed by one generic list-page reader.

Most Korean public-agency boards are a <table> or <ul> list where each row has one title link and
one or two dates (posted date, or an application period "2026-10-01 ~ 2026-10-31"). parse_board()
reads that shape; a source only needs a URL, plus `link` when rows open via javascript:fn('123').

Try one board:  python support.py try <url> [link-template-with-{id}]
Run all boards: python support.py run
"""
import html
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import workspace

KST = timezone(timedelta(hours=9))
SOURCES_FILE = Path(__file__).resolve().parent / 'support_sources.json'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
DATE = re.compile(r'(20\d\d)\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})')
SKIP_TITLES = re.compile(r'^(이전|다음|처음|마지막|더보기|목록|검색|로그인|홈|\d+)$')
STATUS = {}


INSECURE = ssl.create_default_context()
INSECURE.check_hostname, INSECURE.verify_mode = False, ssl.CERT_NONE
INSECURE.set_ciphers('DEFAULT@SECLEVEL=0')  # old servers with weak DH keys  # only for sources flagged `insecure_ssl` (broken cert chains)


def fetch(url, data=None, headers=None, timeout=25, insecure=False):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'Accept-Language': 'ko', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=INSECURE if insecure else None) as r:
        raw = r.read(6_000_000)
        charset = r.headers.get_content_charset()
    if not charset:
        m = re.search(rb'charset=["\']?([\w-]+)', raw[:4000], re.I)
        charset = m.group(1).decode() if m else 'utf-8'
    return raw.decode(charset if charset.lower() not in ('ks_c_5601-1987', 'euc_kr') else 'cp949', 'replace')


def text(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment or ''))).strip()


def iso_date(m):
    try:
        return datetime(int(m[0]), int(m[1]), int(m[2])).strftime('%Y-%m-%d')
    except ValueError:
        return ''


def resolve_link(attrs, base_url, link_tpl):
    """href / javascript:fn('id') / onclick -> absolute URL, or '' when it can't be resolved."""
    href = (re.search(r'href\s*=\s*(["\'])(.*?)\1', attrs, re.S) or [None, None, ''])[2].strip()
    if re.match(r'javascript:\s*(void|;)', href, re.I):
        href = ''  # the real target lives in onclick
    onclick = (re.search(r'onclick\s*=\s*(["\'])(.*?)\1', attrs, re.I | re.S) or [None, None, ''])[2]
    js = href if href.lower().startswith('javascript') else onclick
    if link_tpl and onclick and '(' in onclick:
        js, href = onclick, ''  # with a template, onclick ids beat a shared href (NTIS: every row href="/view.do")
    if (not href or href.startswith('#') or href.lower().startswith('javascript')) and js:
        path = re.search(r"['\"]((?:/|https?://)[^'\"]+)['\"]", js)
        args = re.findall(r"['\"]?([\w-]+)['\"]?", js.split('(', 1)[-1]) if '(' in js else []
        if link_tpl and args:  # the source's own template wins
            try:
                return urllib.parse.urljoin(base_url, link_tpl.format(id=args[0], args=args, *args))
            except (IndexError, KeyError):
                pass  # e.g. a menu link like javascript:link('notice') with too few args
        if path:  # e.g. fn_view('/subList/...?no=1') carries its own URL
            return urllib.parse.urljoin(base_url, html.unescape(path[1]))
        return ''
    if href and not href.startswith('#'):
        return urllib.parse.urljoin(base_url, html.unescape(href))
    return ''


def clean_title(title):
    title = re.sub(r'\s+20\d\d[-./]\d{1,2}[-./]\d{1,2}(\s+\d+)*\s*$', '', title)  # link text that also holds date/hits
    title = re.sub(r'^(\d{1,6}\s+)?(공지|NEW|new|모집중|접수중|마감|완료|진행중)?\s*', '', title)
    title = re.sub(r'\s*(첨부파일\s*\d*|페이지 이동|새창열기|새로운게시글|새글|NEW|new)$', '', title).strip()
    half = len(title) // 2  # some boards print the title twice (tooltip + link)
    return title[:half].strip() if len(title) > 20 and title[:half].strip() == title[half:].strip() else title


def parse_board(page, base_url, link_tpl='', split=''):
    """Rows (<tr>/<li>, or chunks cut at `split` for card layouts) holding a title link and a date."""
    page = re.sub(r'<(script|style)\b.*?</\1>|<!--.*?-->', '', page, flags=re.S | re.I)
    items, seen = [], set()
    blocks = ([('', b) for b in page.split(split)[1:]] if split
              else [(m[1], m[2]) for m in re.findall(r'<(tr|li)\b([^>]*)>(.*?)</\1>', page, re.S | re.I)])
    for row_attrs, block in blocks:
        candidates = []
        for a in re.finditer(r'<a\b([^>]*)>(.*?)</a>', block, re.S | re.I):
            attrs, label = a.group(1), text(a.group(2))
            full = text((re.search(r'title="([^"]*)"', attrs) or [None, ''])[1])
            if label.endswith(('...', '…')) and len(full) > len(label) - 3:
                label = full  # link text cut with "..."; the title attribute has it all
            if not label:
                label = text((re.search(r'title="([^"]*)"', attrs) or [None, ''])[1])
            candidates.append((clean_title(label), attrs))
        if 'onclick' in row_attrs.lower():  # whole row is clickable: <li onclick="goPage('/biz/1')">
            chunks = [text(c) for c in re.findall(r'<(?:strong|p|span|div|h\d|dt)\b[^>]*>(.*?)</', block, re.S | re.I)]
            chunks = [c for c in chunks if len(c) >= 8 and not DATE.search(c)]
            if chunks:
                candidates.append((clean_title(max(chunks, key=len)[:200]), row_attrs))
        best = None
        for title, attrs in candidates:
            if len(title) < 6 or SKIP_TITLES.match(title):
                continue
            url = resolve_link(attrs, base_url, link_tpl)
            if url and (best is None or len(title) > len(best[0])):
                best = (title, url)
        if not best or best[1] in seen:
            continue
        raw = text(block).replace(best[0], ' ')  # ignore dates inside the title (e.g. 공고번호 2026-01-0126)
        dates = [d for d in (iso_date(m) for m in DATE.findall(raw)) if d] or [d for d in (iso_date(m) for m in DATE.findall(text(block))) if d]
        if not dates:
            continue
        seen.add(best[1])
        period = (re.search(r'(20\d\d[-./]\d{1,2}[-./]\d{1,2})[^~]{0,12}~\s*(20\d\d[-./]\d{1,2}[-./]\d{1,2})', raw)
                  or re.search(r'(?:시작|접수)[^\d]{0,6}(20\d\d[-./]\d{1,2}[-./]\d{1,2}).{0,20}?(?:마감|종료)[^\d]{0,6}(20\d\d[-./]\d{1,2}[-./]\d{1,2})', raw))
        posted = re.search(r'(?:등록|작성|게시)[^\d]{0,6}(20\d\d[-./]\d{1,2}[-./]\d{1,2})', raw)
        if posted:
            dates = [iso_date(DATE.search(posted[1]).groups())]
        items.append({'title': best[0], 'url': best[1], 'date': max(dates) if not period else min(dates),
                      'period': f'{iso_date(DATE.search(period[1]).groups())} ~ {iso_date(DATE.search(period[2]).groups())}' if period else ''})
    return items


def with_param(url, key, value):
    parts = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if k != key] + [(key, str(value))]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def dig(data, path):
    for key in path.split('.'):
        data = data.get(key, {}) if isinstance(data, dict) else {}
    return data


def date_of(value):
    m = DATE.search(str(value or '')) or re.search(r'(20\d\d)(\d\d)(\d\d)', str(value or ''))
    return iso_date(m.groups()) if m else ''


def parse_json(source, n):
    """JSON list endpoints. `body` is a template: %N% page number, %START%/%END% row offsets."""
    size = source.get('page_size', 10)
    body = source.get('body', '').replace('%N%', str(n)).replace('%START%', str((n - 1) * size)).replace('%END%', str(n * size))
    is_json = body.startswith('{')
    data = json.loads(fetch(source['url'], data=body.encode() if body else None, headers={
        'Content-Type': 'application/json' if is_json else 'application/x-www-form-urlencoded',
        'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest', **source.get('headers', {})}))
    f = source['fields']  # {"title": key, "id": key, "date": key, "start": key, "end": key}
    out = []
    for r in dig(data, source['items_path']) or []:
        title, rid = text(str(dig(r, f['title']) or '')), dig(r, f['id'])
        if not title or rid in ({}, None, ''):
            continue
        start, end = date_of(dig(r, f.get('start', '_'))), date_of(dig(r, f.get('end', '_')))
        region = str(dig(r, f['region'])) if f.get('region') else ''  # multi-region feeds (창조경제혁신센터)
        slug = source.get('slugs', {}).get(region, source.get('default_slug', ''))
        row = {'title': title, 'url': source['link'].format(id=rid, slug=slug), 'date': date_of(dig(r, f.get('date', '_'))) or start or end,
               'period': f'{start} ~ {end}' if start and end else ''}
        if region and region != '통합':
            row['region'] = region
        out.append(row)
    return out


def collect_source(source, known=frozenset()):
    """`known` = URLs we already have; a multi-page board stops at the first page that brings nothing new."""
    rows, seen = [], set()
    for n in range(1, source.get('pages', 1) + 1):  # `page_param` names the page-number query key
        if source.get('parser') == 'json':
            fresh = [r for r in parse_json(source, n) if r['url'] not in seen]
        else:
            value = (n - 1) * source['page_step'] if source.get('page_step') else n  # offset paging: startCount=0,10,..
            page_url = source['url'] if n == 1 and not source.get('page_step') else with_param(source['url'], source['page_param'], value)
            body = source.get('post')  # some lists are POST-only AJAX endpoints
            page = fetch(page_url, data=body.encode() if body else None, insecure=source.get('insecure_ssl', False),
                         headers={'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest'} if body else None)
            if source.get('short_year'):  # boards that print 26-10-14
                page = re.sub(r'(?<![\d.-])(\d\d)([-.])(\d\d)\2(\d\d)(?![\d.-])', r'20\1-\3-\4', page)
            fresh = [r for r in parse_board(page, page_url, source.get('link', ''), source.get('split', '')) if r['url'] not in seen]
        if not fresh:
            break
        seen.update(r['url'] for r in fresh)
        rows += fresh
        if all(r['url'] in known for r in fresh):
            break
        time.sleep(source.get('delay', 1))
    keep, drop = source.get('include'), source.get('exclude')  # keyword filters for general notice boards
    rows = [r for r in rows if (not keep or re.search(keep, r['title'])) and not (drop and re.search(drop, r['title']))]
    today = datetime.now(KST).strftime('%Y-%m-%d')
    for r in rows:
        r['url'] = stable_url(r['url'])
        if r['date'] > today:  # some boards show the deadline, not the posting date
            r['period'] = r['period'] or f"~ {r['date']}"
            r['date'] = ''
        r.update(source_id=source['id'], source=source['name'], group=source['group'], region=r.get('region') or source.get('region', '전국'))
    return rows


VOLATILE = {'page', 'pageindex', 'cpage', 'pageno', 'nowpage', 'curpage', 'viewpage', 'pagenum', 'startpage', 'rowcnt', 'rows',
            'rowssel', 'sca', 'status', 'schtype', 'schtext', 'searchcnd', 'searchwrd', 'hashcode'}


def stable_url(url):
    """Drop session ids and list-state params so the same notice seen from page 1 or 2 is one item."""
    url = re.sub(r';jsessionid=[^?#]*', '', url, flags=re.I)
    parts = urllib.parse.urlsplit(url)
    # keep the other segments verbatim: some boards need bare flags like ?View&boardNo=1
    query = '&'.join(seg for seg in parts.query.split('&') if seg and seg.split('=', 1)[0].lower() not in VOLATILE)
    return urllib.parse.urlunsplit(parts._replace(query=query))


def sources():
    return [s for s in json.loads(SOURCES_FILE.read_text(encoding='utf-8')) if not s.get('disabled')]


BLOCK_AFTER = 2          # consecutive failed visits before we treat a site as blocking us
BLOCKED_RETRY = 24 * 3600  # then only knock once a day, so we never hammer a site that said no


def visit(source, prev, known):
    """One board visit with block detection. Returns (rows, status). Items already collected are never dropped."""
    now = time.time()
    if prev.get('next_try', 0) > now:  # backing off: keep the previous status as-is
        return [], {**prev, 'skipped': True}
    base = {'name': source['name'], 'home': source.get('home') or source['url'], 'robots_blocked': bool(source.get('robots_blocked')),
            'at': now, 'last_ok': prev.get('last_ok', 0)}
    try:
        rows = collect_source(source, known)
        error = '' if rows else '목록을 읽지 못했어요 (화면 구조가 바뀌었거나 접근이 막혔을 수 있음)'
    except urllib.error.HTTPError as e:
        rows, error = [], f'HTTP {e.code}' + (' · 접근 차단으로 보임' if e.code in (401, 403, 429, 451) else '')
    except Exception as e:  # one broken board must not stop the others
        rows, error = [], str(e)[:160]
    if rows:
        return rows, {**base, 'ok': True, 'count': len(rows), 'error': '', 'fails': 0, 'blocked': False, 'next_try': 0, 'last_ok': now}
    fails = prev.get('fails', 0) + 1
    blocked = fails >= BLOCK_AFTER
    return [], {**base, 'ok': False, 'count': 0, 'error': error, 'fails': fails, 'blocked': blocked,
                'next_try': now + BLOCKED_RETRY if blocked else 0}


def collect_all():
    known = {i['url']: i for i in workspace.load_data('support.json', [])}
    previous = workspace.load_data('support_status.json', {})
    now = datetime.now(KST).isoformat()
    added = 0

    def one(source):
        rows, STATUS[source['id']] = visit(source, previous.get(source['id'], {}), frozenset(known))
        return rows

    with ThreadPoolExecutor(8) as pool:
        for rows in pool.map(one, sources()):
            for r in rows:
                if r['url'] not in known:
                    added += 1
                    r['first_seen'] = now
                known[r['url']] = {**known.get(r['url'], {}), **r, 'last_seen': now}
    cutoff = (datetime.now(KST) - timedelta(days=180)).strftime('%Y-%m-%d')
    for i in known.values():
        i['date'] = i.get('date') or i['first_seen'][:10]  # undated / deadline-only rows: when we first saw them
    items = sorted((i for i in known.values() if i['date'] >= cutoff), key=lambda i: i['date'], reverse=True)
    workspace.save_data('support.json', items)
    workspace.save_data('support_status.json', STATUS)
    return len(items), added


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'try':
        rows = parse_board(fetch(sys.argv[2]), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
        print(len(rows), 'rows')
        for r in rows[:8]:
            print(' ', r['date'], '|', r['period'], '|', r['title'][:60], '|', r['url'][:110])
    elif sys.argv[1:] == ['run']:
        print(collect_all())
        for k, v in STATUS.items():
            print(('OK ' if v.get('ok') else 'XX ') + k, v.get('count'), v.get('error'), '(차단 의심)' if v.get('blocked') else '')
