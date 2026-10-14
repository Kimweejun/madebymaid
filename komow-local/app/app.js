'use strict';
/* New UI over the existing local backend (/api/local/*) and tool runtimes (/komow_app/labs/*).
   Maids: 렘 = GPT, 람 = Claude (pixel sprites cut from ~/.clawdex/pets/(rem|ram)/spritesheet.webp). */
const SITE = {name: '메이드 바이 메이드'};
const MAIDS = [{id: 'rem', name: '렘', engine: 'GPT'}, {id: 'ram', name: '람', engine: 'Claude'}];

const $ = (s, r = document) => r.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const safeURL = (v, local) => { try { const u = new URL(v, location.origin); if (!/^https?:$/.test(u.protocol) || (local && u.origin !== location.origin)) return ''; return u.href; } catch { return ''; } };
const whenTime = v => { const d = new Date(v); return isNaN(d) ? (v || '') : d.toLocaleString('ko-KR', {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'}); };
const when = v => { if (!v) return ''; const d = new Date(v); return isNaN(d) ? v : d.toLocaleDateString('ko-KR', {year: 'numeric', month: 'short', day: 'numeric'}); };
const size = n => n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(1) + ' MB';
const empty = t => `<div class="empty">${esc(t)}</div>`;
let toastTimer;
const toast = m => { $('#toast').textContent = m; $('#toast').classList.add('on'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('on'), 2800); };
async function api(url, method = 'GET', data) {
  const r = await fetch(url, {method, headers: data ? {'Content-Type': 'application/json'} : {}, body: data ? JSON.stringify(data) : undefined});
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `요청 실패 (${r.status})`);
  return body;
}
const qs = o => new URLSearchParams(Object.entries(o).filter(([, v]) => v !== '' && v != null)).toString();

const I = {
  home: '<path d="M4 10.5 12 4l8 6.5"/><path d="M6 9.5V20h12V9.5"/>',
  news: '<rect x="4" y="5" width="13" height="14" rx="2"/><path d="M17 9h3v8a2 2 0 0 1-2 2"/><path d="M8 9h5M8 12.5h5M8 16h3"/>',
  support: '<rect x="3.5" y="7.5" width="17" height="12" rx="2"/><path d="M9 7.5v-2h6v2M3.5 12.5h17"/>',
  community: '<path d="M4 6h10a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H9l-4 3v-3H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"/><path d="M16 10h4a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-1v2l-3-2h-3"/>',
  workshop: '<path d="M14.5 6.5a4 4 0 0 0-5.3 5.3L4 17l3 3 5.2-5.2a4 4 0 0 0 5.3-5.3l-2.5 2.5-2.5-.5-.5-2.5z"/>',
  outputs: '<path d="M3.5 7.5A2 2 0 0 1 5.5 5.5h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
  skills: '<path d="M12 3 4 7.5v9L12 21l8-4.5v-9z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
  face: '<circle cx="12" cy="12" r="9"/><circle cx="9" cy="10.5" r=".8" fill="currentColor"/><circle cx="15" cy="10.5" r=".8" fill="currentColor"/><path d="M9 15c1.6 1.3 4.4 1.3 6 0"/>'
};
const svg = d => `<svg viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
const PAGES = {
  home: ['홈', '오늘 확인할 것들을 한눈에'],
  news: ['뉴스룸', 'AI타임스·네이버·US News와 구독 피드 · 30분마다 갱신'],
  support: ['지원사업', '전국·대구경북 지원사업 공고 · 3시간마다 갱신'],
  community: ['커뮤니티', 'GitHub·Reddit에서 받아 와 바로 실험으로 넘깁니다'],
  workshop: ['작업 공방', '도구를 실행하고, 렘·람에게 맡긴 실험을 관리합니다'],
  outputs: ['산출물 정리', '만든 파일을 폴더별로 보관합니다'],
  skills: ['스킬관리', '스킬을 찾고 고칩니다 · 시험 기록은 작업 공방 > 실험']
};
const S = {page: 'home', sub: {}, cache: {}};

/* ---------- shell ---------- */
function buildShell() {
  $('#nav').innerHTML = Object.entries(PAGES).map(([id, [label]]) => `<a href="#${id}" data-page="${id}">${svg(I[id])}<span>${label}</span></a>`).join('');
  $('#side-maids').innerHTML = MAIDS.map(m => `<div class="side-maid" data-maid="${m.id}"><span class="sprite mini" aria-hidden="true"></span><span><b>${m.name}</b> <small>${m.engine}</small><span class="maid-state">확인 중…</span></span></div>`).join('');
  pollMaids();
  const saved = (() => { try { return localStorage.getItem('ws-theme'); } catch { return null; } })();
  setTheme(saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  $('#theme').onclick = () => { const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; setTheme(t); try { localStorage.setItem('ws-theme', t); } catch {} };
  $('#menu').onclick = () => { const o = $('#side').classList.toggle('open'); $('#menu').setAttribute('aria-expanded', o); };
}
/* 렘·람 live state from /api/local/maids (Codex / Claude Code logs), polled every 3 s */
const FRAMES = [6, 8, 8, 4, 5, 8, 6, 6, 6]; // frames per sprite-sheet row
let maidState = {};
function spriteStyle(row) { return `--row:${row};--n:${FRAMES[row] || 6}`; }
function paintMaids() {
  document.querySelectorAll('[data-maid]').forEach(el => {
    const m = maidState[el.dataset.maid]; if (!m) return;
    el.querySelector('.sprite').setAttribute('style', spriteStyle(m.row));
    el.dataset.state = m.state;
    const label = el.querySelector('.maid-state');
    if (label) label.textContent = m.available === false ? `${m.source} 기록 없음` : m.label + (m.detail && m.state === 'working' ? ` · ${m.detail}` : '');
    el.title = `${m.name}(${m.engine}) · ${m.source}: ${m.label}`;
  });
  const waiting = Object.values(maidState).filter(m => m.state === 'waiting' || m.state === 'done');
  document.title = (waiting.length ? `● ${waiting.map(m => m.name).join('·')} 확인 필요 · ` : '') + PAGES[S.page][0] + ' · ' + SITE.name;
}
async function pollMaids() {
  try { maidState = await api('/api/local/maids'); paintMaids(); } catch {}
  setTimeout(pollMaids, document.hidden ? 15000 : 3000);
}
function setTheme(t) { document.documentElement.dataset.theme = t; $('#theme').textContent = t === 'dark' ? '밝은 테마로' : '어두운 테마로'; }
function route() {
  const [page, ...rest] = location.hash.slice(1).split('/');
  S.page = PAGES[page] ? page : 'home';
  S.arg = decodeURIComponent(rest.join('/'));
  if (S.page === 'workshop' && S.arg.startsWith('lab')) S.sub.workshop = 'lab';
  document.querySelectorAll('#nav a').forEach(a => a.dataset.page === S.page ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
  $('#title').textContent = PAGES[S.page][0]; $('#subtitle').textContent = PAGES[S.page][1];
  paintMaids();
  $('#side').classList.remove('open');
  RENDER[S.page]();
}
function tabs(key, list) {
  const cur = S.sub[key] || list[0][0];
  return `<div class="tabs" role="tablist">${list.map(([id, label]) => `<button role="tab" data-subtab="${key}:${id}" aria-selected="${cur === id}">${esc(label)}</button>`).join('')}</div>`;
}
const sub = (key, def) => S.sub[key] || def;

/* ---------- searchable list (news / support / github) ---------- */
function feedList(cfg) {
  // cfg: {key, url, extra, render(item)}
  const st = S.cache[cfg.key] ||= {q: '', cat: '', page: 0, items: [], total: 0, categories: []};
  const view = $('#list-host');
  view.innerHTML = `<div class="bar"><input type="search" class="grow" id="lq" placeholder="검색" value="${esc(st.q)}" aria-label="검색"><span class="muted" id="lcount"></span></div>${cfg.afterSearch || ''}<div class="chips" id="lcats"></div><div class="card"><div class="list" id="litems">${empty('불러오는 중…')}</div></div><div class="more"><button class="btn" id="lmore" hidden>더 보기</button></div>`;
  const load = async reset => {
    if (reset) { st.page = 0; st.items = []; }
    try {
      const d = await api(cfg.url + '?' + qs({...cfg.extra, q: st.q, cat: st.cat, page: st.page}));
      st.items = st.items.concat(d.items); st.total = d.total; st.categories = d.categories || [];
      if (cfg.onData && S.page === cfg.page) cfg.onData(d);
    } catch (e) { toast(e.message); }
    if (S.page !== cfg.page) return;
    $('#lcount').textContent = `${st.total.toLocaleString()}건`;
    $('#lcats').innerHTML = st.categories.length > 1 ? ['', ...st.categories].map(c => `<button class="chip" data-cat="${esc(c)}" aria-pressed="${st.cat === c}">${esc(c || '전체')}</button>`).join('') : '';
    $('#litems').innerHTML = st.items.map(cfg.render).join('') || empty('결과가 없어요.');
    $('#lmore').hidden = st.items.length >= st.total;
  };
  let timer;
  $('#lq').oninput = e => { clearTimeout(timer); timer = setTimeout(() => { st.q = e.target.value.trim(); load(true); }, 250); };
  $('#lcats').onclick = e => { const b = e.target.closest('[data-cat]'); if (b) { st.cat = b.dataset.cat; load(true); } };
  $('#lmore').onclick = () => { st.page++; load(false); };
  load(true);
}
const linkItem = (i, meta, summary) => { const u = safeURL(i.url); return `<${u ? `a href="${esc(u)}" target="_blank" rel="noopener noreferrer"` : 'div'} class="item"><div class="item-title">${esc(i.title)}</div><div class="item-meta">${meta}</div>${summary ? `<div class="item-sum">${esc(summary)}</div>` : ''}</${u ? 'a' : 'div'}>`; };

/* ---------- pages ---------- */
const RENDER = {};
RENDER.home = async () => {
  const v = $('#view');
  const today = new Date().toLocaleDateString('ko-KR', {month: 'long', day: 'numeric', weekday: 'long'});
  const box = (id, title, link, label) => `<section class="card"><h2>${title}${link ? `<a href="${link}">${label || '전체 보기'}</a>` : ''}</h2><div class="list" id="${id}">${empty('불러오는 중…')}</div></section>`;
  v.innerHTML = `<div class="grid home">
    <section class="card hero"><div class="hero-text"><span class="eyebrow">madebymaid</span><h2>${esc(today)}</h2><p id="h-brief">오늘 들어온 소식과 렘·람의 작업을 모아 왔어요.</p></div><div class="maids">${MAIDS.map(m => `<figure class="maid" data-maid="${m.id}"><span class="sprite" role="img" aria-label="${m.name}"></span><figcaption><b>${m.name} · ${m.engine}</b><span class="maid-state">확인 중…</span></figcaption></figure>`).join('')}</div></section>
    <div class="grid g4" id="h-stats">${[['news', '뉴스'], ['support', '지원사업 공고'], ['community', 'GitHub 트렌딩'], ['community', 'Reddit 인기글']].map(([href, l]) => `<a class="card stat" href="#${href}"><span>오늘 ${l}</span><b>—</b><small></small></a>`).join('')}</div>
    <div class="grid g2">${box('h-news', '추천 뉴스', '#news', '뉴스룸')}${box('h-support', '추천 지원사업', '#support', '지원사업')}</div>
    <div class="grid g2">${box('h-due', '마감 챙기기', '#support', '관심 공고')}${box('h-work', '렘·람 작업', '#workshop/lab', '작업 공방')}</div>
    <div class="grid g2">${box('h-reports', '최근 보고서', 'https://kimweejun.github.io/madebymaid-reports/', '보고서 목록 ↗')}${box('h-files', '최근 산출물', '#outputs', '산출물 정리')}</div>
  </div>`;
  paintMaids();
  let d; try { d = await api('/api/local/home'); } catch (e) { toast(e.message); return; }
  if (S.page !== 'home') return;
  const c = d.counts, bySrc = d.news_by_source || {};
  const nums = [[c.news, Object.entries(bySrc).map(([k, n]) => `${SOURCE_LABEL[k] || k} ${n.toLocaleString()}`).join(' · ')], [c.support, '오늘 게시된 공고'], [c.github, '오늘 스타가 많이 는 저장소'], [c.reddit, '서브레딧별 오늘 추천 순위']];
  document.querySelectorAll('#h-stats .stat').forEach((el, i) => { el.querySelector('b').textContent = (nums[i][0] ?? 0).toLocaleString(); el.querySelector('small').textContent = nums[i][1]; });
  const running = d.work.filter(x => x.status === 'running').length, arrived = d.work.filter(x => x.status === 'arrived').length;
  $('#h-brief').textContent = `추천 공고 ${d.top_support.length}건, 마감 임박 ${d.soon.length}건${running ? `, 렘·람이 ${running}건 진행 중` : ''}${arrived ? `, 확인할 결과 ${arrived}건` : ''}이에요.`;
  $('#h-news').innerHTML = d.top_news.map(i => scoredItem('news', i, `<span class="tag accent">${esc(SOURCE_LABEL[i.source] || i.source)}</span><span>${esc(whenTime(i.date))}</span>`)).join('') || empty('추천할 기사가 아직 없어요.');
  $('#h-support').innerHTML = d.top_support.map(i => scoredItem('support', i, `${dday(i.days_left)}<span class="tag accent">${esc(i.source)}</span>${i.period ? `<span>접수 ${esc(i.period)}</span>` : ''}`)).join('') || empty('추천할 공고가 아직 없어요.');
  const seen = new Set();
  const due = [...d.stars.map(i => ({...i, star: true})), ...d.soon].filter(i => !seen.has(i.url) && seen.add(i.url)).slice(0, 6);
  $('#h-due').innerHTML = due.map(i => linkItem(i, `${dday(i.days_left)}${i.star ? '<span class="tag">★ 관심</span>' : ''}<span>${esc(i.source)}</span>`)).join('') || empty('관심 공고나 마감 임박 공고가 없어요.');
  $('#h-work').innerHTML = d.work.map(x => { const [label, tone] = EXP_STATUS[x.status] || ['', '']; return `<a class="item" href="#workshop/lab/${esc(x.no)}"><div class="item-title">${esc(x.title)}</div><div class="item-meta"><span class="tag ${tone}">${label}</span><span>${esc(x.no)}</span><span>${x.maids.map(m => m === 'rem' ? '렘' : '람').join('·')}</span><span>${esc(EXP_KINDS.find(k => k[0] === x.kind)?.[1] || '')}</span></div></a>`; }).join('') || empty('맡긴 실험이 없어요. 뉴스룸이나 커뮤니티에서 실험하기를 눌러 보세요.');
  $('#h-reports').innerHTML = d.reports.map(r => `<a class="item" href="${esc(safeURL(r.web))}" target="_blank" rel="noopener noreferrer"><div class="item-title">${esc(r.title)}</div><div class="item-meta"><span class="tag accent">${esc(r.no)}</span><span>웹으로 보기 ↗</span></div></a>`).join('') || empty('아직 올린 보고서가 없어요.');
  $('#h-files').innerHTML = d.files.map(f => `<a class="item" href="/api/local/files/${esc(f.id)}" download><div class="item-title">${esc(f.name)}</div><div class="item-meta"><span>${esc(f.folder || '미분류')}</span><span>${size(f.size)}</span><span>${esc(when(f.created))}</span></div></a>`).join('') || empty('아직 보관한 파일이 없어요.');
};

/* collector status line + manual refresh, shared by 뉴스룸·커뮤니티 */
function collectorBar(job, status) {
  const s = status || {};
  const text = s.running ? '새로 가져오는 중…' : s.at ? `${new Date(s.at * 1000).toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'})}에 갱신${s.ok ? '' : ' · 실패: ' + s.error}` : '서버 시작 후 첫 수집 중…';
  return `<div class="bar"><span class="tag ${s.ok === false ? 'warn' : 'accent'}">30분마다 자동 갱신</span><span class="muted">${esc(text)}</span><span class="grow"></span><button class="btn small" data-collect="${job}">지금 새로고침</button></div>`;
}
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-collect]'); if (!b) return;
  b.disabled = true; b.textContent = '가져오는 중…';
  await api('/api/local/collect', 'POST', {job: b.dataset.collect}).catch(err => toast(err.message));
  setTimeout(() => RENDER[S.page](), 4000);
});

