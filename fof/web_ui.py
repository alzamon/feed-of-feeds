"""Locally hosted web UI for FoF - replaces the curses ControlLoop."""
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from .platform_quirks import open_url_in_browser

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<meta name="viewport"
  content="width=device-width,initial-scale=1.0">
<title>FoF</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{
  font-family:system-ui,-apple-system,sans-serif;
  background:#1a1a1a;color:#e0e0e0;
  display:flex;flex-direction:column;
  user-select:none;
}
#hdr{
  padding:8px 12px;background:#252525;
  border-bottom:1px solid #333;flex-shrink:0;
}
#art-title{
  font-size:1em;font-weight:600;
  white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;margin-bottom:3px;
}
#art-meta{
  font-size:0.72em;color:#999;
  display:flex;flex-wrap:wrap;gap:6px;
}
#main{
  flex:1;display:flex;flex-direction:column;
  min-height:0;position:relative;
  cursor:grab;
}
#main.dragging{cursor:grabbing}
/* Transparent capture layer over iframe during drag */
#drag-overlay{
  position:absolute;inset:0;z-index:10;
  pointer-events:none;
}
#main.dragging #drag-overlay{pointer-events:all}
/* Draggable card */
#card{
  flex:1;display:flex;flex-direction:column;
  min-height:0;position:relative;
}
#card.snap-back{
  transition:transform 0.3s cubic-bezier(.25,.46,.45,.94),
             opacity 0.3s;
}
#card.fly-out{
  transition:transform 0.3s ease-in,opacity 0.3s;
}
/* Colour-wash overlays */
#wash-like,#wash-dis{
  position:absolute;inset:0;
  opacity:0;pointer-events:none;z-index:5;
}
#wash-like{background:rgba(0,200,0,0.18)}
#wash-dis{background:rgba(200,0,0,0.18)}
/* Emoji hint badges */
#hint-like,#hint-dis{
  position:absolute;top:50%;
  transform:translateY(-50%);
  font-size:3.5em;opacity:0;
  pointer-events:none;z-index:20;
  text-shadow:0 2px 10px rgba(0,0,0,0.6);
}
#hint-like{right:20px}
#hint-dis{left:20px}
#iframe-wrap{flex:1;min-height:0}
#frm{
  width:100%;height:100%;
  border:none;background:#fff;display:block;
}
#fallback{
  flex:1;overflow-y:auto;padding:12px;
  display:none;flex-direction:column;gap:8px;
}
#fallback.show{display:flex}
#content-preview{
  font-size:0.88em;line-height:1.6;
  white-space:pre-wrap;word-break:break-word;
  color:#ccc;background:#222;
  padding:10px;border-radius:4px;
}
#open-link{font-size:0.9em;color:#6af}
#open-link:hover{text-decoration:underline}
#no-art{
  flex:1;display:none;align-items:center;
  justify-content:center;
  color:#666;font-size:1.1em;
}
#no-art.show{display:flex}
/* Drag hint label */
#drag-hint{
  position:absolute;bottom:26px;
  left:0;right:0;text-align:center;
  font-size:0.72em;color:#555;
  pointer-events:none;z-index:15;
}
#status{
  flex-shrink:0;padding:3px 12px;
  font-size:0.75em;color:#777;
  background:#202020;min-height:20px;
}
</style>
</head>
<body>
<div id="hdr">
  <div id="art-title">Loading\u2026</div>
  <div id="art-meta"></div>
</div>
<div id="main">
  <div id="drag-overlay"></div>
  <div id="card">
    <div id="wash-dis"></div>
    <div id="wash-like"></div>
    <div id="hint-dis">\U0001f44e</div>
    <div id="hint-like">\U0001f44d</div>
    <div id="iframe-wrap">
      <iframe id="frm"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        src="about:blank" title="Article"></iframe>
    </div>
    <div id="fallback">
      <div id="content-preview"></div>
      <a id="open-link" href="#" target="_blank"
        rel="noopener">Open article in new tab \u2197</a>
    </div>
    <div id="no-art">All caught up! No more articles.</div>
    <div id="drag-hint">\u2190 drag to skip \u00b7 drag to like \u2192</div>
  </div>
