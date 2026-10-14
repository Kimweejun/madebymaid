"""추천 점수 스킬: rule-based, deterministic importance scores for 지원사업 / 뉴스 / 커뮤니티.

Same input -> same score. Every score carries `reasons` (which rule gave how many points) so the
user can see why. All weights and keyword lists live in scoring.json; feedback (👍/👎) is stored in
data/feedback.json and used only to *check* and *suggest* changes, never to change rules silently.
"""
import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import workspace

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
REGIONS = ('서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주')
_rules = {'mtime': None, 'value': None}


def rules():
    f = ROOT / 'scoring.json'
    mtime = f.stat().st_mtime
    if _rules['mtime'] != mtime:
        _rules.update(mtime=mtime, value=json.loads(f.read_text(encoding='utf-8')))
    return _rules['value']


def hits(text, words):
    """Words found in text. Short Latin terms (AI, IP, GPU) must stand alone so 'MAID' doesn't count as 'AI'."""
    found = []
    for w in words:
        if re.fullmatch(r'[A-Za-z&]{1,4}', w):
            if re.search(r'(?<![A-Za-z])' + re.escape(w) + r'(?![A-Za-z])', text):
                found.append(w)
        elif w.lower() in text.lower():
            found.append(w)
    return found


def domain_fit(text):
    """0..1 and the matched 분야 names. One 분야 = 0.7, each extra +0.15; only generic AI words = 0.4."""
    r = rules()
    matched = [name for name, words in r['domains'].items() if hits(text, words)]
    core = [m for m in matched if m not in r.get('minor_domains', [])]
    if core:
        return min(1.0, 0.7 + 0.15 * (len(matched) - 1)), matched
    if matched:  # only generic R&D/사업화 words: weak signal on its own
        return 0.45, matched
    return (0.4, ['AI 일반']) if hits(text, r['ai_terms']) else (0.0, [])


def parse_day(value):
    m = re.search(r'(20\d\d)-(\d\d)-(\d\d)', value or '')
    return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=KST) if m else None


def days_left(item, today=None):
    end = parse_day((item.get('period') or '').split('~')[-1])
    if not end:
        return None
    today = today or datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    return (end - today).days


# ── 지원사업 ──
def score_support(item, today=None):
    r, w = rules()['support'], rules()['support']['weights']
    title = item.get('title', '')
    excluded = hits(title, r['exclude'])
    if excluded:
        return {'score': 0, 'reasons': [f'제외: {excluded[0]}'], 'excluded': True, 'days_left': days_left(item, today)}
    reasons, total = [], 0.0

    fit, matched = domain_fit(title)
    total += fit * w['domain']
    reasons.append(f"분야 {round(fit * w['domain'])}/{w['domain']}" + (f" ({', '.join(matched)})" if matched else ' (관련 분야 없음)'))

    region = item.get('region') or '전국'
    tag = re.match(r'\s*\[([^\]]+)\]', title)  # 기업마당 titles start with [경기], [경북] ...
    if tag and tag[1][:2] in REGIONS:
        region = tag[1][:2]
    if region == '전국' and hits(title, r['region_bonus_words']):
        region = '경북' if hits(title, ['경북', '경상북도', '구미', '포항', '경산', 'POSTECH', '포스텍']) else '대구'
    reg = r['region'].get(region, r['region']['other'])
    total += reg
    reasons.append(f"지역 {reg}/{w['region']} ({region})")

    plus, minus = hits(title, r['eligible_plus']), hits(title, r['eligible_minus'])
    elig = 1.0 if plus else (0.1 if minus else 0.5)
    total += elig * w['eligibility']
    reasons.append(f"신청 자격 {round(elig * w['eligibility'])}/{w['eligibility']}" + (f' ({plus[0]})' if plus else f' ({minus[0]} 대상)' if minus else ''))

    tplus, tminus = hits(title, r['type_plus']), hits(title, r['type_minus'])
    typ = 1.0 if tplus else (0.2 if tminus else 0.5)
    total += typ * w['type']
    reasons.append(f"지원 형태 {round(typ * w['type'])}/{w['type']}" + (f' ({tplus[0]})' if tplus else f' ({tminus[0]})' if tminus else ''))

    left = days_left(item, today)
    dl = 0.5 if left is None else 0.0 if left < 0 else 1.0 if left >= 14 else 0.8 if left >= 7 else 0.6 if left >= 3 else 0.4
    total += dl * w['deadline']
    reasons.append(f"남은 기간 {round(dl * w['deadline'])}/{w['deadline']} (" + ('기간 정보 없음' if left is None else '마감' if left < 0 else f'D-{left}') + ')')
    return {'score': round(total), 'reasons': reasons, 'excluded': False, 'days_left': left,
            'deadline_soon': left is not None and 0 <= left <= r['deadline_soon_days']}