/* 추천 점수: badge + reasons + 👍/👎 (scoring.py decides; votes only check and tune the rules) */
const scoreTone = n => n >= 75 ? 'ok' : n >= 50 ? 'accent' : '';
function scoredItem(kind, i, meta, summary) {
  const u = safeURL(i.url);
  const why = (i.reasons || []).join('\n');
  const data = esc(JSON.stringify({kind, url: i.url, title: i.title, score: i.score}));
  const exp = kind === 'news' ? expButton(i) : '';
  const star = kind === 'support' ? `<button class="vote star${i.starred ? ' on' : ''}" data-star="${esc(i.url)}" title="관심 공고" aria-label="관심 공고" aria-pressed="${!!i.starred}">${i.starred ? '★' : '☆'}</button>` : '';
  return `<div class="item scored${i.closed ? ' closed' : ''}"><div class="scored-body"><${u ? `a href="${esc(u)}" target="_blank" rel="noopener noreferrer"` : 'span'} class="item-title">${esc(i.title)}</${u ? 'a' : 'span'}><div class="item-meta"><span class="tag score ${scoreTone(i.score)}" title="${esc(why)}">추천 ${i.score ?? '-'}</span>${meta}</div>${summary ? `<div class="item-sum">${esc(summary)}</div>` : ''}<details class="why"><summary>점수 이유</summary>${(i.reasons || []).map(r => `<div>${esc(r)}</div>`).join('')}</details></div><div class="votes" data-vote-item="${data}">${exp}${star}<button class="vote${i.vote === 'up' ? ' on' : ''}" data-vote="up" title="중요해요" aria-label="중요해요" aria-pressed="${i.vote === 'up'}">👍</button><button class="vote${i.vote === 'down' ? ' on' : ''}" data-vote="down" title="중요하지 않아요" aria-label="중요하지 않아요" aria-pressed="${i.vote === 'down'}">👎</button></div></div>`;
}
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-vote]'); if (!b) return;
  const box = b.closest('[data-vote-item]'); const item = JSON.parse(box.dataset.voteItem);
  const vote = b.classList.contains('on') ? '' : b.dataset.vote;  // clicking again cancels
  try {
    await api('/api/local/feedback', 'POST', {...item, vote});
    box.querySelectorAll('.vote').forEach(x => { const on = x.dataset.vote === vote; x.classList.toggle('on', on); x.setAttribute('aria-pressed', on); });
    toast(vote ? '피드백을 남겼어요. 기준 점검에 쓰여요.' : '피드백을 취소했어요.');
  } catch (err) { toast(err.message); }
});
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-star]'); if (!b) return;
  const on = !b.classList.contains('on');
  try {
    const r = await api('/api/local/bookmarks', 'POST', {url: b.dataset.star, on});
    b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); b.textContent = on ? '★' : '☆';
    const n = $('#star-n'); if (n) n.textContent = ' ' + r.count;
    toast(on ? '관심 공고에 담았어요.' : '관심 공고에서 뺐어요.');
  } catch (err) { toast(err.message); }
});
document.addEventListener('click', e => { const a = e.target.closest('[data-goto-area]'); if (a) S.cache.supportArea = a.dataset.gotoArea; });
const dday = n => n == null ? '' : n < 0 ? '<span class="tag">마감</span>' : n === 0 ? '<span class="tag warn">오늘 마감</span>' : n <= 7 ? `<span class="tag warn">D-${n}</span>` : `<span class="tag">D-${n}</span>`;
const SORTS = [['', '최신순'], ['score', '추천순']];
const sortBar = (key, cur) => `<div class="seg" role="group" aria-label="정렬">${SORTS.map(([id, label]) => `<button data-sort="${key}:${id}" aria-pressed="${cur === id}">${label}</button>`).join('')}</div>`;
document.addEventListener('click', e => {
  const b = e.target.closest('[data-sort]'); if (!b) return;
  const [key, id] = b.dataset.sort.split(':'); S.cache[key] = id; RENDER[S.page]();
});
async function feedbackSummary(kind) {
  const r = (await api('/api/local/feedback/report').catch(() => ({})))[kind];
  if (!r || !(r.up + r.down)) return '<p class="muted">👍/👎를 누르면 추천 기준이 맞는지 점검할 수 있어요.</p>';
  return `<p class="muted">피드백 👍 ${r.up} · 👎 ${r.down} · 기준 일치율 ${r.agreement}% (👍 평균 ${r.avg_up}점, 👎 평균 ${r.avg_down}점)${r.suggest_keywords.length ? ` · 추가 검토할 낱말: ${r.suggest_keywords.map(esc).join(', ')}` : ''}${r.suspicious_domains.length ? ` · 점검할 분야: ${r.suspicious_domains.map(esc).join(', ')}` : ''}</p>`;
}