</div>
<div id="status"></div>
<script>
'use strict';
var THRESHOLD=80;
var main=document.getElementById('main');
var card=document.getElementById('card');
var hintL=document.getElementById('hint-like');
var hintD=document.getElementById('hint-dis');
var wL=document.getElementById('wash-like');
var wD=document.getElementById('wash-dis');
var dragging=false,startX=0,startY=0;

function applyDrag(dx){
  card.style.transform=
    'translateX('+dx+'px) rotate('+(dx*0.04)+'deg)';
  var r=Math.min(Math.abs(dx)/THRESHOLD,1);
  if(dx>0){
    hintL.style.opacity=r;hintD.style.opacity=0;
    wL.style.opacity=r*0.9;wD.style.opacity=0;
  }else if(dx<0){
    hintD.style.opacity=r;hintL.style.opacity=0;
    wD.style.opacity=r*0.9;wL.style.opacity=0;
  }else{
    hintL.style.opacity=0;hintD.style.opacity=0;
    wL.style.opacity=0;wD.style.opacity=0;
  }
}

function clearHints(){
  hintL.style.opacity=0;hintD.style.opacity=0;
  wL.style.opacity=0;wD.style.opacity=0;
}

function snapBack(){
  card.classList.add('snap-back');
  card.style.transform='';card.style.opacity='';
  clearHints();
  setTimeout(function(){card.classList.remove('snap-back');},320);
}

function flyOut(toRight,action){
  card.classList.remove('snap-back');
  card.classList.add('fly-out');
  var w=window.innerWidth||400;
  card.style.transform=
    'translateX('+(toRight?w:-w)+'px)'
    +' rotate('+(toRight?25:-25)+'deg)';
  card.style.opacity='0';
  setTimeout(function(){
    card.classList.remove('fly-out');
    card.style.transform='';
    card.style.opacity='';
    clearHints();
    act(action);
  },300);
}

/* Mouse drag */
main.addEventListener('mousedown',function(e){
  if(e.button!==0)return;
  startX=e.clientX;startY=e.clientY;
  dragging=true;
  main.classList.add('dragging');
  card.classList.remove('snap-back','fly-out');
});
window.addEventListener('mousemove',function(e){
  if(!dragging)return;
  applyDrag(e.clientX-startX);
});
window.addEventListener('mouseup',function(e){
  if(!dragging)return;
  dragging=false;
  main.classList.remove('dragging');
  var dx=e.clientX-startX;
  var dy=e.clientY-startY;
  if(Math.abs(dx)>=THRESHOLD&&Math.abs(dx)>Math.abs(dy)){
    flyOut(dx>0,dx>0?'like':'dislike');
  }else{
    snapBack();
  }
});

/* Touch drag */
var tx=0,ty=0,touching=false;
document.addEventListener('touchstart',function(e){
  tx=e.touches[0].clientX;
  ty=e.touches[0].clientY;
  touching=true;
  card.classList.remove('snap-back','fly-out');
},{passive:true});
document.addEventListener('touchmove',function(e){
  if(!touching)return;
  var dx=e.touches[0].clientX-tx;
  var dy=e.touches[0].clientY-ty;
  if(Math.abs(dx)>Math.abs(dy))applyDrag(dx);
},{passive:true});
document.addEventListener('touchend',function(e){
  if(!touching)return;
  touching=false;
  var dx=e.changedTouches[0].clientX-tx;
  var dy=e.changedTouches[0].clientY-ty;
  if(Math.abs(dx)>=THRESHOLD&&Math.abs(dx)>Math.abs(dy)){
    flyOut(dx>0,dx>0?'like':'dislike');
  }else{
    snapBack();
  }
},{passive:true});

/* Keyboard */
document.addEventListener('keydown',function(e){
  var t=e.target.tagName;
  if(t==='INPUT'||t==='TEXTAREA')return;
  if(e.key==='ArrowRight'||e.key==='l')flyOut(true,'like');
  else if(e.key==='ArrowLeft'||e.key==='d')flyOut(false,'dislike');
  else if(e.key==='p')act('previous');
  else if(e.key==='q')act('quit');
});

function esc(s){
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;');
}

function setStatus(m){
  document.getElementById('status').textContent=m;
}

function showFallback(){
  document.getElementById('iframe-wrap').style.display='none';
  document.getElementById('fallback').classList.add('show');
}