# ── 뉴스 ──
STOP = {'있다', '했다', '위한', '대한', '통해', '관련', '공개', '발표', '기자', '뉴스', '오늘', '2026년', 'the', 'and', 'for', 'with'}


def tokens(title):
    return {t for t in re.findall(r'[가-힣A-Za-z0-9]{2,}', title.lower()) if t not in STOP}


def score_news_all(items, now=None):
    """Scores every item at once (화제성 needs the whole set). Returns list aligned with items."""
    r, w = rules(), rules()['news']['weights']
    now = now or datetime.now(KST)
    window = timedelta(hours=rules()['news']['buzz_window_hours'])
    parsed = []
    for i in items:
        try:
            dt = datetime.fromisoformat(i.get('date', '')) if i.get('date') else None
            dt = dt.replace(tzinfo=KST) if dt and not dt.tzinfo else dt
        except ValueError:
            dt = None
        parsed.append(dt)
    toks = [tokens(i.get('title', '')) for i in items]
    index = {}  # token -> recent item indexes (for 화제성)
    for n, (dt, tk) in enumerate(zip(parsed, toks)):
        if dt and now - dt <= window:
            for t in tk:
                index.setdefault(t, []).append(n)
    out = []
    for n, item in enumerate(items):
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        fit, matched = domain_fit(text)
        low = hits(item.get('title', ''), r['low_value'])
        if low and not matched:
            out.append({'score': 0, 'reasons': [f'제외: {low[0]} 단독 이슈'], 'excluded': True})
            continue
        reasons = [f"분야 {round(fit * w['domain'])}/{w['domain']}" + (f" ({', '.join(matched)})" if matched else ' (관련 분야 없음)')]
        others = set()
        if parsed[n] and now - parsed[n] <= window:
            common = Counter(m for t in toks[n] for m in index.get(t, []) if m != n)
            for m, c in common.items():
                if items[m].get('source') != item.get('source') and c >= 3 and c / max(1, len(toks[n] | toks[m])) >= 0.3:
                    others.add(items[m].get('source'))
        buzz = min(1.0, len(others) / 2)
        reasons.append(f"화제성 {round(buzz * w['buzz'])}/{w['buzz']}" + (f" ({len(others)}개 다른 출처에서도 보도)" if others else ''))
        age = (now - parsed[n]).total_seconds() / 3600 if parsed[n] else 999
        fresh = 0.5 ** (max(0, age) / rules()['news']['fresh_half_life_hours'])
        reasons.append(f"최신성 {round(fresh * w['fresh'])}/{w['fresh']}" + (f' ({int(age)}시간 전)' if age < 999 else ''))
        src = r['news']['trusted_sources'].get(item.get('source'), 3)
        reasons.append(f"출처 {src}/{w['source']}")
        out.append({'score': round(fit * w['domain'] + buzz * w['buzz'] + fresh * w['fresh'] + src), 'reasons': reasons, 'excluded': False})
    return out


# ── 커뮤니티 (인기만으로 판단) ──
def score_rank(items, gain_key=None):
    """GitHub: stars gained in the period (relative to the top repo). Reddit: position in Reddit's own top list."""
    if gain_key:
        top = max((i.get(gain_key) or 0 for i in items), default=0) or 1
        return [{'score': round(100 * (i.get(gain_key) or 0) / top), 'reasons': [f"기간 스타 +{(i.get(gain_key) or 0):,}"]} for i in items]
    n = max(1, len(items))
    return [{'score': round(100 * (1 - k / n)), 'reasons': [f'인기 순위 {k + 1}위']} for k in range(len(items))]


