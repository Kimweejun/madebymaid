"""Background collectors for the 받기 axis: AI타임스 articles, GitHub (trending + keyword search), Reddit.

Runs once when the server starts, then every 30 minutes. Results go to data/*.json and are read by workspace.py.
"""
import html
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import workspace

INTERVAL = 1800
UA = 'Mozilla/5.0 (madebymaid local collector)'
KST = timezone(timedelta(hours=9))
DEFAULT_SOURCES = {
    'reddit': ['LocalLLaMA', 'ClaudeAI', 'OpenAI', 'ChatGPT', 'MachineLearning'],
    'github_keywords': ['claude', 'mcp server', 'agent skills', 'llm agent'],
}
STATUS = {}  # name -> {ok, at, count, error}
_lock = threading.Lock()


def fetch(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(8_000_000)


def strip_tags(text):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text or ''))).strip()


def sources():
    s = workspace.load_data('community_sources.json', {})
    return {k: s.get(k, v) for k, v in DEFAULT_SOURCES.items()}


# ── AI타임스: the site's own "더보기" JSON endpoint, 20 articles per page ──
AIT_LIST = 'https://www.aitimes.com/news/ajaxArticlePaging.php'


def collect_aitimes():
    known = {a['id']: a for a in workspace.load_data('aitimes.json', [])}
    cutoff = (datetime.now(KST) - timedelta(days=90)).strftime('%Y-%m-%d')
    added = 0
    for page in range(1, 201):  # the site caps paging at 200
        q = urllib.parse.urlencode({'view_type': 'sm', 'list_per_page': 20, 'page_per_page': 10, 'page': page,
                                    'box_idxno': 0, 'list_page_limit': 200, 'total': 0})
        data = json.loads(fetch(f'{AIT_LIST}?{q}', {'X-Requested-With': 'XMLHttpRequest',
                                                    'Referer': 'https://www.aitimes.com/news/articleList.html?view_type=sm'}))
        rows = data.get('data') or []
        fresh = 0
        for r in rows:
            if r['idxno'] in known:
                continue
            known[r['idxno']] = {'id': r['idxno'], 'source': 'aitimes', 'title': strip_tags(r.get('title')),
                                 'summary': strip_tags(r.get('summary'))[:220],
                                 'url': 'https://www.aitimes.com/news/articleView.html?idxno=' + r['idxno'],
                                 'category': strip_tags(r.get('sectionTitle')) or '기타',
                                 'date': (r.get('reg_date') or '').replace(' ', 'T') + '+09:00'}
            fresh += 1
        added += fresh
        oldest = min((r.get('reg_date') or '9') for r in rows) if rows else ''
        # stop at the 3-month line, or once a page brings nothing new (incremental runs)
        if not rows or oldest[:10] < cutoff or (fresh == 0 and len(known) > 40):
            break
        time.sleep(1)  # be polite
    items = sorted((a for a in known.values() if a['date'][:10] >= cutoff), key=lambda a: a['date'], reverse=True)
    workspace.save_data('aitimes.json', items)
    return len(items), added


# ── GitHub: trending page (no key) + search API for recent repos per keyword ──
def parse_trending(page):
    items = []
    for block in page.split('<article class="Box-row')[1:]:
        block = re.sub(r'<svg.*?</svg>', '', block, flags=re.S)
        name = re.search(r'<h2[^>]*>.*?href="/([^"]+)"', block, re.S)
        if not name:
            continue
        desc = re.search(r'<p class="col-9[^"]*">(.*?)</p>', block, re.S)
        lang = re.search(r'itemprop="programmingLanguage">([^<]+)', block)
        stars = re.search(r'/stargazers"[^>]*>\s*([\d,]+)', block)
        today = re.search(r'([\d,]+) stars (today|this week|this month)', block)
        items.append({'id': name[1], 'title': name[1], 'url': 'https://github.com/' + name[1],
                      'summary': strip_tags(desc[1]) if desc else '', 'language': lang[1].strip() if lang else '',
                      'stars': int(stars[1].replace(',', '')) if stars else 0,
                      'gain': int(today[1].replace(',', '')) if today else 0})
    return items