function render(a){
  var iw=document.getElementById('iframe-wrap');
  var fb=document.getElementById('fallback');
  var na=document.getElementById('no-art');
  var frm=document.getElementById('frm');
  var ttl=document.getElementById('art-title');
  var meta=document.getElementById('art-meta');
  var prev=document.getElementById('content-preview');
  var lnk=document.getElementById('open-link');

  if(!a){
    na.classList.add('show');
    iw.style.display='none';
    fb.classList.remove('show');
    ttl.textContent='All caught up!';
    meta.innerHTML='';
    setStatus('No more articles.');
    return;
  }

  na.classList.remove('show');
  iw.style.display='';
  fb.classList.remove('show');

  ttl.textContent=a.title||'(no title)';
  var parts=[];
  if(a.author)parts.push(esc(a.author));
  if(a.published_date)parts.push(esc(a.published_date));
  if(a.feedpath&&a.feedpath.length)
    parts.push(esc(a.feedpath.join(' \u2192 ')));
  if(a.tags&&a.tags.length)
    parts.push('Tags: '+esc(a.tags.join(', ')));
  meta.innerHTML=parts.map(
    function(p){return '<span>'+p+'</span>';}
  ).join('');

  prev.textContent=a.content_preview||'';
  if(lnk)lnk.href=a.link||'#';

  frm.onload=null;
  frm.onerror=null;
  frm.src='about:blank';
  if(a.link){
    frm.onload=function(){
      if(frm.src==='about:blank')return;
      try{
        var d=frm.contentDocument;
        if(d&&d.body&&d.body.innerHTML.trim()===''){
          showFallback();
        }
      }catch(ignore){
        /* Cross-origin: iframe may be showing content normally */
      }
    };
    frm.onerror=showFallback;
    setTimeout(function(){frm.src=a.link;},50);
  }else{
    showFallback();
  }
  setStatus('');
}

function act(action){
  if(action==='quit'){
    setStatus('Quitting\u2026');
    fetch('/api/quit',{method:'POST'})['catch'](function(){});
    document.body.innerHTML=
      '<div style="display:flex;align-items:center;'+
      'justify-content:center;height:100vh;'+
      'font-family:system-ui;font-size:1.2em;color:#666">'+
      'FoF closed. You can close this tab.</div>';
    return;
  }
  var labels={
    'like':'Loading next\u2026',
    'dislike':'Loading next\u2026',
    'previous':'Loading previous\u2026'
  };
  setStatus(labels[action]||'');
  fetch('/api/'+action,{method:'POST'})
    .then(function(r){return r.json();})
    .then(render)
    ['catch'](function(e){setStatus('Error: '+e.message);});
}

fetch('/api/article')
  .then(function(r){return r.json();})
  .then(render)
  ['catch'](function(e){
    setStatus('Failed to load: '+e.message);
  });
