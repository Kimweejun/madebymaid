import json
import threading
import unittest
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
import base64,tempfile
from pathlib import Path
import server,workspace
from server import Handler,ThreadingHTTPServer,SITE,MOUNTS,ROOT

class Assets(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script' and a.get('src'):self.urls.append(a['src'])
        if tag=='link' and a.get('rel')=='stylesheet':self.urls.append(a['href'])

class LocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();workspace.DATA=Path(cls.tmp.name)
        import runner;runner.start=lambda *a,**k:'';runner.start_plain=lambda *a,**k:''  # tests must never launch real 렘·람 runs
        import os,worklog;os.environ['MADEBYMAID_WORKLOG']=str(Path(cls.tmp.name)/'work.jsonl');worklog.FILE=Path(os.environ['MADEBYMAID_WORKLOG']);worklog.LOGS=worklog.FILE.parent  # never touch the real work log
        workspace.LAB=Path(cls.tmp.name)/'lab'
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
    def get(self,path,headers={}):return urllib.request.urlopen(urllib.request.Request(self.base+path,headers=headers),timeout=10)
    def test_new_ui_and_old_screen_redirect(self):
        with self.get('/') as r:self.assertTrue(r.geturl().endswith('/app/'))
        with self.get('/app/') as r:html=r.read().decode()
        self.assertIn('메이드 바이 메이드',html);self.assertNotIn('/local/bridge.js',html)
        with self.get('/komow_app/index.html') as r:self.assertIn('/app/',r.geturl())
        for t in json.load(open(ROOT/'app/tools.json',encoding='utf-8')):
            with self.subTest(tool=t['slug']),self.get(t['url']) as r:self.assertEqual(r.status,200)
    def test_craft_mounts(self):
        for prefix in MOUNTS:
            if '/artcraft/' not in prefix:continue
            with self.subTest(app=prefix),self.get(prefix+'index.html') as r:self.assertEqual(r.status,200)
    def test_video_range(self):
        path='/komow_app/labs/mediabunny/sample.mp4'
        # Choose the collected sample's actual path, independent of filename changes.
        sample=next((SITE/'komow_app/labs/mediabunny').rglob('*.mp4'))
        path='/'+sample.relative_to(SITE).as_posix()
        with self.get(path,{'Range':'bytes=0-31'}) as r:
            self.assertEqual(r.status,206);self.assertEqual(len(r.read()),32)
    def test_no_fake_auth_or_remote_mutation(self):
        with self.get('/api/auth/me') as r:self.assertFalse(json.load(r)['logged_in'])
        req=urllib.request.Request(self.base+'/api/auth/login',data=b'{}',headers={'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as raised:urllib.request.urlopen(req)
        self.assertEqual(raised.exception.code,503)
    def test_host_and_path_boundaries(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:self.get('/api/health',{'Host':'untrusted.example'})
        self.assertEqual(raised.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError):self.get('/local/%2e%2e/server.py')
        with self.assertRaises(urllib.error.HTTPError):self.get('/komow_app/assets/')
        with self.assertRaises(urllib.error.HTTPError):self.get('/app/../server.py')

    def call(self,path,method='GET',data=None):
        req=urllib.request.Request(self.base+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=10) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_workspace_skills(self):
        code,body=self.call('/api/local/skills');self.assertEqual(code,200);self.assertGreater(len(body['skills']),0)
        code,body=self.call('/api/local/skills?id='+body['skills'][0]['id']);self.assertTrue(body['content'])
        code,body=self.call('/api/local/my-skills','POST',{'content':'---\nname: My Skill 1\ndescription: 테스트\n---\n본문'})
        self.assertEqual((code,body['slug']),(201,'my-skill-1'))
        self.assertEqual(self.call('/api/local/my-skills')[1]['skills'][0]['description'],'테스트')
        self.assertEqual(self.call('/api/local/my-skills','POST',{'slug':'../x','content':'a'})[0],400)
        self.assertEqual(self.call('/api/local/my-skills?slug=..','DELETE')[0],404)
        self.assertEqual(self.call('/api/local/my-skills?slug=my-skill-1','DELETE')[0],200)
        self.assertEqual(self.call('/api/local/my-skills')[1]['skills'],[])
    def test_workspace_experiments(self):
        code,item=self.call('/api/local/experiments','POST',{'title':'첫 실험','rating':9})
        self.assertEqual((code,item['rating']),(201,5))
        self.assertEqual(self.call('/api/local/experiments','POST',{'title':' '})[0],400)
        self.call('/api/local/experiments?id='+item['id'],'DELETE')
        self.assertEqual(self.call('/api/local/experiments')[1]['experiments'],[])
    def test_feed_safety_and_parsing(self):
        for url in ('http://127.0.0.1/feed','http://169.254.169.254/latest','file:///etc/passwd'):
            self.assertFalse(workspace.public_url(url),url)
            self.assertEqual(self.call('/api/local/feeds','POST',{'url':url})[0],400)
        rss=b'<rss><channel><item><title>A</title><link>https://a</link><pubDate>Mon</pubDate></item></channel></rss>'
        atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>B</title><link href="https://b"/><updated>2026</updated></entry></feed>'
        self.assertEqual(workspace.parse_feed(rss),[{'title':'A','link':'https://a','date':'Mon'}])
        self.assertEqual(workspace.parse_feed(atom),[{'title':'B','link':'https://b','date':'2026'}])
    def test_new_ui_data_and_storage(self):
        workspace.save_data('aitimes.json',[{'id':'1','title':'기사','summary':'요약','url':'https://www.aitimes.com/x','category':'정책','date':'2026-10-14T10:00:00+09:00'}])
        workspace.save_data('support.json',[{'title':'경북 AI 지원사업','url':'https://x.kr/1','source':'경북테크노파크','region':'경북','date':'2026-10-14'}])
        workspace.save_data('community_reddit.json',{'posts':[{'id':'r1','sub':'ClaudeAI','title':'글','url':'https://reddit.com/x','date':'2026-10-14'}]})
        for path in ('/api/local/news?source=aitimes','/api/local/news','/api/local/support','/api/local/support?area=dg','/api/local/community/reddit?sub=ClaudeAI','/api/local/tools'):
            code,body=self.call(path);self.assertEqual(code,200,path);self.assertTrue(body.get('items') or body.get('tools'),path)
        self.assertEqual(self.call('/api/local/community/reddit?sub=OpenAI')[1]['items'],[])
        self.assertEqual(self.call('/api/local/posts')[0],503)  # old board removed
        code,src=self.call('/api/local/community/sources','POST',{'kind':'reddit','value':'LocalLLaMA'});self.assertEqual(code,200)
        self.assertEqual(self.call('/api/local/community/sources','POST',{'kind':'reddit','value':'../x'})[0],400)
        code,src=self.call('/api/local/community/sources','POST',{'kind':'github_keywords','value':'rag'});self.assertIn('rag',src['github_keywords'])
        code,src=self.call('/api/local/community/sources','POST',{'kind':'github_keywords','value':'rag','remove':True});self.assertNotIn('rag',src['github_keywords'])
        code,item=self.call('/api/local/files','POST',{'name':'../a.txt','content':base64.b64encode(b'hello').decode(),'folder':'보고서'})
        self.assertEqual((code,item['name']),(201,'a.txt'))
        self.assertTrue(self.call('/api/local/files','POST',{'name':'b.txt','content':base64.b64encode(b'hello').decode()})[1]['duplicate'])
        with self.get('/api/local/files/'+item['id']) as r:self.assertEqual(r.read(),b'hello')
        self.assertEqual(self.call('/api/local/files/../../server.py')[0],404)
        self.assertEqual(self.call('/api/local/files?id='+item['id'],'DELETE')[0],200)
        self.assertEqual(self.call('/api/local/files')[1]['files'],[])
    def test_password(self):
        server.PASSWORD='correct-horse-battery'
        try:
            with self.get('/api/health') as r:self.assertEqual(r.status,200)  # this PC itself: no password
            fake=type('H',(),{'headers':{'Host':'127.0.0.1:8788','Authorization':''},'client_address':('192.168.0.5',1),
                              'send_response':lambda s,c:setattr(s,'code',c),'send_header':lambda s,*a:None,'end_headers':lambda s:None})()
            self.assertFalse(server.Handler.allowed(fake));self.assertEqual(fake.code,401)  # a phone on the LAN must log in
            fake.headers['Authorization']='Basic '+base64.b64encode(b'me:correct-horse-battery').decode()
            self.assertTrue(server.Handler.allowed(fake))
        finally:server.PASSWORD=''

    def test_collector_parsers_and_maids(self):
        import collectors,maids,os,time
        page='<article class="Box-row"><h2 class="h3"><a href="/a/b" class="Link"><svg><path/></svg> a / b</a></h2><p class="col-9 color-fg-muted my-1"> 설명 </p><span itemprop="programmingLanguage">Python</span><a href="/a/b/stargazers" class="Link"> 1,234</a> 56 stars today</article>'
        self.assertEqual(collectors.parse_trending(page),[{'id':'a/b','title':'a/b','url':'https://github.com/a/b','summary':'설명','language':'Python','stars':1234,'gain':56}])
        log=Path(self.tmp.name)/'events.log'
        now=int(time.time()*1000)
        for ev,state in (({'event':'PreToolUse','tool':'Bash'},'working'),({'event':'PreToolUse','tool':'Read'},'review'),({'event':'Notification'},'waiting'),({'event':'Stop'},'done')):
            log.write_text('x\n'+json.dumps({**ev,'ts':now})+'\n',encoding='utf-8');maids.CLAUDE_LOG=log
            self.assertEqual(maids.claude()['state'],state,ev)
        log.write_text('x\n'+json.dumps({'event':'PreToolUse','tool':'Bash','ts':now-3_600_000})+'\n',encoding='utf-8')
        self.assertEqual(maids.claude()['state'],'idle')
    def test_usnews_parse_and_deepl_cap(self):
        import collectors
        page='x"stories":[{"id":"a1","headline":"AI &amp; chips","deck":"Deck","permalink":"https://www.usnews.com/a","overline":{"text":"Business News"},"pubdate":"Oct. 14, 2026"}],"y":1'
        self.assertEqual([s['headline'] for s in collectors.usnews_stories(page)],['AI &amp; chips'])
        self.assertEqual(collectors.translate_budget(),0)  # no key -> never call DeepL
        workspace.save_data('secrets.json',{'deepl':{'auth_key':'test:fx'}})
        month=__import__('datetime').datetime.now(collectors.KST).strftime('%Y-%m')
        workspace.save_data('translate_usage.json',{'month':month,'chars':collectors.DEEPL_MONTHLY_CAP-10})
        real=collectors.fetch
        collectors.fetch=lambda *a,**k:(_ for _ in ()).throw(OSError('offline'))
        try:
            self.assertEqual(collectors.translate_budget(),10)
            self.assertIsNone(collectors.translate_many(['this text is longer than ten characters']))  # over the cap -> skipped
        finally:
            collectors.fetch=real
            workspace.save_data('secrets.json',{})
    def test_support_board_parser(self):
        import support
        page=("<table><tr><th>제목</th></tr>"
              "<tr><td>3</td><td><a href=\"javascript:void(0);\" onclick=\"fn_view('notice','','6530')\">2026-01-0126 AI 바우처 지원사업 공고</a></td><td>2026-10-01 ~ 2026-10-20</td></tr>"
              "<tr><td><a href=\"/view?id=9\">766 데이터 활용 기업 모집 공고 2026.10.14 24</a></td></tr></table>"
              "<ul><li onclick=\"goPage('S', null, '/biz/applyInfo/3849')\"><strong>스마트 물류 기업지원사업 모집공고</strong><span>접수기간 : 2026-10-13 ~ 2026-10-31</span></li></ul>")
        rows=support.parse_board(page.split('<ul>')[0],'https://x.kr/list','https://x.kr/v?id={1}')+support.parse_board('<ul>'+page.split('<ul>')[1],'https://x.kr/list')
        self.assertEqual([(r['title'],r['url'],r['date'],r['period']) for r in rows],[
            ('2026-01-0126 AI 바우처 지원사업 공고','https://x.kr/v?id=6530','2026-10-01','2026-10-01 ~ 2026-10-20'),
            ('데이터 활용 기업 모집 공고','https://x.kr/view?id=9','2026-10-14',''),
            ('스마트 물류 기업지원사업 모집공고','https://x.kr/biz/applyInfo/3849','2026-10-13','2026-10-13 ~ 2026-10-31')])
        src={'id':'t','name':'t','group':'C','url':'https://x.kr/list','pages':1,'include':'모집','exclude':'데이터'}
        real=support.fetch;support.fetch=lambda *a,**k:page
        try:self.assertEqual([r['title'] for r in support.collect_source(src)],['스마트 물류 기업지원사업 모집공고'])
        finally:support.fetch=real
    def test_support_block_backoff(self):
        import support,urllib.error,time
        src={'id':'x','name':'막힌곳','group':'D','url':'https://x.kr/list','robots_blocked':True}
        real=support.collect_source
        def blocked(*a,**k): raise urllib.error.HTTPError('https://x.kr/list',403,'Forbidden',{},None)
        try:
            support.collect_source=blocked
            rows,st=support.visit(src,{},frozenset());self.assertEqual((rows,st['fails'],st['blocked']),([],1,False))
            rows,st=support.visit(src,st,frozenset());self.assertTrue(st['blocked']);self.assertIn('403',st['error'])
            self.assertGreater(st['next_try'],time.time()+3600)
            support.collect_source=lambda *a,**k:[{'url':'u'}]
            rows,skipped=support.visit(src,st,frozenset());self.assertEqual(rows,[]);self.assertTrue(skipped['skipped'])  # backing off
            rows,ok=support.visit(src,{**st,'next_try':0},frozenset());self.assertEqual((len(rows),ok['fails'],ok['blocked']),(1,0,False))
        finally:support.collect_source=real
    def test_scoring_rules(self):
        import scoring
        from datetime import datetime
        today=datetime(2026,10,14,tzinfo=scoring.KST)
        good=scoring.score_support({'title':'[경북] 2026년 제조 AI 실증 지원사업 참여기업 모집','region':'전국','period':'2026-10-01 ~ 2026-11-30'},today)
        far=scoring.score_support({'title':'[경기] 2026년 제조 AI 실증 지원사업 참여기업 모집','region':'전국','period':'2026-10-01 ~ 2026-11-30'},today)
        soon=scoring.score_support({'title':'경북 로봇 실증 참여기업 모집','region':'경북','period':'2026-10-01 ~ 2026-10-18'},today)
        self.assertEqual(good['score'],scoring.score_support({'title':'[경북] 2026년 제조 AI 실증 지원사업 참여기업 모집','region':'전국','period':'2026-10-01 ~ 2026-11-30'},today)['score'])  # deterministic
        self.assertGreater(good['score'],far['score']);self.assertIn('지역 25/25 (경북)',good['reasons'])
        self.assertTrue(soon['deadline_soon']);self.assertEqual(soon['days_left'],4)
        self.assertTrue(scoring.score_support({'title':'AI 플랫폼 구축 용역 입찰 공고'},today)['excluded'])
        self.assertEqual(scoring.hits('MAID AI 연구','AI'.split()),['AI']);self.assertEqual(scoring.hits('MAIDEN',['AI']),[])
        now=datetime(2026,10,14,12,tzinfo=scoring.KST)
        items=[{'title':'앤트로픽 국방부 공급망 위험 지정 재심 청구','source':'aitimes','date':'2026-10-14T10:00:00+09:00'},
               {'title':'앤트로픽 국방부 공급망 위험 지정 불복 재심 청구','source':'naver','date':'2026-10-14T09:00:00+09:00'},
               {'title':'프로야구 결승전 결과','source':'naver','date':'2026-10-14T09:00:00+09:00'}]
        sc=scoring.score_news_all(items,now)
        self.assertIn('1개 다른 출처',sc[0]['reasons'][1]);self.assertTrue(sc[2]['excluded'])
        votes=scoring.add_feedback('support',{'url':'https://x/1','title':'t','score':80},'up');self.assertEqual(votes,{'https://x/1':'up'})
        self.assertEqual(scoring.add_feedback('support',{'url':'https://x/1','title':'t'},''),{})
    def test_bookmarks(self):
        import scoring
        real=scoring.support_scored
        rows=[{'url':'https://x/open','title':'열린 공고','source':'A','period':'2026-10-01 ~ 2099-12-31','days_left':9000,'score':50},
              {'url':'https://x/soon','title':'곧 마감','source':'A','period':'2026-10-01 ~ 2026-10-20','days_left':6,'score':50},
              {'url':'https://x/gone','title':'지난 공고','source':'B','period':'2026-01-01 ~ 2026-02-01','days_left':-255,'score':50}]
        scoring.support_scored=lambda:rows
        try:
            for u in ('https://x/open','https://x/gone','https://x/soon'):self.assertEqual(workspace.post('/api/local/bookmarks',{'url':u,'on':True})[1],200)
            self.assertEqual(workspace.post('/api/local/bookmarks',{'url':'https://evil/','on':True})[1],404)
            rows.pop()  # dropped from the collected list: snapshot keeps it, days_left recomputed from period
            d=workspace.get('/api/local/support',{'area':['star']})[0]
            self.assertEqual([i['url'] for i in d['items']],['https://x/soon','https://x/open','https://x/gone'])
            self.assertTrue(d['items'][-1]['closed']);self.assertEqual(d['star_count'],3)
            self.assertTrue(all(i['starred'] for i in d['items']))
            workspace.post('/api/local/bookmarks',{'url':'https://x/soon','on':False})
            self.assertEqual(workspace.get('/api/local/support',{'area':['star']})[0]['total'],2)
        finally:scoring.support_scored=real
    def test_experiment_handoff(self):
        workspace.save_data('experiments.json',[])
        x,code=workspace.post('/api/local/experiments',{'title':'open-code-review','url':'https://github.com/a/b','kind':'try','maids':['rem','ram']})
        self.assertEqual(code,201);self.assertRegex(x['no'],r'^EXP-\d{4}-01$');self.assertEqual(x['status'],'sent')
        self.assertIn(x['no']+'_open-code-review.md',x['prompts']['rem']);self.assertIn('outputs','\n'.join(x['prompts'].values()))
        self.assertTrue(workspace.post('/api/local/experiments',{'title':'t','kind':'try','maids':['rem']})[0]['no'].endswith('-02'))
        with self.assertRaises(ValueError):workspace.post('/api/local/experiments',{'title':'t','kind':'hack','maids':['rem']})
        f=workspace.store_file(b'# result '+x['no'].encode(),x['no']+'_open-code-review.md','람')
        self.assertEqual(f['experiment'],x['no'])
        got=[i for i in workspace.load_data('experiments.json',[]) if i.get('no')==x['no']][0]
        self.assertEqual((got['status'],got['results'][0]['maid']),('arrived','ram'))
        r,_=workspace.post('/api/local/experiments/rate',{'id':x['id'],'rating':4,'result':'좋음'});self.assertEqual(r['status'],'rated')
        self.call('/api/local/files?id='+f['id'],'DELETE')
        p,_=workspace.post('/api/local/experiments',{'title':'deck','kind':'ppt','maids':['rem']})
        self.assertIn('deck.py',p['prompts']['rem']);self.assertIn('madebymaid-ppt-analysis',p['prompts']['rem'])
        w=workspace.store_file(b'https://kimweejun.github.io/madebymaid-reports/'+p['no'].encode()+b'/\n',p['no']+'_웹주소.txt','렘')
        got=[i for i in workspace.load_data('experiments.json',[]) if i.get('no')==p['no']][0]
        self.assertEqual(got['results'][0]['web'],'https://kimweejun.github.io/madebymaid-reports/'+p['no']+'/')
        t1=workspace.store_file(('# '+p['no']+' 생성할 그림\n\n## 5번 슬라이드\n\n개념도').encode(),p['no']+'_이미지프롬프트.md','렘')
        got=[i for i in workspace.load_data('experiments.json',[]) if i.get('no')==p['no']][0];self.assertIn('madebymaid-image-gen',got['image_task'])
        t2=workspace.store_file(('# '+p['no']+'\n\n생성할 그림 없음\n').encode(),p['no']+'_이미지프롬프트.md','렘')
        got=[i for i in workspace.load_data('experiments.json',[]) if i.get('no')==p['no']][0];self.assertEqual(got['image_task'],'')
        for f_ in (w,t1,t2):self.call('/api/local/files?id='+f_['id'],'DELETE')
        workspace.save_data('experiments.json',[])
    def test_runner_handoff(self):
        import runner
        started=[];real=runner.start
        runner.start=lambda x,m,p,t='main':started.append((x['no'],m,t)) or ''
        try:
            workspace.save_data('experiments.json',[])
            x,_=workspace.post('/api/local/experiments',{'title':'t','kind':'review','maids':['rem','ram'],'run':True})
            self.assertEqual([s[1] for s in started],['rem','ram']);self.assertEqual(x['run_errors'],[])
            self.assertIn('설치 필요',x['prompts']['rem'])
            self.assertEqual(workspace.post('/api/local/experiments/run',{'id':x['id'],'maid':'rem','task':'image'})[1],404)  # no image task yet
            self.assertEqual(workspace.post('/api/local/experiments/run',{'id':x['id'],'maid':'ram'})[1],202)
            items=workspace.load_data('experiments.json',[]);items[0]['runs']={'rem':{'state':'running'}}
            self.assertEqual(runner.refresh(items)[0]['runs']['rem']['state'],'ended')  # not started by this server
        finally:
            runner.start=real;workspace.save_data('experiments.json',[])
    def test_tags(self):
        import tagging
        t=tagging.by_rules('Whisper speech diarization for drone defense')
        self.assertEqual(t['tech'][0],'음성');self.assertIn('국방·안보',t['field'])
        self.assertEqual(tagging.by_rules('nvm node version manager')['tech'],[])
        self.assertEqual(tagging.hits('MCP server','mcp'.split()),1);self.assertEqual(tagging.hits('compute','mcp'.split()),0)
        items=[{'url':'https://x/1','title':'speech model'},{'url':'https://x/2','title':'nvm'}]
        tagging.attach(items,lambda i:i['url'],lambda i:i['title'])
        self.assertEqual(items[1]['tags']['tech'],['미분류'])
        workspace.post('/api/local/tags',{'key':'https://x/1','tech':['비전','가짜','음성','언어·LLM'],'field':[]})
        tagging.attach(items,lambda i:i['url'],lambda i:i['title'])
        self.assertEqual((items[0]['tags']['tech'],items[0]['tags']['src']),(['비전','음성'],'manual'))  # only known labels, max 2
        workspace.post('/api/local/tags',{'key':'https://x/1','tech':[],'field':[]})  # back to automatic
        tagging.attach(items,lambda i:i['url'],lambda i:i['title']);self.assertEqual(items[0]['tags']['src'],'rule')
        with self.assertRaises(ValueError):workspace.post('/api/local/tags',{'key':'javascript:x','tech':['비전']})
        tools=json.loads((workspace.ROOT/'app'/'tools.json').read_text(encoding='utf-8'))
        self.assertTrue(all(tagging.tool_base(t) for t in tools))  # every workshop tool hand-tagged
    def test_file_preview(self):
        f=workspace.store_file(b'<script>alert(1)</script>','page.html','t');m=workspace.store_file(b'# hi','note.md','t')
        try:
            with self.get('/api/local/files/'+f['id']+'?as=view') as r:self.assertIn('attachment',r.headers.get('Content-Disposition',''))  # opened directly: download only
            with self.get('/api/local/files/'+f['id']+'?as=view',{'Sec-Fetch-Dest':'iframe'}) as r:
                self.assertTrue(r.headers['Content-Type'].startswith('text/html'));self.assertIsNone(r.headers.get('Content-Disposition'))
            with self.get('/api/local/files/'+m['id']+'?as=view') as r:self.assertTrue(r.headers['Content-Type'].startswith('text/markdown'))
            with self.assertRaises(urllib.error.HTTPError) as e:self.get('/api/local/files/'+m['id']+'?as=pdf')
            self.assertEqual(e.exception.code,415)  # only Office files convert
        finally:
            for x in (f,m):self.call('/api/local/files?id='+x['id'],'DELETE')
    def test_worklog(self):
        import worklog,runner,threading,time
        e=worklog.log('EXP-1015-09','ram','start','main');self.assertEqual(e['ev'],'start')
        threading.Timer(0.5,lambda:worklog.log('EXP-1015-09','ram','done','ok')).start()
        t=time.time();d,_=workspace.get('/api/local/log',{'after':[str(e['n'])],'wait':['5']})
        self.assertLess(time.time()-t,4);self.assertEqual([x['ev'] for x in d['events']],['done']);self.assertEqual(d['last'],e['n']+1)
        self.assertEqual(workspace.get('/api/local/log',{'after':['0'],'job':['EXP-1015-09']})[0]['events'][0]['msg'],'main')
        # CLI event parsing: Codex --json and Claude stream-json
        self.assertEqual(runner.steps('rem',{'type':'item.started','item':{'type':'command_execution','command':'git push'}}),('step','run: git push'))
        self.assertEqual(runner.steps('rem',{'type':'item.completed','item':{'type':'agent_message','text':'끝'}}),('final','끝'))
        self.assertEqual(runner.steps('ram',{'type':'assistant','message':{'content':[{'type':'tool_use','name':'WebFetch','input':{'url':'https://a.b'}}]}}),('step','web: https://a.b'))
        self.assertEqual(runner.steps('ram',{'type':'result','is_error':True,'result':'boom'}),('error','boom'))
        self.assertIsNone(runner.steps('ram',{'type':'system'}))
    def test_deck_rules(self):
        import json,subprocess,sys
        bad=Path(self.tmp.name)/'deck.json';bad.write_text(json.dumps({'no':'EXP-1014-01','maid':'람','title':'t','slides':[],'conclusion':{}}),encoding='utf-8')
        r=subprocess.run([sys.executable,str(Path(__file__).parent/'ppt'/'deck.py'),'build',str(bad)],capture_output=True,text=True,encoding='utf-8',env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'})
        self.assertNotEqual(r.returncode,0);self.assertIn('5~9장',r.stderr)
        sl=[{'title':f's{i}','points':['p'],'summary':['s']} for i in range(6)]
        bad.write_text(json.dumps({'no':'EXP-1014-01','maid':'람','title':'t','theme':'현장','slides':sl,'conclusion':{'verdict':'추천','headline':'h','reasons':[{'text':'r'}]}}),encoding='utf-8')
        r=subprocess.run([sys.executable,str(Path(__file__).parent/'ppt'/'deck.py'),'build',str(bad)],capture_output=True,text=True,encoding='utf-8',env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'})
        self.assertIn('그래프·그림이 2개 이상',r.stderr)
    def test_outbox_ingest(self):
        import os,time
        box=Path(self.tmp.name)/'outputs';workspace.OUTBOX=box
        (box/'람').mkdir(parents=True);f=box/'람'/'report.md';f.write_text('결과',encoding='utf-8')
        old=time.time()-60;os.utime(f,(old,old))
        self.assertEqual(workspace.ingest_outbox(),1);self.assertEqual(workspace.ingest_outbox(),0)
        item=[x for x in workspace.file_list() if x['name']=='report.md'][0]
        self.assertEqual(item['folder'],'람');self.call('/api/local/files?id='+item['id'],'DELETE')

if __name__=='__main__':unittest.main()
