"""펼치기 미리 보기: Word·Excel·PowerPoint files become a PDF (via the Office already on this PC), cached per file.

Everything else is previewed in the browser itself (HTML in a sandboxed frame, Markdown, images, PDF via pdf.js,
HWP/HWPX via the rhwp viewer's WASM). Conversion is one at a time; a file that fails is not retried until restart.
"""
import subprocess
import threading

import workspace

OFFICE = {'.doc': 'word', '.docx': 'word', '.rtf': 'word', '.odt': 'word',
          '.xls': 'excel', '.xlsx': 'excel', '.ods': 'excel',
          '.ppt': 'powerpoint', '.pptx': 'powerpoint', '.odp': 'powerpoint'}
_lock = threading.Lock()
_failed = set()

SCRIPT = {  # $src / $dst are filled in; every app is opened read-only, invisible, and always closed
    'word': "$a=New-Object -ComObject Word.Application;$a.Visible=$false;$a.DisplayAlerts=0;try{$d=$a.Documents.Open($src,$false,$true);$d.ExportAsFixedFormat($dst,17);$d.Close(0)}finally{$a.Quit()}",
    'excel': "$a=New-Object -ComObject Excel.Application;$a.Visible=$false;$a.DisplayAlerts=$false;try{$w=$a.Workbooks.Open($src,0,$true);$w.ExportAsFixedFormat(0,$dst);$w.Close($false)}finally{$a.Quit()}",
    'powerpoint': "$a=New-Object -ComObject PowerPoint.Application;try{$p=$a.Presentations.Open($src,$true,$false,$false);$p.SaveAs($dst,32);$p.Close()}finally{$a.Quit()}",
}


def office_pdf(file_id):
    """PDF bytes for an Office file, converted once and cached in data/previews/. None when it cannot be done."""
    meta, raw = workspace.file_bytes(file_id)
    if not meta:
        return None
    ext = '.' + meta['name'].rsplit('.', 1)[-1].lower() if '.' in meta['name'] else ''
    app = OFFICE.get(ext)
    folder = workspace.DATA / 'previews'
    pdf = folder / f'{file_id}.pdf'
    if pdf.is_file():
        return pdf.read_bytes()
    if not app or file_id in _failed:
        return None
    with _lock:
        if pdf.is_file():
            return pdf.read_bytes()
        folder.mkdir(parents=True, exist_ok=True)
        src = folder / f'{file_id}{ext}'
        src.write_bytes(raw)
        ps = f"$ErrorActionPreference='Stop';$src='{src}';$dst='{pdf}';" + SCRIPT[app]
        try:
            subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], capture_output=True, timeout=120,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, subprocess.TimeoutExpired):
            pass
        src.unlink(missing_ok=True)
        if not pdf.is_file():
            _failed.add(file_id)
            return None
        return pdf.read_bytes()