const NEWS_SOURCES = [['', '전체'], ['aitimes', 'AI타임스'], ['naver', '네이버'], ['usnews', 'US News']];
const SOURCE_LABEL = Object.fromEntries(NEWS_SOURCES);
RENDER.news = () => {
  const t = sub('news', 'news');
  $('#view').innerHTML = tabs('news', [['news', '뉴스'], ['rss', '구독 피드']]) + '<div id="status-host"></div><div id="list-host"></div>';
  if (t !== 'news') return renderRSS();
  const src = S.cache.newsSource || '';
  const order = S.cache.newsSort || '';
  const sourceBar = `<div class="bar" style="margin-bottom:8px">${sortBar('newsSort', order)}</div><div class="chips source-chips" id="nsrc">${NEWS_SOURCES.map(([id, label]) => `<button class="chip source" data-nsrc="${id}" aria-pressed="${src === id}">${label}<span class="n" data-count="${id}"></span></button>`).join('')}</div>`;
  feedList({key: 'news-' + src + order, page: 'news', url: '/api/local/news', extra: {source: src, sort: order}, afterSearch: sourceBar,
    onData: async d => {
      const st = d.status || {};
      const fb = order === 'score' ? await feedbackSummary('news') : '';
      if (S.page !== 'news') return;
      $('#status-host').innerHTML = collectorBar(src || 'aitimes', src ? st[src] : st.aitimes) + fb +
        (src === 'naver' && st.naver?.error ? `<p class="muted">${esc(st.naver.error)}</p>` : '') +
        (src === 'usnews' && d.items.some(i => i.translated === false) ? '<p class="muted">DeepL 키가 들어오면 제목·요약을 한국어로 바꿔 보여드려요. 지금은 원문이에요.</p>' : '');
      const total = Object.values(d.counts || {}).reduce((a, b) => a + b, 0);
      document.querySelectorAll('[data-count]').forEach(el => { const c = el.dataset.count ? d.counts?.[el.dataset.count] : total; el.textContent = c == null ? '' : ' ' + c.toLocaleString(); });
    },
    render: i => scoredItem('news', i, `${!src ? `<span class="tag accent">${esc(SOURCE_LABEL[i.source] || i.source)}</span>` : ''}<span class="tag">${esc(i.category)}</span><span>${esc(whenTime(i.date))}</span>${i.translated && i.title_en ? `<span title="${esc(i.title_en)}">원문: ${esc(i.title_en.slice(0, 60))}${i.title_en.length > 60 ? '…' : ''}</span>` : ''}`, i.summary)});
  $('#nsrc').onclick = e => { const b = e.target.closest('[data-nsrc]'); if (b) { S.cache.newsSource = b.dataset.nsrc; RENDER.news(); } };
};
async function renderRSS(refresh) {
  const host = $('#list-host');
  host.innerHTML = empty('피드를 가져오는 중…');
  let d; try { d = await api('/api/local/feeds' + (refresh ? '?refresh=1' : '')); } catch (e) { host.innerHTML = empty(e.message); return; }
  if (S.page !== 'news') return;
  const f = S.cache.rssFilter || '';
  const items = d.items.filter(i => !f || i.source === f).sort((a, b) => (Date.parse(b.date) || 0) - (Date.parse(a.date) || 0));
  host.innerHTML = `<form class="bar" id="feed-add"><input class="grow" type="url" id="feed-url" required placeholder="RSS·Atom 주소 추가 (예: https://github.com/사용자/저장소/releases.atom)" aria-label="피드 주소"><input id="feed-title" placeholder="이름 (선택)" maxlength="80" aria-label="피드 이름"><button class="btn primary">구독</button><button class="btn" type="button" id="feed-refresh">새로고침</button></form>
    <div class="chips"><button class="chip" data-rss="" aria-pressed="${!f}">전체 ${d.items.length}</button>${d.feeds.map(x => `<button class="chip" data-rss="${esc(x.title)}" aria-pressed="${f === x.title}" title="${esc(x.error || x.url)}">${esc(x.title)} ${x.error ? '⚠' : x.count}</button><button class="chip" data-unsub="${esc(x.url)}" aria-label="${esc(x.title)} 구독 해제">✕</button>`).join('')}</div>
    <div class="card"><div class="list">${items.map(i => linkItem({...i, url: i.link}, `<span>${esc(i.source)}</span><span>${esc(when(i.date))}</span>`)).join('') || empty('표시할 소식이 없어요.')}</div></div>`;
  $('#feed-add').onsubmit = async e => { e.preventDefault(); try { await api('/api/local/feeds', 'POST', {url: $('#feed-url').value, title: $('#feed-title').value}); toast('구독을 추가했어요.'); renderRSS(); } catch (err) { toast(err.message); } };
  $('#feed-refresh').onclick = () => renderRSS(true);
  host.querySelector('.chips').onclick = async e => {
    const r = e.target.closest('[data-rss]'), u = e.target.closest('[data-unsub]');
    if (r) { S.cache.rssFilter = r.dataset.rss; renderRSS(); }
    if (u && confirm('이 피드 구독을 해제할까요?')) { await api('/api/local/feeds?url=' + encodeURIComponent(u.dataset.unsub), 'DELETE').catch(err => toast(err.message)); S.cache.rssFilter = ''; renderRSS(); }
  };
}