def collect_github():
    result = {'trending_daily': [], 'trending_weekly': [], 'trending_monthly': [], 'search': {}}
    for since in ('daily', 'weekly', 'monthly'):  # stars gained today / this week / this month
        result['trending_' + since] = parse_trending(fetch(f'https://github.com/trending?since={since}').decode('utf-8', 'replace'))
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
    for kw in sources()['github_keywords']:
        q = urllib.parse.urlencode({'q': f'{kw} created:>{week_ago}', 'sort': 'stars', 'order': 'desc', 'per_page': 20})
        data = json.loads(fetch('https://api.github.com/search/repositories?' + q, {'Accept': 'application/vnd.github+json'}))
        result['search'][kw] = [{'id': r['full_name'], 'title': r['full_name'], 'url': r['html_url'],
                                 'summary': (r.get('description') or '')[:220], 'language': r.get('language') or '',
                                 'stars': r.get('stargazers_count', 0), 'date': r.get('created_at')}
                                for r in data.get('items', [])]
        time.sleep(2)
    result['collected'] = datetime.now(timezone.utc).isoformat()
    workspace.save_data('community_github.json', result)
    return sum(len(v) for k, v in result.items() if k.startswith('trending')) + sum(len(v) for v in result['search'].values()), 0


# ── Reddit: public RSS (Atom) per subreddit ──
def reddit_feed(sub, period):
    for wait in (0, 15, 45):  # Reddit answers 429 to bursts; back off and retry
        time.sleep(wait)
        try:
            return fetch(f'https://www.reddit.com/r/{urllib.parse.quote(sub)}/top/.rss?t={period}&limit=25',
                         {'User-Agent': 'windows:madebymaid:0.1 (personal feed reader)'})
        except urllib.error.HTTPError as error:
            if error.code != 429:
                raise
    raise OSError('Reddit이 요청을 잠시 막았어요 (429). 다음 갱신 때 다시 시도합니다.')


REDDIT_PERIODS = ('day', 'week', 'month')


def collect_reddit():
    """Each subreddit's own top lists (일간·주간·월간). Reddit's RSS has no vote counts, so rank = popularity."""
    atom = '{http://www.w3.org/2005/Atom}'
    old = workspace.load_data('community_reddit.json', {}).get('posts', [])
    posts, failed = [], []
    for sub in sources()['reddit']:
        for period in REDDIT_PERIODS:
            try:
                root = ET.fromstring(reddit_feed(sub, period))
            except (OSError, ET.ParseError):
                failed.append(f'{sub}({period})')
                posts += [p for p in old if p['sub'] == sub and p.get('period') == period]  # keep what we had
                continue
            entries = root.findall(atom + 'entry')
            for rank, e in enumerate(entries):
                link = e.find(atom + 'link')
                posts.append({'id': e.findtext(atom + 'id'), 'sub': sub, 'period': period, 'rank': rank + 1, 'of': len(entries),
                              'title': (e.findtext(atom + 'title') or '').strip(),
                              'url': link.get('href') if link is not None else '',
                              'author': (e.findtext(f'{atom}author/{atom}name') or '').replace('/u/', ''),
                              'summary': strip_tags(e.findtext(atom + 'content'))[:220],
                              'date': e.findtext(atom + 'published') or e.findtext(atom + 'updated')})
            time.sleep(2)
    workspace.save_data('community_reddit.json', {'collected': datetime.now(timezone.utc).isoformat(), 'posts': posts, 'failed': failed})
    if failed and len(failed) == len(sources()['reddit']) * len(REDDIT_PERIODS):
        raise OSError('Reddit에서 가져오지 못했어요 (요청 제한). 다음 갱신 때 다시 시도합니다.')
    return len(posts), 0


# ── translation: DeepL API Free (key in data/secrets.json), hard-capped below the 500,000 chars/month free quota ──
DEEPL_MONTHLY_CAP = 480_000  # leave headroom under DeepL Free's 500,000; counted locally and checked against DeepL's own meter


def deepl_key():
    return (workspace.load_data('secrets.json', {}).get('deepl') or {}).get('auth_key', '').strip()


def deepl_host():  # Free keys end in ':fx'
    return 'https://api-free.deepl.com' if deepl_key().endswith(':fx') else 'https://api.deepl.com'


def translate_budget():
    """Characters we may still send this month (0 when no key or the cap is reached)."""
    key = deepl_key()
    if not key:
        return 0
    usage = workspace.load_data('translate_usage.json', {})
    month = datetime.now(KST).strftime('%Y-%m')
    used = usage.get('chars', 0) if usage.get('month') == month else 0
    try:  # DeepL's meter wins when it is higher (e.g. the key is also used elsewhere)
        meter = json.loads(fetch(deepl_host() + '/v2/usage', {'Authorization': 'DeepL-Auth-Key ' + key}))
        used = max(used, meter.get('character_count', 0))
    except (OSError, ValueError):
        pass
    return max(0, DEEPL_MONTHLY_CAP - used)