# ── cached scoring of the stored datasets ──
_cache = {}


def scored(name, loader, scorer):
    """Score a whole dataset once per file change (and at most every 10 minutes for time-based parts)."""
    f = workspace.DATA / name
    key = (f.stat().st_mtime if f.exists() else 0, int(time.time() // 600), rules_mtime())
    if _cache.get(name, (None,))[0] != key:
        items = loader()
        _cache[name] = (key, [{**i, **s} for i, s in zip(items, scorer(items))])
    return _cache[name][1]


def rules_mtime():
    return (ROOT / 'scoring.json').stat().st_mtime


def support_scored():
    return scored('support.json', lambda: [{**i, 'category': i.get('source')} for i in workspace.load_data('support.json', [])],
                  lambda items: [score_support(i) for i in items])


def news_scored(names):
    items = [{**i, 'source': n} for n in names for i in workspace.load_data(workspace.NEWS_SOURCES[n], [])]
    key = '+'.join(names)
    f_mtimes = tuple((workspace.DATA / workspace.NEWS_SOURCES[n]).stat().st_mtime if (workspace.DATA / workspace.NEWS_SOURCES[n]).exists() else 0 for n in names)
    cache_key = (f_mtimes, int(time.time() // 600), rules_mtime())
    if _cache.get('news:' + key, (None,))[0] != cache_key:
        all_items = [{**i, 'source': n} for n in workspace.NEWS_SOURCES for i in workspace.load_data(workspace.NEWS_SOURCES[n], [])]
        scores = {id(x): s for x, s in zip(all_items, score_news_all(all_items))}  # 화제성 looks across all sources
        by_url = {x.get('url'): scores[id(x)] for x in all_items}
        _cache['news:' + key] = (cache_key, [{**i, **by_url.get(i.get('url'), {'score': 0, 'reasons': []})} for i in items])
    return _cache['news:' + key][1]


# ── 피드백 ──
def add_feedback(kind, item, vote):
    entries = [e for e in workspace.load_data('feedback.json', []) if not (e['kind'] == kind and e['url'] == item['url'])]
    if vote in ('up', 'down'):
        entries.append({'kind': kind, 'url': item['url'], 'title': item.get('title', ''), 'vote': vote,
                        'score': item.get('score'), 'at': datetime.now(KST).isoformat()})
    workspace.save_data('feedback.json', entries)
    return {e['url']: e['vote'] for e in entries if e['kind'] == kind}


def feedback_report():
    """How well the rules agree with 👍/👎, plus keyword suggestions (never applied automatically)."""
    entries = workspace.load_data('feedback.json', [])
    report = {}
    for kind in ('support', 'news'):
        current = {i['url']: i for i in (support_scored() if kind == 'support' else news_scored(list(workspace.NEWS_SOURCES)))}
        ups = [current[e['url']] for e in entries if e['kind'] == kind and e['vote'] == 'up' and e['url'] in current]
        downs = [current[e['url']] for e in entries if e['kind'] == kind and e['vote'] == 'down' and e['url'] in current]
        agree = sum(1 for i in ups if i['score'] >= 50) + sum(1 for i in downs if i['score'] < 50)
        words_up = Counter(t for i in ups for t in tokens(i['title']))
        known = {w.lower() for ws in rules()['domains'].values() for w in ws}
        suggest_add = [w for w, c in words_up.most_common(30) if c >= 2 and w not in known][:8]
        bad = Counter(m for i in downs for m in domain_fit(i['title'])[1] if m != 'AI 일반')
        report[kind] = {'up': len(ups), 'down': len(downs), 'agreement': round(100 * agree / max(1, len(ups) + len(downs))),
                        'avg_up': round(sum(i['score'] for i in ups) / max(1, len(ups))),
                        'avg_down': round(sum(i['score'] for i in downs) / max(1, len(downs))),
                        'suggest_keywords': suggest_add, 'suspicious_domains': [d for d, c in bad.most_common(3) if c >= 2]}
    return report