const AREAS = [['', '전체'], ['dg', '대구·경북'], ['nation', '전국 기관'], ['other', '다른 지역'], ['soon', '마감 임박 (7일 이내)'], ['star', '★ 관심 공고']];
function supportStatus(src) {
  if (!src || !src.total) return `<div class="bar"><span class="tag accent">3시간마다 자동 갱신</span><span class="muted">처음 수집 중이에요. 기관이 많아 몇 분 걸려요.</span><span class="grow"></span><button class="btn small" data-collect="support">지금 새로고침</button></div>`;
  const at = src.at ? new Date(src.at * 1000).toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'}) + '에 갱신 · ' : '';
  return `<div class="bar"><span class="tag accent">3시간마다 자동 갱신</span><span class="muted">${at}기관 ${src.total}곳 중 ${src.ok}곳 수집됨</span><span class="grow"></span><button class="btn small" data-collect="support">지금 새로고침</button></div>` +
    (src.failed.length ? `<details class="muted" style="margin:-6px 0 12px"${src.failed.some(f => f.blocked) ? ' open' : ''}><summary>못 읽은 곳 ${src.failed.length}곳${src.failed.some(f => f.blocked) ? ` · 차단 의심 ${src.failed.filter(f => f.blocked).length}곳` : ''}</summary>${src.failed.map(f => { const u = safeURL(f.home); return `<div>${f.blocked ? '<span class="tag warn">차단 의심 · 하루 1번만 재시도</span> ' : ''}${u ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(f.name)} 바로가기 ↗</a>` : esc(f.name)} · ${esc(f.error)}</div>`; }).join('')}<div style="margin-top:6px">이미 받아 둔 공고는 그대로 남아 있어요.</div></details>` : '');
}
RENDER.support = () => {
  const area = S.cache.supportArea || '';
  const order = S.cache.supportSort || '';
  $('#view').innerHTML = '<div id="status-host"></div><div id="list-host"></div>';
  const areaBar = `<div class="bar" style="margin-bottom:8px">${sortBar('supportSort', order)}${area === 'soon' && !order ? '<span class="muted">마감이 가까운 순서예요</span>' : ''}${area === 'star' && !order ? '<span class="muted">마감이 가까운 순서예요 · 마감된 공고는 아래에 흐리게 남아요</span>' : ''}</div><div class="chips source-chips" id="sarea">${AREAS.map(([id, label]) => `<button class="chip source" data-area="${id}" aria-pressed="${area === id}">${label}${id === 'star' ? '<span class="n" id="star-n"></span>' : ''}</button>`).join('')}</div>`;
  feedList({key: 'support-' + area + order, page: 'support', url: '/api/local/support', extra: {area, sort: order}, afterSearch: areaBar,
    onData: async d => {
      const fb = order === 'score' ? await feedbackSummary('support') : '';
      if (S.page !== 'support') return;
      $('#status-host').innerHTML = supportStatus(d.sources) + fb;
      const sn = $('#star-n'); if (sn) sn.textContent = ' ' + (d.star_count ?? '');
    },
    render: i => scoredItem('support', i, `${dday(i.days_left)}<span class="tag accent">${esc(i.source)}</span>${i.region && i.region !== '전국' ? `<span class="tag">${esc(i.region)}</span>` : ''}${i.period ? `<span>접수 ${esc(i.period)}</span>` : ''}<span>${esc(when(i.date))} 게시</span>`)});
  $('#sarea').onclick = e => { const b = e.target.closest('[data-area]'); if (b) { S.cache.supportArea = b.dataset.area; RENDER.support(); } };
};

/* ---------- AI 기술·분야 태그 (tagging.py decides; ✎ edits; a tag click opens everything with it) ---------- */
const tagOf = i => i.tags ? [...i.tags.tech, ...i.tags.field] : [];
const tagChips = t => !t ? '' : `<span class="tags">${t.tech.map(x => `<span role="button" tabindex="0" class="tagc tech${x === '미분류' ? ' un' : ''}" data-tag="${esc(x)}">${esc(x)}</span>`).join('')}${t.field.map(x => `<span role="button" tabindex="0" class="tagc field" data-tag="${esc(x)}">${esc(x)}</span>`).join('')}<span role="button" tabindex="0" class="tagc edit" data-tagedit="${esc(JSON.stringify(t))}" title="태그 고치기" aria-label="태그 고치기">✎</span></span>`;
function tagBar(key, items, labels) {  // two rows: AI 기술 (outlined) and 분야 (filled), most used first
  const cur = S.cache['tag-' + key] || '';
  const row = (axis, title) => {
    const c = {}; items.forEach(i => (i.tags?.[axis] || []).forEach(t => { c[t] = (c[t] || 0) + 1; }));
    const list = labels ? labels[axis].map(t => [t, '']) : Object.entries(c).sort((a, b) => b[1] - a[1]);
    return list.length ? `<div class="chips tagbar ${axis}" data-tagbar="${key}"><span class="muted">${title}</span>${axis === 'tech' ? `<button class="chip" data-tf="" aria-pressed="${!cur}">전체</button>` : ''}${list.map(([t, n]) => `<button class="chip" data-tf="${esc(t)}" aria-pressed="${cur === t}">${esc(t)}${n ? ' ' + n : ''}</button>`).join('')}</div>` : '';
  };
  return row('tech', 'AI 기술') + row('field', '분야');
}
const byTag = (items, key) => { const cur = S.cache['tag-' + key]; return cur ? items.filter(i => tagOf(i).includes(cur)) : items; };
document.addEventListener('click', e => {
  const f = e.target.closest('[data-tf]'); if (!f) return;
  S.cache['tag-' + f.closest('[data-tagbar]').dataset.tagbar] = f.dataset.tf; RENDER[S.page]();
});
const tagLabels = async () => S.cache.tagLabels ||= await api('/api/local/tags');
document.addEventListener('click', async e => {  // capture: tags sit inside clickable rows and cards
  const tg = e.target.closest('[data-tag]'), ed = e.target.closest('[data-tagedit]');
  if (!tg && !ed) return;
  e.preventDefault(); e.stopPropagation();
  if (tg) openTag(tg.dataset.tag); else openTagEdit(JSON.parse(ed.dataset.tagedit));
}, true);
document.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches?.('.tagc')) { e.preventDefault(); e.target.click(); } }, true);
async function openTag(tag) {
  $('#dlg-body').innerHTML = `<h2>태그 · ${esc(tag)}</h2>${empty('모으는 중…')}`; if (!$('#dlg').open) $('#dlg').showModal();
  const {groups} = await api('/api/local/tags?' + qs({tag})).catch(err => ({groups: {}, err}));
  const row = (href, title, meta, ext) => `<a class="item" href="${esc(href)}"${ext ? ' target="_blank" rel="noopener noreferrer"' : ''}><div class="item-title">${esc(title)}</div><div class="item-meta">${meta}</div></a>`;
  const G = [['github', 'GitHub', i => row(safeURL(i.url), i.title, `<span>★ ${Number(i.stars || 0).toLocaleString()}</span>`, true)],
             ['reddit', 'Reddit', i => row(safeURL(i.url), i.title, `<span>r/${esc(i.sub)}</span>`, true)],
             ['tools', '작업 공방 도구', i => row('#workshop/' + i.slug, i.title, `<span>${esc(i.category)}</span>`)],
             ['experiments', '실험', i => row('#workshop/lab/' + (i.no || ''), i.title, `<span>${esc(i.no || '직접 기록')}</span>`)],
             ['skills', '스킬', i => row('#skills', i.name, `<span>${esc(i.repo || i.slug || '')}</span>`)]];
  const total = G.reduce((n, [k]) => n + (groups[k] || []).length, 0);
  $('#dlg-body').innerHTML = `<h2>태그 · ${esc(tag)} <span class="muted" style="font-size:14px;font-weight:500">${total}개</span></h2>
    ${tag === '미분류' ? `<div class="bar"><span class="muted">낱말 규칙으로 못 정한 것들이에요. 하루 한 번 렘이 모아서 분류해요.</span><span class="grow"></span><button class="btn small primary" id="tg-classify">지금 렘에게 맡기기</button></div>` : ''}
    <div class="tag-groups">${G.map(([k, label, f]) => (groups[k] || []).length ? `<section><h3>${label} <span class="muted">${groups[k].length}</span></h3><div class="list">${groups[k].map(f).join('')}</div></section>` : '').join('') || empty('이 태그가 붙은 항목이 없어요.')}</div>
    <div class="bar" style="margin:12px 0 0"><span class="grow"></span><button class="btn primary" id="dlg-close">닫기</button></div>`;
  $('#dlg-close').onclick = () => $('#dlg').close();
  $('#dlg-body').querySelectorAll('a.item:not([target])').forEach(a => a.addEventListener('click', () => $('#dlg').close()));
  const c = $('#tg-classify'); if (c) c.onclick = async () => { try { const r = await api('/api/local/tags/classify', 'POST', {}); toast(r.sent ? `미분류 ${r.sent}개를 렘에게 맡겼어요.` : '맡길 미분류가 없어요.'); } catch (err) { toast(err.message); } };
}
async function openTagEdit(t) {
  const L = await tagLabels().catch(() => ({tech: [], field: []}));
  const box = (axis, title) => `<fieldset class="tag-edit"><legend>${title} <span class="muted">최대 2개</span></legend>${L[axis].map(x => `<label><input type="checkbox" name="${axis}" value="${esc(x)}"${t[axis].includes(x) ? ' checked' : ''}> ${esc(x)}</label>`).join('')}</fieldset>`;
  $('#dlg-body').innerHTML = `<h2>태그 고치기</h2><p class="muted">${t.src === 'manual' ? '직접 고친 태그예요.' : t.src === 'ai' ? '렘이 붙인 태그예요.' : t.src === 'base' ? '처음에 정해 둔 태그예요.' : '낱말 규칙으로 붙은 태그예요.'} 고치면 다음 수집 때도 그대로 남아요.</p>
    <form id="tag-form">${box('tech', 'AI 기술')}${box('field', '분야')}<div class="bar" style="margin:12px 0 0"><button type="button" class="btn" id="tg-auto">자동으로 되돌리기</button><span class="grow"></span><button type="button" class="btn" id="dlg-close">닫기</button><button class="btn primary">저장</button></div></form>`;
  if (!$('#dlg').open) $('#dlg').showModal();
  const form = $('#tag-form');
  form.onchange = e => { const n = form.querySelectorAll(`input[name="${e.target.name}"]:checked`); if (n.length > 2) { e.target.checked = false; toast('기준마다 2개까지 고를 수 있어요.'); } };
  const save = async (tech, field) => { try { await api('/api/local/tags', 'POST', {key: t.key, tech, field}); $('#dlg').close(); S.cache.lib = null; S.cache.tools = null; toast('태그를 저장했어요.'); RENDER[S.page](); } catch (err) { toast(err.message); } };
  form.onsubmit = e => { e.preventDefault(); const pick = a => [...form.querySelectorAll(`input[name="${a}"]:checked`)].map(i => i.value); save(pick('tech'), pick('field')); };
  $('#tg-auto').onclick = () => save([], []);
  $('#dlg-close').onclick = () => $('#dlg').close();
}

/* 커뮤니티: received items with an "실험하기" hand-off to 스킬관리 */
const expItem = (i, meta) => { const u = safeURL(i.url); return `<div class="item exp-item"><div><${u ? `a href="${esc(u)}" target="_blank" rel="noopener noreferrer"` : 'span'} class="item-title">${esc(i.title)}</${u ? 'a' : 'span'}><div class="item-meta">${meta}</div>${i.summary ? `<div class="item-sum">${esc(i.summary)}</div>` : ''}${tagChips(i.tags)}</div>${expButton(i)}</div>`; };
function sourceEditor(kind, list, label, placeholder) {
  return `<form class="bar" data-source-form="${kind}"><span class="muted">${label}</span>${list.map(v => `<span class="chip" aria-pressed="false">${esc(v)} <button type="button" class="link-x" data-source-remove="${kind}:${esc(v)}" aria-label="${esc(v)} 빼기">✕</button></span>`).join('')}<input name="value" placeholder="${placeholder}" aria-label="${label} 추가" style="width:160px"><button class="btn small">추가</button></form>`;
}
document.addEventListener('submit', async e => {
  const f = e.target.closest('[data-source-form]'); if (!f) return;
  e.preventDefault();
  try { await api('/api/local/community/sources', 'POST', {kind: f.dataset.sourceForm, value: f.value.value}); await api('/api/local/collect', 'POST', {job: f.dataset.sourceForm === 'reddit' ? 'reddit' : 'github'}); toast('추가했어요. 곧 새로 가져옵니다.'); setTimeout(() => RENDER.community(), 4000); }
  catch (err) { toast(err.message); }
});
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-source-remove]'); if (!b) return;
  const [kind, ...v] = b.dataset.sourceRemove.split(':');
  await api('/api/local/community/sources', 'POST', {kind, value: v.join(':'), remove: true}).catch(err => toast(err.message));
  RENDER.community();
});

RENDER.community = async () => {
  const t = sub('community', 'github');
  const v = $('#view');
  v.innerHTML = tabs('community', [['github', 'GitHub'], ['reddit', 'Reddit'], ['threads', 'Threads']]) + `<div id="cm-host">${empty('불러오는 중…')}</div>`;
  const host = $('#cm-host');
  if (t === 'threads') { host.innerHTML = `<div class="card">${empty('Threads는 로그인과 공식 API 등록이 필요해 잠시 보류했어요. GitHub·Reddit부터 받아 옵니다.')}</div>`; return; }
  const src = await api('/api/local/community/sources').catch(() => ({reddit: [], github_keywords: []}));
  if (t === 'github') {
    const d = await api('/api/local/community/github').catch(() => ({}));
    if (S.page !== 'community') return;
    const kw = S.cache.ghKw || '';
    const per = S.cache.ghPeriod || 'daily';
    const PER = [['daily', '일간'], ['weekly', '주간'], ['monthly', '월간']];
    const trend = byTag(d['trending_' + per] || [], 'gh');
    const top = Math.max(1, ...trend.map(r => r.gain || 0));
    const repo = r => expItem(r, `${r._rank != null ? `<span class="tag score ${scoreTone(r._rank)}" title="기간 스타 증가 ${(r.gain || 0).toLocaleString()} (1위 대비)">인기 ${r._rank}</span>` : ''}${r.language ? `<span class="tag">${esc(r.language)}</span>` : ''}<span>★ ${Number(r.stars || 0).toLocaleString()}</span>${r.gain ? `<span class="tag accent">+${r.gain.toLocaleString()}</span>` : ''}${r.date ? `<span>${esc(when(r.date))} 생성</span>` : ''}`);
    const search = d.search || {};
    host.innerHTML = collectorBar('github', d.status) +
      tagBar('gh', [...(d['trending_' + per] || []), ...Object.values(d.search || {}).flat()]) + `<section class="card"><h2>스타 증가 순위 <span class="seg" role="group" aria-label="기간">${PER.map(([id, label]) => `<button data-ghper="${id}" aria-pressed="${per === id}">${label}</button>`).join('')}</span></h2><div class="list">${trend.map(r => repo({...r, _rank: Math.round(100 * (r.gain || 0) / top)})).join('') || empty('아직 없어요. 다음 갱신 때 들어와요.')}</div></section>
       <section class="card" style="margin-top:16px"><h2>키워드로 찾은 이번 주 새 저장소</h2>${sourceEditor('github_keywords', src.github_keywords, '키워드', '예: rag')}
       <div class="chips">${['', ...Object.keys(search)].map(k => `<button class="chip" data-ghkw="${esc(k)}" aria-pressed="${kw === k}">${esc(k || '전체')}</button>`).join('')}</div>
       <div class="list">${byTag(kw ? search[kw] || [] : Object.values(search).flat(), 'gh').map(repo).join('') || empty('아직 없어요.')}</div></section>`;
    host.onclick = e => {
      const b = e.target.closest('[data-ghkw]'); if (b) { S.cache.ghKw = b.dataset.ghkw; RENDER.community(); }
      const p2 = e.target.closest('[data-ghper]'); if (p2) { S.cache.ghPeriod = p2.dataset.ghper; RENDER.community(); }
    };
  } else {
    const subName = S.cache.rdSub || '';
    const per = S.cache.rdPeriod || 'day';
    const rdTag = S.cache['tag-rd'] || '';
    const L = await tagLabels().catch(() => ({tech: [], field: []}));
    if (S.page !== 'community') return;
    host.innerHTML = `<div id="rd-status"></div>${sourceEditor('reddit', src.reddit, '서브레딧', '예: StableDiffusion')}<div class="bar"><span class="seg" role="group" aria-label="기간">${[['day', '일간'], ['week', '주간'], ['month', '월간']].map(([id, label]) => `<button data-rdper="${id}" aria-pressed="${per === id}">${label}</button>`).join('')}</span><span class="muted">각 서브레딧의 ${per === 'day' ? '오늘' : per === 'week' ? '이번 주' : '이번 달'} 추천 순위</span></div><div class="chips">${['', ...src.reddit].map(s => `<button class="chip" data-rdsub="${esc(s)}" aria-pressed="${subName === s}">${esc(s ? 'r/' + s : '전체')}</button>`).join('')}</div>${tagBar('rd', [], {tech: ['미분류', ...L.tech], field: L.field})}<div id="list-host"></div>`;
    host.querySelector('.chips:not([data-source-form])').onclick = e => { const b = e.target.closest('[data-rdsub]'); if (b) { S.cache.rdSub = b.dataset.rdsub; RENDER.community(); } };
    host.querySelector('.seg').onclick = e => { const b = e.target.closest('[data-rdper]'); if (b) { S.cache.rdPeriod = b.dataset.rdper; RENDER.community(); } };
    feedList({key: 'reddit-' + subName + per + rdTag, page: 'community', url: '/api/local/community/reddit', extra: {sub: subName, period: per, tag: rdTag},
      onData: d => { $('#rd-status').innerHTML = collectorBar('reddit', d.status) + (d.failed?.length ? `<p class="muted">가져오지 못한 곳: ${d.failed.map(s => 'r/' + esc(s)).join(', ')} (Reddit 요청 제한, 다음 갱신 때 다시 시도)</p>` : ''); },
      render: p => expItem(p, `<span class="tag score ${scoreTone(p.score)}" title="r/${esc(p.sub)} ${p.rank}위 / ${p.of}">인기 ${p.score}</span><span class="tag accent">r/${esc(p.sub)}</span>${p.author ? `<span>${esc(p.author)}</span>` : ''}<span>${esc(whenTime(p.date))}</span>`)});
  }
};

/* ---------- 실험하기: 렘·람 hand-off (server numbers it EXP-MMDD-NN and writes the prompt) ---------- */
const EXP_KINDS = [['try', '써보기', '저장소·도구를 실험 폴더에서 직접 설치·실행해 보고 되는지 확인해요. 결과: 실행 보고서'], ['skill', '스킬로 만들기', '방법을 우리 스킬(SKILL.md 초안)로 정리해요. 결과: 보고서 + SKILL.md'], ['review', '적용 검토', 'A4AI 업무에 쓸 수 있는지 판단해요. 결과: 1쪽 검토서'], ['ppt', 'PPT로 분석하기', '8~12장 PPT로 분석해요. 슬라이드마다 옆에 핵심 요약, 마지막에 결론. 결과: PPT + 웹 슬라이드 주소']];
const EXP_STATUS = {sent: ['지시함', ''], running: ['진행 중', 'accent'], arrived: ['결과 도착', 'ok'], rated: ['평가 완료', 'accent']};
const MAID_NAME = {rem: '렘 (GPT · Codex Desktop)', ram: '람 (Claude · Claude Code)'};
const expButton = i => `<button class="btn small exp-btn" data-exp="${esc(JSON.stringify({title: i.title, url: i.url, summary: (i.summary || '').slice(0, 600)}))}">실험하기</button>`;
document.addEventListener('click', e => { const b = e.target.closest('[data-exp]'); if (b) openExperiment(JSON.parse(b.dataset.exp)); });
function openExperiment(x) {
  let kind = 'try', who = 'rem';
  const draw = () => {
    $('#dlg-body').innerHTML = `<h2>실험하기</h2><p class="muted">${esc(x.title)}</p>
      <div class="bar"><span class="muted">종류</span><span class="seg" id="xk">${EXP_KINDS.map(([id, l]) => `<button data-k="${id}" aria-pressed="${kind === id}">${l}</button>`).join('')}</span></div>
      <p class="muted" style="margin-top:-4px">${esc(EXP_KINDS.find(k => k[0] === kind)[2])}</p>
      <div class="bar"><span class="muted">누구에게</span><span class="seg" id="xm">${[['rem', '렘 (GPT)'], ['ram', '람 (Claude)'], ['both', '둘 다 · 비교']].map(([id, l]) => `<button data-m="${id}" aria-pressed="${who === id}">${l}</button>`).join('')}</span></div>
      <p class="muted">맡기면 렘·람이 이 컴퓨터에서 바로 시작해요. 쓰기는 <b>실험실\\실험번호</b>·outputs·보고서 저장소에만 하고, 설치가 필요하면 하지 않고 "설치 필요"를 남겨요. 결과는 작업 공방 &gt; 실험과 산출물 정리에 저절로 붙어요.</p>
      <div class="bar" style="margin:12px 0 0"><button class="btn" id="xcopy">지시문만 만들기</button><span class="grow"></span><button class="btn" id="dlg-close">닫기</button><button class="btn primary" id="xgo">맡기기</button></div>`;
    $('#dlg-close').onclick = () => $('#dlg').close();
    $('#xk').onclick = e => { const b = e.target.closest('[data-k]'); if (b) { kind = b.dataset.k; draw(); } };
    $('#xm').onclick = e => { const b = e.target.closest('[data-m]'); if (b) { who = b.dataset.m; draw(); } };
    const send = async run => {
      try {
        const r = await api('/api/local/experiments', 'POST', {title: x.title, url: x.url, input: x.summary, kind, maids: who === 'both' ? ['rem', 'ram'] : [who], run});
        if (!run) return showPrompts(r, true);
        $('#dlg').close();
        toast(r.run_errors?.length ? r.run_errors.join(' ') : `${r.no}: ${r.maids.map(m => m === 'rem' ? '렘' : '람').join('·')}에게 맡겼어요.`);
        location.hash = 'workshop/lab/' + r.no;
      } catch (err) { toast(err.message); }
    };
    $('#xgo').onclick = () => send(true);
    $('#xcopy').onclick = () => send(false);
  };
  draw(); $('#dlg').showModal();
}
async function copyText(t) { try { await navigator.clipboard.writeText(t); return true; } catch { return false; } }
async function showPrompts(x, fresh) {
  $('#dlg-body').innerHTML = `<h2>${esc(x.no)} 지시문</h2><p class="muted">${esc(x.title)}</p>${x.maids.map(m => `<div style="margin-top:12px"><div class="bar" style="margin:0 0 6px"><b>${MAID_NAME[m]}에게</b><span class="grow"></span><button class="btn small" data-copy="${m}">복사</button></div><textarea class="mono" readonly rows="9" aria-label="${MAID_NAME[m]} 지시문">${esc(x.prompts[m])}</textarea></div>`).join('')}
    <p class="muted">복사해서 ${x.maids.map(m => m === 'rem' ? 'Codex Desktop' : 'Claude Code').join('·')}에 붙여 넣으세요. 진행 상황은 작업 공방 &gt; 실험에서 볼 수 있어요.</p>
    <div class="bar" style="margin:12px 0 0"><span class="grow"></span><a class="btn" href="#workshop/lab/${esc(x.no)}" id="xlab">실험에서 보기</a><button class="btn primary" id="dlg-close">닫기</button></div>`;
  $('#dlg-close').onclick = () => $('#dlg').close();
  $('#xlab').onclick = () => $('#dlg').close();
  $('#dlg-body').onclick = async e => { const b = e.target.closest('[data-copy]'); if (b) toast(await copyText(x.prompts[b.dataset.copy]) ? '복사했어요.' : '복사가 막혔어요. 글을 직접 선택해 복사하세요.'); };
  if (!$('#dlg').open) $('#dlg').showModal();
  if (fresh) toast(await copyText(x.prompts[x.maids[0]]) ? `${x.no} 지시문을 복사했어요.` : `${x.no}를 만들었어요. 복사 버튼을 눌러 주세요.`);
}

function expCard(x) {
  const [st, tone] = EXP_STATUS[x.status] || ['직접 기록', ''];
  const u = safeURL(x.url);
  const files = m => { const latest = {}; (x.results || []).filter(r => r.maid === m || (!r.maid && m === x.maids[0])).forEach(r => { latest[r.name] = r; }); return Object.values(latest); };  // republished files: newest only
  const RUN = {running: ['진행 중…', 'accent'], done: ['끝남', 'ok'], failed: ['실패', 'warn'], ended: ['끝남 (서버 재시작)', '']};
  const run = m => { const r = (x.runs || {})[m]; if (!r) return ''; const [l, tone] = RUN[r.state] || [r.state, '']; return `<span class="tag ${tone}">${l}${r.task === 'image' ? ' · 그림' : ''}${r.note ? ' · ' + esc(r.note) : ''}</span><button class="btn small" data-runlog="${esc(x.id)}:${m}">기록 보기</button>`; };
  const again = m => (x.runs || {})[m]?.state === 'running' ? '' : `<button class="btn small" data-rerun="${esc(x.id)}:${m}">${(x.runs || {})[m] ? '다시 맡기기' : '맡기기'}</button>`;
  const col = m => `<div class="exp-col"><div class="item-meta" style="margin:0 0 4px"><b>${MAID_NAME[m]}</b>${run(m)}</div>${files(m).map(r => r.web ? `<div class="bar" style="margin:0 0 4px"><a class="btn small primary" href="${esc(safeURL(r.web))}" target="_blank" rel="noopener noreferrer">웹으로 보기 ↗</a><span class="muted">${esc(r.web)}</span></div>` : `<div class="result-row"><div class="bar" style="margin:0 0 4px"><span class="ftype">${esc(fileKind(r.name).label)}</span><a href="/api/local/files/${esc(r.id)}" download>${esc(r.name)}</a><span class="grow"></span><button class="btn small" data-preview="${esc(r.id)}" data-name="${esc(r.name)}" aria-expanded="false">펼치기</button><a class="btn small" href="#outputs/${esc(r.id)}">산출물에서 보기</a></div><div class="preview" hidden></div></div>`).join('') || `<div class="bar" style="margin:0"><span class="muted">결과를 기다리는 중</span></div>`}<div class="bar" style="margin:6px 0 0">${again(m)}<button class="btn small" data-reprompt="${esc(x.id)}">지시문 복사</button></div></div>`;
  return `<article class="card exp-card" id="${esc(x.no || x.id)}"><div class="item-meta" style="margin:0 0 4px">${x.no ? `<span class="tag accent">${esc(x.no)}</span>` : ''}${x.kind ? `<span class="tag">${esc(EXP_KINDS.find(k => k[0] === x.kind)?.[1] || x.kind)}</span>` : ''}${x.skill ? `<span class="tag accent">${esc(x.skill)}</span>` : ''}<span class="tag ${tone}">${st}</span><span>${esc(new Date(x.created).toLocaleString('ko-KR'))}</span></div>
    <${u ? `a href="${esc(u)}" target="_blank" rel="noopener noreferrer"` : 'div'} class="item-title">${esc(x.title)}</${u ? 'a' : 'div'}>${tagChips(x.tags)}
    ${x.maids ? `<div class="grid ${x.maids.length > 1 ? 'g2' : ''}" style="gap:12px;margin-top:10px">${x.maids.map(col).join('')}</div>` : x.input ? `<pre class="doc">${esc(x.input)}</pre>` : ''}
    ${x.image_task ? `<div class="bar" style="margin:10px 0 0"><span class="tag warn">그림 생성 필요</span><span class="muted">맞는 사진이 없는 슬라이드가 있어요. 기본은 렘이 만들어요.</span><span class="grow"></span>${(x.runs || {}).rem?.state === 'running' && x.runs.rem.task === 'image' ? '<span class="tag accent">렘이 그리는 중…</span>' : `<button class="btn small primary" data-imgrun="${esc(x.id)}">렘에게 맡기기</button>`}<button class="btn small" data-imgtask="${esc(x.id)}">지시문 복사</button></div>` : ''}
    <form class="bar" data-rate="${esc(x.id)}" style="margin:10px 0 0"><select name="rating" aria-label="평가"><option value="0">평가 없음</option>${[1, 2, 3, 4, 5].map(n => `<option value="${n}"${x.rating === n ? ' selected' : ''}>${'★'.repeat(n)}</option>`).join('')}</select><input class="grow" name="result" value="${esc(x.result)}" placeholder="평가 메모" aria-label="평가 메모"><button class="btn small">저장</button><button type="button" class="btn small" data-dellog="${esc(x.id)}">삭제</button></form></article>`;
}
async function renderLab(host) {
  const {experiments = []} = await api('/api/local/experiments').catch(() => ({}));
  if (S.page !== 'workshop') return;
  S.cache.exps = experiments;
  const f = S.cache.expFilter || '';
  const shown = byTag(experiments, 'exp').filter(x => !f || x.status === f);
  host.innerHTML = `<div class="chips" id="xf">${[['', '전체'], ['running', '진행 중'], ['sent', '지시함'], ['arrived', '결과 도착'], ['rated', '평가 완료']].map(([id, l]) => `<button class="chip" data-xf="${id}" aria-pressed="${f === id}">${l} ${experiments.filter(x => !id || x.status === id).length}</button>`).join('')}</div>
    ${tagBar('exp', experiments)}
    <div id="logs">${shown.map(expCard).join('') || empty('아직 실험이 없어요. 커뮤니티나 뉴스룸에서 실험하기를 눌러 보세요.')}</div>`;
  $('#xf').onclick = e => { const b = e.target.closest('[data-xf]'); if (b) { S.cache.expFilter = b.dataset.xf; renderLab(host); } };
  $('#logs').onsubmit = async e => { const fm = e.target.closest('[data-rate]'); if (!fm) return; e.preventDefault(); try { await api('/api/local/experiments/rate', 'POST', {id: fm.dataset.rate, rating: Number(fm.rating.value), result: fm.result.value}); toast('평가를 저장했어요.'); renderLab(host); } catch (err) { toast(err.message); } };
  $('#logs').onclick = async e => {
    const d = e.target.closest('[data-dellog]'); if (d && confirm('이 실험 기록을 삭제할까요? 산출물 파일은 그대로 남아요.')) { await api('/api/local/experiments?id=' + d.dataset.dellog, 'DELETE').catch(err => toast(err.message)); renderLab(host); }
    const r = e.target.closest('[data-reprompt]'); if (r) showPrompts(experiments.find(x => x.id === r.dataset.reprompt));
    const ir = e.target.closest('[data-imgrun]'); if (ir) { try { await api('/api/local/experiments/run', 'POST', {id: ir.dataset.imgrun, maid: 'rem', task: 'image'}); toast('렘에게 그림을 맡겼어요.'); renderLab(host); } catch (err) { toast(err.message); } }
    const rr = e.target.closest('[data-rerun]'); if (rr) { const [id, maid] = rr.dataset.rerun.split(':'); try { await api('/api/local/experiments/run', 'POST', {id, maid}); toast((maid === 'rem' ? '렘' : '람') + '에게 맡겼어요.'); renderLab(host); } catch (err) { toast(err.message); } }
    const lg = e.target.closest('[data-runlog]'); if (lg) { const [id, maid] = lg.dataset.runlog.split(':'); const {log} = await api('/api/local/experiments/log?' + qs({id, maid})).catch(() => ({log: ''})); $('#dlg-body').innerHTML = `<h2>${maid === 'rem' ? '렘' : '람'} 실행 기록</h2><pre class="doc" style="max-height:60vh;overflow:auto;white-space:pre-wrap">${esc(log || '기록이 없어요.')}</pre><div class="bar" style="margin:12px 0 0"><span class="grow"></span><button class="btn primary" id="dlg-close">닫기</button></div>`; $('#dlg-close').onclick = () => $('#dlg').close(); $('#dlg').showModal(); }
    const g = e.target.closest('[data-imgtask]'); if (g) { const x = experiments.find(y => y.id === g.dataset.imgtask); showPrompts({...x, maids: ['rem'], prompts: {rem: x.image_task}}, true); }
  };
  const target = S.arg.split('/')[1]; if (target) document.getElementById(target)?.scrollIntoView({block: 'center'});
  // results land while you watch: re-check quietly every 10 s, redraw only if something changed and you are not typing
  clearTimeout(S.labTimer);
  const sigOf = list => JSON.stringify(list.map(x => [x.status, (x.results || []).length, !!x.image_task, Object.values(x.runs || {}).map(r => r.state)]));
  const sig = sigOf(experiments);
  S.labTimer = setTimeout(async function tick() {
    if (S.page !== 'workshop' || sub('workshop', 'tools') !== 'lab') return;
    const d = await api('/api/local/experiments').catch(() => null);
    const busy = $('#dlg').open || host.contains(document.activeElement) && document.activeElement.matches('input,textarea,select') || !!host.querySelector('.preview:not([hidden])');
    if (d && sigOf(d.experiments) !== sig && !busy) renderLab(host);
    else S.labTimer = setTimeout(tick, 10000);
  }, 10000);
}
/* 펼치기: every result file previewed in place (HTML sandboxed, Markdown, images, PDF, Word·Excel·PPT via PDF, HWP via rhwp) */
const KINDS = [
  [/\.(html?)$/i, 'html', '웹 페이지'], [/\.(md|markdown)$/i, 'md', '마크다운'], [/\.(png|jpe?g|gif|webp|svg|bmp)$/i, 'img', '이미지'],
  [/\.pdf$/i, 'pdf', 'PDF'], [/\.(docx?|rtf|odt)$/i, 'office', '워드'], [/\.(xlsx?|ods)$/i, 'office', '엑셀'], [/\.(pptx?|odp)$/i, 'office', 'PPT'],
  [/\.(hwpx?)$/i, 'hwp', '한글'], [/\.(mp4|webm|mov)$/i, 'video', '영상'], [/\.(mp3|wav|ogg|m4a)$/i, 'audio', '오디오'],
  [/\.(txt|json|csv|log|ya?ml|py|js|ts|css)$/i, 'text', '텍스트']];
const fileKind = name => { const k = KINDS.find(([re]) => re.test(name)); return k ? {type: k[1], label: k[2]} : {type: 'other', label: '파일'}; };
const loaded = {};
const loadScript = src => loaded[src] ||= new Promise((ok, no) => { const el = document.createElement('script'); el.src = src; el.onload = ok; el.onerror = () => no(new Error('미리보기 도구를 불러오지 못했어요.')); document.head.append(el); });
const PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
async function renderPdf(box, url) {
  await loadScript(PDFJS);
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  const res = await fetch(url); if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || '미리 볼 수 없어요.');
  const pdf = await pdfjsLib.getDocument({data: await res.arrayBuffer()}).promise;
  box.innerHTML = `<div class="muted">${pdf.numPages}쪽</div>`;
  for (let n = 1; n <= Math.min(pdf.numPages, 30); n++) {
    const page = await pdf.getPage(n), vp = page.getViewport({scale: 1.6});
    const c = document.createElement('canvas'); c.width = vp.width; c.height = vp.height; c.className = 'page';
    box.append(c); await page.render({canvasContext: c.getContext('2d'), viewport: vp}).promise;
  }
  if (pdf.numPages > 30) box.insertAdjacentHTML('beforeend', '<p class="muted">30쪽까지만 보여요. 나머지는 받아서 보세요.</p>');
}
async function renderHwp(box, url) {
  const {default: init, HwpDocument} = await import('/komow_app/rhwp/package/rhwp.js');
  const ctx = document.createElement('canvas').getContext('2d');
  globalThis.measureTextWidth ||= (font, text) => { ctx.font = font; return ctx.measureText(text).width; };
  await init({module_or_path: '/komow_app/rhwp/package/rhwp_bg.wasm'});
  const doc = new HwpDocument(new Uint8Array(await (await fetch(url)).arrayBuffer()));
  const n = doc.pageCount(); box.innerHTML = `<div class="muted">${n}쪽</div>`;
  for (let i = 0; i < Math.min(n, 30); i++) { const img = new Image(); img.className = 'page'; img.alt = `${i + 1}쪽`; img.src = URL.createObjectURL(new Blob([doc.renderPageSvg(i)], {type: 'image/svg+xml'})); box.append(img); }
  doc.free();
}
async function openPreview(btn) {
  const box = btn.closest('.result-row').querySelector('.preview');
  const open = box.hidden; box.hidden = !open; btn.textContent = open ? '접기' : '펼치기'; btn.setAttribute('aria-expanded', open);
  if (!open || box.dataset.done) return;
  const id = btn.dataset.preview, view = `/api/local/files/${id}?as=view`, {type} = fileKind(btn.dataset.name);
  box.innerHTML = empty('불러오는 중…');
  try {
    if (type === 'html') {  // srcdoc + sandbox: the page runs with an opaque origin, never as this site
      const f = document.createElement('iframe'); f.className = 'frame-preview'; f.title = btn.dataset.name; f.setAttribute('sandbox', 'allow-scripts allow-popups');
      f.srcdoc = await (await fetch(view)).text(); box.replaceChildren(f);
    }
    else if (type === 'img') box.innerHTML = `<img class="page" src="${view}" alt="${esc(btn.dataset.name)}">`;
    else if (type === 'video') box.innerHTML = `<video class="page" controls src="${view}"></video>`;
    else if (type === 'audio') box.innerHTML = `<audio controls src="${view}"></audio>`;
    else if (type === 'md') {
      await Promise.all([loadScript('https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js'), loadScript('https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.1.6/purify.min.js')]);
      const md = await (await fetch(view)).text();
      box.innerHTML = `<div class="md">${DOMPurify.sanitize(marked.parse(md))}</div>`;
      box.querySelectorAll('.md a').forEach(a => { a.target = '_blank'; a.rel = 'noopener noreferrer'; });
    } else if (type === 'text') box.innerHTML = `<pre class="doc">${esc(await (await fetch(view)).text())}</pre>`;
    else if (type === 'pdf') await renderPdf(box, view);
    else if (type === 'office') { box.innerHTML = empty('PDF로 바꾸는 중… (처음 한 번만 몇 초 걸려요)'); await renderPdf(box, `/api/local/files/${id}?as=pdf`); }
    else if (type === 'hwp') await renderHwp(box, view);
    else box.innerHTML = empty('이 형식은 미리 볼 수 없어요. 파일 이름을 눌러 받아 주세요.');
    box.dataset.done = '1';
  } catch (err) { box.innerHTML = empty(err.message || '미리 볼 수 없어요.'); }
}
document.addEventListener('click', e => { const b = e.target.closest('[data-preview]'); if (b) openPreview(b); });

RENDER.workshop = async () => {
  const v = $('#view');
  const tools = S.cache.tools ||= (await api('/api/local/tools').catch(() => ({tools: []}))).tools;
  if (S.page !== 'workshop') return;
  const open = tools.find(t => t.slug === S.arg);
  if (!open && sub('workshop', 'tools') === 'lab') {
    v.innerHTML = tabs('workshop', [['tools', '도구'], ['lab', '실험']]) + `<div id="lab-host">${empty('불러오는 중…')}</div>`;
    return renderLab($('#lab-host'));
  }
  if (open) {
    const u = safeURL(open.url, true);
    $('#title').textContent = open.title; $('#subtitle').textContent = open.desc;
    v.innerHTML = `<div class="stage"><div class="bar" style="margin:0"><a class="btn" href="#workshop">← 도구 목록</a><a class="btn" href="${esc(u)}" target="_blank" rel="noopener">새 탭에서 열기 ↗</a>${open.login ? '<span class="tag warn">원본 계정 기능은 연결되지 않음</span>' : ''}</div><iframe src="${esc(u)}" title="${esc(open.title)}" allow="fullscreen; clipboard-read; clipboard-write; cross-origin-isolated" allowfullscreen></iframe></div>`;
    return;
  }
  const cat = S.cache.toolCat || '';
  const cats = [...new Set(tools.map(t => t.category))];
  v.innerHTML = tabs('workshop', [['tools', '도구'], ['lab', '실험']]) + `<div class="bar"><input type="search" class="grow" id="tq" placeholder="도구 검색" aria-label="도구 검색" value="${esc(S.cache.toolQ || '')}"></div><div class="chips" id="tcats">${['', ...cats].map(c => `<button class="chip" data-tcat="${esc(c)}" aria-pressed="${cat === c}">${esc(c || '전체')}</button>`).join('')}</div>${tagBar('tool', tools)}<div class="tools" id="tgrid"></div>`;
  const draw = () => {
    const q = (S.cache.toolQ || '').toLowerCase();
    $('#tgrid').innerHTML = byTag(tools, 'tool').filter(t => (!cat || t.category === cat) && (!q || (t.title + t.desc).toLowerCase().includes(q))).map(t => `<a class="tool" href="#workshop/${esc(t.slug)}" style="text-decoration:none"><span class="tag">${esc(t.category)}</span><b>${esc(t.title)}</b><p>${esc(t.desc)}</p>${tagChips(t.tags)}${t.login ? '<span class="muted">일부 기능은 원본 서버 필요</span>' : ''}</a>`).join('') || empty('일치하는 도구가 없어요.');
  };
  $('#tq').oninput = e => { S.cache.toolQ = e.target.value; draw(); };
  $('#tcats').onclick = e => { const b = e.target.closest('[data-tcat]'); if (b) { S.cache.toolCat = b.dataset.tcat; RENDER.workshop(); } };
  draw();
};

RENDER.outputs = async () => {
  const v = $('#view');
  v.innerHTML = `<form class="card bar" id="up-form" style="margin-bottom:16px"><input id="up-folder" list="up-folders" placeholder="폴더 (예: 보고서)" aria-label="폴더"><datalist id="up-folders"></datalist><input class="grow" id="up-note" placeholder="메모 (선택)" aria-label="메모"><label class="btn primary">파일 올리기<input id="up-file" type="file" multiple hidden></label><span class="muted">파일당 20MB · 같은 파일은 한 번만 저장</span></form><div class="chips" id="f-folders"></div><div class="card table-wrap" id="f-list">${empty('불러오는 중…')}</div>`;
  const {files = []} = await api('/api/local/files').catch(() => ({}));
  if (S.page !== 'outputs') return;
  const folders = [...new Set(files.map(f => f.folder).filter(Boolean))];
  const target = S.arg && files.find(f => f.id === S.arg);
  if (target && S.cache.folder && S.cache.folder !== target.folder) S.cache.folder = '';  // make sure the file is in view
  const cur = S.cache.folder || '';
  $('#up-folders').innerHTML = folders.map(f => `<option value="${esc(f)}">`).join('');
  $('#f-folders').innerHTML = folders.length ? ['', ...folders].map(f => `<button class="chip" data-folder="${esc(f)}" aria-pressed="${cur === f}">${esc(f || '전체')}</button>`).join('') : '';
  const shown = files.filter(f => !cur || f.folder === cur);
  $('#f-list').innerHTML = shown.length ? `<table><thead><tr><th>파일</th><th>폴더</th><th>크기</th><th>올린 날</th><th></th></tr></thead><tbody>${shown.map(f => `<tr data-file="${esc(f.id)}"><td><div class="item-title">${esc(f.name)}</div>${f.experiment ? `<a class="tag accent" href="#workshop/lab/${esc(f.experiment)}">실험 ${esc(f.experiment)}</a>` : ''}${f.web ? ` <a class="tag" href="${esc(safeURL(f.web))}" target="_blank" rel="noopener noreferrer">웹으로 보기 ↗</a>` : ''}${f.note ? `<div class="muted">${esc(f.note)}</div>` : ''}</td><td>${esc(f.folder || '미분류')}</td><td>${size(f.size)}</td><td>${esc(when(f.created))}</td><td style="white-space:nowrap"><a class="btn small" href="/api/local/files/${esc(f.id)}" download>받기</a> <button class="btn small" data-delfile="${esc(f.id)}">삭제</button></td></tr>`).join('')}</tbody></table>` : empty('아직 보관한 파일이 없어요.');
  if (target) { const row = $(`#f-list tr[data-file="${target.id}"]`); if (row) { row.scrollIntoView({block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'}); row.classList.add('flash'); setTimeout(() => row.classList.remove('flash'), 2600); } S.arg = ''; history.replaceState(null, '', '#outputs'); }
  $('#f-folders').onclick = e => { const b = e.target.closest('[data-folder]'); if (b) { S.cache.folder = b.dataset.folder; RENDER.outputs(); } };
  $('#f-list').onclick = async e => { const b = e.target.closest('[data-delfile]'); if (b && confirm('이 파일을 삭제할까요? 되돌릴 수 없습니다.')) { await api('/api/local/files?id=' + b.dataset.delfile, 'DELETE').catch(err => toast(err.message)); RENDER.outputs(); } };
  $('#up-file').onchange = async e => {
    const list = [...e.target.files]; let ok = 0; const errs = [];
    for (const file of list) {
      if (file.size > 20 * 1048576) { errs.push(file.name + ': 20MB 초과'); continue; }
      toast(`올리는 중… ${file.name}`);
      try {
        const bytes = new Uint8Array(await file.arrayBuffer()); let bin = '';
        for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
        await api('/api/local/files', 'POST', {name: file.name, content: btoa(bin), folder: $('#up-folder').value, note: $('#up-note').value}); ok++;
      } catch (err) { errs.push(file.name + ': ' + err.message); }
    }
    toast(`${ok}개 저장${errs.length ? ' · 실패: ' + errs.join(', ') : ''}`); RENDER.outputs();
  };
};

