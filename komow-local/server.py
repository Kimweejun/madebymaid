"""Loopback-only host for the original Komow UI and collected public runtimes."""
import argparse
import base64
import io
import json
import mimetypes
import os
import re
import shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit
import workspace

ROOT=Path(__file__).resolve().parent
SITE=ROOT/'site'
COLLECTION=ROOT.parent/'a4ai-import'
WEBAPPS=json.loads((COLLECTION/'webapps.json').read_text(encoding='utf-8-sig'))
MOUNTS={f'/komow_app/labs/artcraft/apps/{app["id"]}/{app["version"]}/':(COLLECTION/app['local_url'].lstrip('/')).parent for app in WEBAPPS}
MOUNTS['/local-downloads/']=COLLECTION/'downloads'
mimetypes.add_type('application/wasm','.wasm')
mimetypes.add_type('text/javascript','.mjs')
mimetypes.add_type('text/markdown','.md');mimetypes.add_type('image/webp','.webp')
ALLOWED_HOSTS={'127.0.0.1','localhost'}
PASSWORD=''  # required when bound to a non-loopback address (see __main__)

class Handler(SimpleHTTPRequestHandler):
    def allowed(self):
        if self.headers.get('Host','').split(':')[0] not in ALLOWED_HOSTS:return False
        if not PASSWORD or self.client_address[0] in ('127.0.0.1','::1'):return True  # this PC itself never needs the LAN password
        auth=self.headers.get('Authorization','')
        try:ok=auth.startswith('Basic ') and base64.b64decode(auth[6:]).decode().partition(':')[2]==PASSWORD
        except ValueError:ok=False
        if not ok:
            self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="Komow", charset="UTF-8"');self.send_header('Content-Length','0');self.end_headers()
            self.auth_failed=True
        return ok
    def deny(self):
        if not getattr(self,'auth_failed',False):self.reply({'error':'Host not allowed'},403)
    def same_origin(self):
        origin=self.headers.get('Origin');host=self.headers.get('Host','')
        return not origin or origin in ('http://'+host,'https://'+host)
    def workspace(self,method):
        parsed=urlsplit(self.path);query=parse_qs(parsed.query)
        try:
            if method=='GET':result=workspace.get(parsed.path,query)
            elif method=='DELETE':result=workspace.delete(parsed.path,query)
            else:
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply({'error':'JSON only'},415)
                size=int(self.headers.get('Content-Length','0'))
                if size<1 or size>(29_000_000 if parsed.path=='/api/local/files' else 300_000):return self.reply({'error':'요청 크기를 확인하세요.'},413)
                result=workspace.post(parsed.path,json.loads(self.rfile.read(size)))
        except (ValueError,KeyError,TypeError,AttributeError):
            return self.reply({'error':'입력 형식이 올바르지 않습니다.'},400)
        if result is None:return False
        self.reply(*result);return True
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        self.send_header('Cross-Origin-Embedder-Policy','require-corp')
        self.send_header('Cross-Origin-Resource-Policy','cross-origin' if getattr(self,'preview',False) else 'same-origin')  # sandboxed previews have an opaque origin
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-cache')
        super().end_headers()
    def reply(self,body,status=200,kind='application/json; charset=utf-8'):
        data=json.dumps(body,ensure_ascii=False).encode() if not isinstance(body,bytes) else body
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(data)
    def do_GET(self):
        if not self.allowed():return self.deny()
        path=urlsplit(self.path).path
        if path.startswith('/api/local/files/'):
            file_id=path.rsplit('/',1)[-1];mode=parse_qs(urlsplit(self.path).query).get('as',[''])[0]
            meta,raw=workspace.file_bytes(file_id)
            if not meta:return self.reply({'error':'파일을 찾을 수 없습니다.'},404)
            if mode=='pdf':  # 펼치기: Word·Excel·PowerPoint -> PDF via this PC's Office
                import preview
                raw=preview.office_pdf(file_id)
                if raw is None:return self.reply({'error':'이 파일은 미리 볼 수 없어요. 받아서 열어 주세요.'},415)
            kind='application/pdf' if mode=='pdf' else (mimetypes.guess_type(meta['name'])[0] or 'application/octet-stream')
            active=kind in ('text/html','image/svg+xml','application/xhtml+xml','text/xml','application/xml')
            # Pages that can run script are shown only inside the app's sandboxed frame (opaque origin) or as an <img>;
            # opened directly they download instead, so a result file can never act as this site.
            inline=mode in ('view','pdf') and (not active or self.headers.get('Sec-Fetch-Dest','') in ('iframe','image'))
            self.send_response(200)
            self.preview=inline
            if inline:
                if kind.startswith('text/') or kind in ('application/json','image/svg+xml'):kind+='; charset=utf-8'
                self.send_header('Content-Type',kind)  # no Content-Disposition: a sandboxed frame treats any as a blocked download
            else:
                self.send_header('Content-Type','application/octet-stream')
                self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(meta['name']))
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if path.startswith('/api/local/') and self.workspace('GET')!=False:return
        if path in ('/','/app'):
            self.send_response(302);self.send_header('Location','/app/');self.end_headers();return
        if path in ('/komow_app','/komow_app/','/komow_app/index.html'):  # old 꼬물이 screen was removed; tools link back here
            self.send_response(302);self.send_header('Location','/app/#workshop');self.end_headers();return
        if path=='/api/health':return self.reply({'service':'Komow Local','status':'ok'})
        if path=='/api/auth/me':return self.reply({'logged_in':False,'user':None,'local':True})
        if path=='/api/mcp-lab/manager':
            return self.reply({'ok':True,'servers':{},'counts':{},'can_install':False,'active':False,'installed_count':0,'ready_count':0,'hermes':{},'batch':{}})
        if path.startswith('/api/') or path.startswith('/mascot/') or path.startswith('/card/'):
            return self.reply({'ok':False,'error':'이 기능은 원본 서버·계정 연결이 필요합니다. 로컬 복사본에는 연결되어 있지 않습니다.','local':True},503)
        target=Path(self.translate_path(self.path))
        if not target.exists():
            if target.suffix in ('.html',''):
                return self.reply('<!doctype html><html lang="ko"><meta charset="utf-8"><style>body{background:#171a19;color:#ddd;font:16px system-ui;padding:32px;line-height:1.8}a{color:#eaa875}</style><h2>원본 서버 연결이 필요한 화면</h2><p>메뉴는 원본 그대로 유지했습니다. 이 화면의 실행 파일 또는 서버는 공개 자료에서 가져오지 못했습니다.</p><p>로그인·AI 모델·장비 연결은 별도 설정이 필요합니다.</p><a href="/app/#workshop" target="_top">작업 공방으로 돌아가기</a></html>'.encode(),503,'text/html; charset=utf-8')
            return self.reply({'error':'Public asset was not available','path':path},404)
        return super().do_GET()
    def do_HEAD(self):
        if not self.allowed():return self.deny()
        return super().do_HEAD()
    def do_POST(self):
        if not self.allowed():return self.deny()
        if not self.same_origin():return self.reply({'error':'Origin rejected'},403)
        if urlsplit(self.path).path.startswith('/api/local/') and self.workspace(self.command)!=False:return
        return self.reply({'ok':False,'error':'원본 서버의 실행·로그인 기능은 로컬에 연결되어 있지 않습니다.','local':True},503)
    do_PUT=do_POST
    do_DELETE=do_POST
    def translate_path(self,path):
        clean=unquote(urlsplit(path).path)
        base,relative=SITE,clean.lstrip('/')
        if clean.startswith('/app/'):
            base,relative=ROOT/'app',clean[len('/app/'):] or 'index.html'
        if clean.startswith('/local/'):
            base,relative=ROOT/'local',clean[len('/local/'):]
        for prefix,mount in MOUNTS.items():
            if clean.startswith(prefix):base,relative=mount,clean[len(prefix):];break
        dest=(base/relative).resolve()
        return str(dest if dest.is_relative_to(base.resolve()) else ROOT/'__not_found__')
    def list_directory(self,path):return self.send_error(404)
    def send_head(self):
        target=Path(self.translate_path(self.path))
        if target.is_dir() and (target/'index.html').is_file():target=target/'index.html'
        if target.is_file() and target.suffix=='.html' and not target.is_relative_to(ROOT/'app'):
            text=target.read_text(encoding='utf-8',errors='replace')
            text=re.sub(r'<script\b[^>]*src=["\']https://static\.cloudflareinsights\.com[^>]*>.*?</script>','',text,flags=re.S|re.I)
            stamp=int(max((ROOT/'local'/n).stat().st_mtime for n in ('bridge.js',)))  # cache-bust local edits
            text=text.replace('<head>',f'<head><script src="/local/bridge.js?v={stamp}" data-v="{stamp}"></script>',1)
            raw=text.encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers()
            return io.BytesIO(raw)
        if target.is_file() and self.headers.get('Range'):
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
            if match:
                size=target.stat().st_size;start=int(match[1]);end=min(int(match[2]) if match[2] else size-1,size-1)
                if start>end:return self.send_error(416)
                self.send_response(206);self.send_header('Content-Type',self.guess_type(str(target)));self.send_header('Content-Length',str(end-start+1));self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.end_headers()
                with target.open('rb') as f:f.seek(start);return io.BytesIO(f.read(end-start+1))
        return super().send_head()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=int(os.environ.get('PORT',8788)))
    parser.add_argument('--host',default=os.environ.get('KOMOW_HOST','127.0.0.1'))
    args=parser.parse_args()
    import worklog
    worklog.log('server', 'server', 'start', f'listening {args.host}:{args.port}')
    ALLOWED_HOSTS.update(h.strip() for h in os.environ.get('KOMOW_ALLOWED_HOSTS','').split(',') if h.strip())
    PASSWORD=os.environ.get('KOMOW_PASSWORD','')
    if args.host not in ('127.0.0.1','localhost','::1') and len(PASSWORD)<12:
        raise SystemExit('외부 주소로 열 때는 KOMOW_PASSWORD(12자 이상)와 KOMOW_ALLOWED_HOSTS를 설정해야 합니다.')
    import collectors
    collectors.start()
    print(f'madebymaid: http://{args.host}:{args.port}/',flush=True)
    ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