def translate_many(texts, target='KO'):
    """Translate a batch in one request; returns None when skipped (no key / over budget / error)."""
    texts = [t[:1500] for t in texts]
    size = sum(len(t) for t in texts)
    if not size or size > translate_budget():
        return None
    body = urllib.parse.urlencode([('target_lang', target)] + [('text', t) for t in texts]).encode()
    req = urllib.request.Request(deepl_host() + '/v2/translate', data=body,
                                 headers={'Authorization': 'DeepL-Auth-Key ' + deepl_key(), 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = [t['text'] for t in json.load(r)['translations']]
    except (OSError, ValueError, KeyError):
        return None
    with _usage_lock:
        month = datetime.now(KST).strftime('%Y-%m')
        usage = workspace.load_data('translate_usage.json', {})
        used = usage.get('chars', 0) if usage.get('month') == month else 0
        workspace.save_data('translate_usage.json', {'month': month, 'chars': used + size})
    return out


_usage_lock = threading.Lock()


# ── US News: AI topic page embeds its story list as JSON ("stories":[...]); ~10 newest per visit ──
USNEWS_URL = 'https://www.usnews.com/topics/subjects/artificial-intelligence'
BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'


def usnews_stories(page):
    decoder, found, at = json.JSONDecoder(), {}, 0
    while (at := page.find('"stories":[', at)) >= 0:
        try:
            stories, _ = decoder.raw_decode(page[at + 10:])
        except ValueError:
            break
        for s in stories:
            if isinstance(s, dict) and s.get('headline') and s.get('permalink'):
                found[s.get('id') or s['permalink']] = s
        at += 10
    return list(found.values())


def collect_usnews():
    known = {a['id']: a for a in workspace.load_data('usnews.json', [])}
    page = fetch(USNEWS_URL, {'User-Agent': BROWSER_UA, 'Accept': 'text/html', 'Accept-Language': 'en-US'}).decode('utf-8', 'replace')
    now = datetime.now(KST)
    added = 0
    for s in usnews_stories(page):
        sid = s.get('id') or s['permalink']
        if sid in known:
            continue
        try:  # "Oct. 14, 2026" -> date; same-day stories get the time we first saw them so ordering stays useful
            day = datetime.strptime(s.get('pubdate', '').replace('Sept.', 'Sep.').replace('.', ''), '%b %d, %Y').replace(tzinfo=KST)
        except ValueError:
            day = now
        date = now if now - day < timedelta(days=2) else day
        title_en, summary_en = strip_tags(s['headline']), strip_tags(s.get('deck') or '')
        known[sid] = {'id': sid, 'source': 'usnews', 'title': title_en, 'title_en': title_en, 'summary': summary_en,
                      'summary_en': summary_en, 'translated': False, 'url': s['permalink'],
                      'category': strip_tags((s.get('overline') or {}).get('text')) or 'News', 'date': date.isoformat()}
        added += 1
    # translate anything still in English (new items, or ones skipped earlier for lack of key/budget)
    for item in sorted((a for a in known.values() if not a.get('translated')), key=lambda a: a['date'], reverse=True):
        out = translate_many([item['title_en'], item['summary_en']] if item['summary_en'] else [item['title_en']])
        if out is None:
            break
        item.update(title=out[0], summary=out[1] if len(out) > 1 else '', translated=True)
    cutoff = (now - timedelta(days=90)).isoformat()
    items = sorted((a for a in known.values() if a['date'] >= cutoff), key=lambda a: a['date'], reverse=True)
    workspace.save_data('usnews.json', items)
    return len(items), added


# ── 네이버 뉴스: official search API (developers.naver.com 검색 키, data/secrets.json) ──
OUTLETS = {'yna.co.kr': '연합뉴스', 'newsis.com': '뉴시스', 'news1.kr': '뉴스1', 'chosun.com': '조선일보', 'joongang.co.kr': '중앙일보',
           'donga.com': '동아일보', 'hani.co.kr': '한겨레', 'khan.co.kr': '경향신문', 'mk.co.kr': '매일경제', 'hankyung.com': '한국경제',
           'sedaily.com': '서울경제', 'edaily.co.kr': '이데일리', 'mt.co.kr': '머니투데이', 'etnews.com': '전자신문', 'zdnet.co.kr': '지디넷코리아',
           'dt.co.kr': '디지털타임스', 'aitimes.com': 'AI타임스', 'aitimes.kr': '인공지능신문', 'ddaily.co.kr': '디지털데일리', 'bloter.net': '블로터',
           'kbs.co.kr': 'KBS', 'imbc.com': 'MBC', 'sbs.co.kr': 'SBS', 'ytn.co.kr': 'YTN', 'fnnews.com': '파이낸셜뉴스', 'asiae.co.kr': '아시아경제',
           'heraldcorp.com': '헤럴드경제', 'inews24.com': '아이뉴스24', 'thebell.co.kr': '더벨', 'nocutnews.co.kr': '노컷뉴스',
           'newspim.com': '뉴스핌', 'ebn.co.kr': 'EBN', 'koreatimes.co.kr': '코리아타임스', 'koreaherald.com': '코리아헤럴드', 'seoul.co.kr': '서울신문',
           'kmib.co.kr': '국민일보', 'segye.com': '세계일보', 'munhwa.com': '문화일보', 'hankookilbo.com': '한국일보', 'ajunews.com': '아주경제',
           'bizwatch.co.kr': '비즈워치', 'businesspost.co.kr': '비즈니스포스트', 'etoday.co.kr': '이투데이', 'dailian.co.kr': '데일리안', 'news.mt.co.kr': '머니투데이'}


def outlet(url):
    host = urllib.parse.urlsplit(url).hostname or ''
    return next((name for dom, name in OUTLETS.items() if host == dom or host.endswith('.' + dom)), host.removeprefix('www.') or '기타')


def collect_naver():
    keys = workspace.load_data('secrets.json', {}).get('naver_search', {})
    if not keys.get('client_id') or not keys.get('client_secret'):
        raise OSError('네이버 개발자센터 검색 API 키가 필요해요 (data/secrets.json)')
    known = {a['id']: a for a in workspace.load_data('naver.json', [])}
    headers = {'X-Naver-Client-Id': keys['client_id'], 'X-Naver-Client-Secret': keys['client_secret']}
    added = 0
    for start in range(1, 1000, 100):  # the API serves at most the 1,000 newest results
        q = urllib.parse.urlencode({'query': 'AI', 'display': 100, 'start': start, 'sort': 'date'})
        rows = json.loads(fetch('https://openapi.naver.com/v1/search/news.json?' + q, headers)).get('items', [])
        fresh = 0
        for r in rows:
            url = r.get('originallink') or r.get('link')
            if url in known:
                continue
            known[url] = {'id': url, 'source': 'naver', 'title': strip_tags(r.get('title')), 'summary': strip_tags(r.get('description')),
                          'url': url, 'category': outlet(url), 'date': workspace.iso(r.get('pubDate'))}
            fresh += 1
        added += fresh
        if fresh == 0 or len(rows) < 100:
            break
        time.sleep(0.3)
    cutoff = (datetime.now(KST) - timedelta(days=90)).isoformat()
    items = sorted((a for a in known.values() if a['date'] >= cutoff), key=lambda a: a['date'], reverse=True)
    workspace.save_data('naver.json', items)
    return len(items), added


def collect_support():
    import support
    return support.collect_all()


JOBS = {'aitimes': collect_aitimes, 'usnews': collect_usnews, 'naver': collect_naver, 'github': collect_github, 'reddit': collect_reddit,
        'support': collect_support}


def run(name='*'):
    with _lock:  # one collection at a time (startup, 30-minute loop, manual refresh)
        for job in ([j for j in JOBS if j != 'support'] if name == '*' else [name]):  # support has its own 3-hour loop
            STATUS[job] = {**STATUS.get(job, {}), 'running': True}
            try:
                count, added = JOBS[job]()
                STATUS[job] = {'ok': True, 'at': time.time(), 'count': count, 'added': added, 'error': ''}
            except Exception as error:  # network/site changes must not kill the loop
                STATUS[job] = {**STATUS.get(job, {}), 'ok': False, 'running': False, 'at': time.time(), 'error': str(error)[:200]}


def start():
    """Collect once now (in the background), then every 30 minutes."""
    def loop():
        while True:
            run('*')
            time.sleep(INTERVAL)
    threading.Thread(target=loop, daemon=True, name='collectors').start()

    def support_loop():  # 지원사업 boards: once at start, then every 3 hours
        while True:
            run('support')
            time.sleep(3 * 3600)
    threading.Thread(target=support_loop, daemon=True, name='support').start()

    def outbox():
        while True:
            try:
                workspace.ingest_outbox()
            except OSError:
                pass
            try:
                import tagging
                tagging.daily()  # unclassified items -> 렘, once a day
            except Exception as e:  # ponytail: a bad batch must never stop the outbox loop
                print('tagging.daily', e)
            time.sleep(30)
    threading.Thread(target=outbox, daemon=True, name='outbox').start()


if __name__ == '__main__':
    for job in JOBS:
        t = time.time(); run(job); print(job, STATUS[job], f'{time.time() - t:.1f}s')