/* ---------- 스킬관리 ---------- */
RENDER.skills = async () => {
  const t = sub('skills', 'library');
  const v = $('#view');
  v.innerHTML = tabs('skills', [['library', '스킬 라이브러리'], ['mine', '내 스킬']]) + `<div id="sk-host">${empty('불러오는 중…')}</div>`;
  const host = $('#sk-host');
  if (t === 'library') {
    const lib = S.cache.lib ||= (await api('/api/local/skills').catch(() => ({skills: []}))).skills;
    if (S.page !== 'skills') return;
    host.innerHTML = `<div class="bar"><input type="search" class="grow" id="sq" placeholder="스킬 이름·설명·저장소 검색" aria-label="스킬 검색" value="${esc(S.cache.skQ || '')}"><span class="muted" id="sc"></span></div>${tagBar('skill', lib)}<div class="card"><div class="list" id="sl"></div></div>`;
    const draw = () => { const q = (S.cache.skQ || '').toLowerCase(); const l = byTag(lib, 'skill').filter(s => !q || (s.name + s.description + s.repo).toLowerCase().includes(q)); $('#sc').textContent = l.length + '개'; $('#sl').innerHTML = l.slice(0, 200).map(s => `<button class="item" style="background:none;border-width:0 0 1px;text-align:left;width:100%;cursor:pointer" data-skill="${esc(s.id)}"><div class="item-title">${esc(s.name)}</div><div class="item-meta"><span>${esc(s.repo)}</span></div>${s.description ? `<div class="item-sum">${esc(s.description.slice(0, 200))}</div>` : ''}${tagChips(s.tags)}</button>`).join('') || empty('일치하는 스킬이 없어요.'); };
    $('#sq').oninput = e => { S.cache.skQ = e.target.value; draw(); }; draw();
    $('#sl').onclick = e => { const b = e.target.closest('[data-skill]'); if (b) openSkill(lib.find(s => s.id === b.dataset.skill)); };
  } else {
    const {skills = []} = await api('/api/local/my-skills').catch(() => ({}));
    if (S.page !== 'skills') return;
    host.innerHTML = `<div class="bar"><button class="btn primary" id="new-skill">새 스킬 만들기</button><span class="muted">komow-local/data/skills 폴더에 SKILL.md로 저장돼요.</span></div><div class="card"><div class="list" id="ml">${skills.map(s => `<button class="item" style="background:none;border-width:0 0 1px;text-align:left;width:100%;cursor:pointer" data-mine="${esc(s.slug)}"><div class="item-title">${esc(s.name)}</div><div class="item-meta"><span>${esc(s.slug)}</span><span>수정 ${esc(when(s.updated))}</span></div>${s.description ? `<div class="item-sum">${esc(s.description)}</div>` : ''}${tagChips(s.tags)}</button>`).join('') || empty('아직 내 스킬이 없어요. 새로 만들거나 라이브러리에서 복사해 보세요.')}</div></div>`;
    $('#new-skill').onclick = () => openEditor('', TEMPLATE);
    $('#ml').onclick = async e => { const b = e.target.closest('[data-mine]'); if (b) { try { const d = await api('/api/local/my-skills?slug=' + encodeURIComponent(b.dataset.mine)); openEditor(d.slug, d.content); } catch (err) { toast(err.message); } } };
  }
};
const TEMPLATE = '---\nname: my-skill\ndescription: 이 스킬을 언제 쓰는지 한 줄로 적으세요.\n---\n\n# 내 스킬\n\n## 언제 쓰나요\n\n## 순서\n1. \n';
async function openSkill(s) {
  if (!s) return;
  $('#dlg-body').innerHTML = `<h2>${esc(s.name)}</h2><p class="muted">${esc(s.repo)} / ${esc(s.path)} · 원문 보기 (자동 실행하지 않음)</p><pre class="doc" id="sk-doc">불러오는 중…</pre><div class="bar" style="margin:0"><button class="btn primary" id="sk-copy" disabled>내 스킬로 복사</button><span class="grow"></span><button class="btn" id="dlg-close">닫기</button></div>`;
  $('#dlg-close').onclick = () => $('#dlg').close();
  $('#dlg').showModal();
  try { const d = await api('/api/local/skills?id=' + encodeURIComponent(s.id)); $('#sk-doc').textContent = d.content; $('#sk-copy').disabled = false; $('#sk-copy').onclick = () => { openEditor('', d.content); toast('복사본을 열었어요. 고친 뒤 저장하세요.'); }; }
  catch (e) { $('#sk-doc').textContent = e.message; }
}
function openEditor(slug, content) {
  $('#dlg-body').innerHTML = `<h2>${slug ? '내 스킬 · ' + esc(slug) : '새 스킬'}</h2><p class="muted" id="ed-status">맨 위 name: 값이 폴더 이름이 됩니다 (영문 소문자·숫자·-).</p><textarea class="mono" id="ed" spellcheck="false" aria-label="SKILL.md 내용"></textarea><div class="bar" style="margin:12px 0 0">${slug ? '<button class="btn" id="ed-del">삭제</button>' : ''}<span class="grow"></span><button class="btn" id="dlg-close">닫기</button><button class="btn primary" id="ed-save">저장</button></div>`;
  $('#ed').value = content;
  $('#dlg-close').onclick = () => $('#dlg').close();
  $('#ed-save').onclick = async () => {
    try { const r = await api('/api/local/my-skills', 'POST', {slug, content: $('#ed').value}); openEditor(r.slug, $('#ed').value); toast(`저장했어요 · data/skills/${r.slug}/SKILL.md`); if (S.page === 'skills' && sub('skills') === 'mine') RENDER.skills(); }
    catch (e) { $('#ed-status').textContent = e.message; }
  };
  if (slug) {
    $('#ed-del').onclick = async () => { if (!confirm(`‘${slug}’ 스킬을 삭제할까요? 되돌릴 수 없습니다.`)) return; await api('/api/local/my-skills?slug=' + encodeURIComponent(slug), 'DELETE').catch(e => toast(e.message)); $('#dlg').close(); if (S.page === 'skills') RENDER.skills(); };
  }
  if (!$('#dlg').open) $('#dlg').showModal();
}

/* ---------- wiring ---------- */
document.addEventListener('click', e => {
  const b = e.target.closest('[data-subtab]'); if (!b) return;
  const [key, id] = b.dataset.subtab.split(':'); S.sub[key] = id; RENDER[S.page]();
});
window.addEventListener('hashchange', route);
buildShell();
route();