</script>
</body>
</html>"""


class WebUI:
    """
    Locally-hosted web UI for FoF.

    Architecture:
    - Starts an HTTPServer in a background thread on localhost
      at a random port.
    - Serves a single-page HTML/JS/CSS app for article browsing.
    - API: GET /api/article, POST /api/like, POST /api/dislike,
      POST /api/previous, POST /api/quit.
    - Main thread blocks on a shutdown event (set by /api/quit
      or session timeout).
    - Thread-safe article state via threading.Lock.
    """

    def __init__(
        self, feed_manager, article_manager, session_timeout=300
    ):
        self.feed_manager = feed_manager
        self.article_manager = article_manager
        self.current_article = None
        self.browsing_read_history = False
        self.session_timeout = session_timeout
        self.last_activity_time = time.time()
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()

    def start(self):
        """Start server, open browser, block until shutdown."""
        port = self._find_free_port()
        handler = self._make_handler()
        server = HTTPServer(("localhost", port), handler)

        # Load the first article before starting the server
        self.current_article = self.feed_manager.next_article()
        if self.current_article:
            self.article_manager.mark_as_read(
                self.current_article.id
            )

        server_thread = threading.Thread(
            target=server.serve_forever, daemon=True
        )
        server_thread.start()

        url = f"http://localhost:{port}"
        print(f"FoF web UI: {url}")
        open_url_in_browser(url)

        try:
            while not self._shutdown_event.is_set():
                elapsed = time.time() - self.last_activity_time
                if (self.session_timeout > 0
                        and elapsed >= self.session_timeout):
                    print("Session timed out. Shutting down...")
                    self._shutdown()
                    break
                self._shutdown_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            print("\nInterrupted. Shutting down...")
            self._shutdown()
        finally:
            server.shutdown()

    def _find_free_port(self):
        """Bind to port 0 and return the assigned port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            return s.getsockname()[1]

    def _make_handler(self):
        """Return a BaseHTTPRequestHandler subclass."""
        web_ui = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default request logging

            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    self._serve_html()
                elif self.path == "/api/article":
                    self._serve_article()
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == "/api/like":
                    self._handle_like()
                elif self.path == "/api/dislike":
                    self._handle_dislike()
                elif self.path == "/api/previous":
                    self._handle_previous()
                elif self.path == "/api/quit":
                    self._handle_quit()
                else:
                    self.send_error(404)

            def _serve_html(self):
                content = HTML_TEMPLATE.encode("utf-8")
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
                )
                self.send_header(
                    "Content-Length", str(len(content))
                )
                self.end_headers()
                self.wfile.write(content)

            def _serve_article(self):
                web_ui._update_activity()
                with web_ui._lock:
                    data = web_ui._get_article_json(
                        web_ui.current_article
                    )
                self._send_json(data)

            def _handle_like(self):
                web_ui._update_activity()
                with web_ui._lock:
                    web_ui._advance_to_next()
                    data = web_ui._get_article_json(
                        web_ui.current_article
                    )
                self._send_json(data)

            def _handle_dislike(self):
                web_ui._update_activity()
                with web_ui._lock:
                    web_ui._advance_to_next()
                    data = web_ui._get_article_json(
                        web_ui.current_article
                    )
                self._send_json(data)

            def _handle_previous(self):
                web_ui._update_activity()
                with web_ui._lock:
                    current = web_ui.current_article
                    prev_article = None
                    if current and getattr(current, "read", None):
                        prev_article = (
                            web_ui.article_manager
                            .get_previous_read_article(
                                current.read.isoformat()
                            )
                        )
                    else:
                        most_recent = (
                            web_ui.article_manager
                            .get_previous_read_article()
                        )
                        if (most_recent and current
                                and most_recent.id == current.id):
                            prev_article = (
                                web_ui.article_manager
                                .get_previous_read_article(
                                    most_recent.read.isoformat()
                                )
                            )
                        else:
                            prev_article = most_recent
                    if prev_article:
                        web_ui.current_article = prev_article
                        web_ui.browsing_read_history = True
                    data = web_ui._get_article_json(
                        web_ui.current_article
                    )
                self._send_json(data)

            def _handle_quit(self):
                self._send_json({"status": "ok"})
                web_ui._shutdown()

            def _send_json(self, data):
                content = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header(
                    "Content-Type", "application/json"
                )
                self.send_header(
                    "Content-Length", str(len(content))
                )
                self.end_headers()
                self.wfile.write(content)

        return _Handler

    def _get_article_json(self, article):
        """Serialise an Article to a JSON-safe dict."""
        if article is None:
            return None

        tags = []
        if hasattr(article, "tags") and article.tags:
            tags = list(article.tags)

        feedpath = []
        if article.feedpath:
            feedpath = list(article.feedpath)

        content = article.content or ""
        preview = (
            content[:500] + "..."
            if len(content) > 500
            else content
        )

        pub_date = article.published_date
        if hasattr(pub_date, "isoformat"):
            pub_date = pub_date.isoformat()
        else:
            pub_date = str(pub_date or "")

        return {
            "title": article.title or "",
            "link": article.link or "",
            "author": article.author or "",
            "published_date": pub_date,
            "feedpath": feedpath,
            "content_preview": preview,
            "tags": tags,
        }

    def _advance_to_next(self, mark_read=True):
        """Advance to next unread article (call with lock held).

        Args:
            mark_read: If True (default), mark the new article as read.
                       Retained for potential future callers that need to
                       advance without marking as read.
        """
        self.browsing_read_history = False
        self.current_article = self.feed_manager.next_article()
        if self.current_article and mark_read:
            self.article_manager.mark_as_read(
                self.current_article.id
            )

    def _update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity_time = time.time()

    def _shutdown(self):
        """Signal shutdown, purge old articles, save config."""
        if not self._shutdown_event.is_set():
            self.feed_manager.purge_old_articles()
            self.feed_manager.save_config()
            self._shutdown_event.set()
