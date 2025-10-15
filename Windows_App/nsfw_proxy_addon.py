# nsfw_proxy_addon.py
from mitmproxy import http, ctx
import base64, requests, re, json
from urllib.parse import urljoin
API_ANALYZE = "http://127.0.0.1:5000/analyze"
API_LOCK = "http://127.0.0.1:5000/lock"
NSFW_CLASSES_TRIGGER = None  # let detector config pick classes

def extract_img_data_from_html(html, base):
    # find <img src="..."> and data: URIs
    imgs = []
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I):
        src = m.group(1)
        if src.startswith("data:"):
            imgs.append(src)
        else:
            imgs.append(urljoin(base, src))
    return imgs

def analyze_image_url(url):
    try:
        r = requests.get(url, timeout=8)
        if r.status_code==200 and 'image' in r.headers.get('Content-Type',''):
            b64 = "data:image/jpeg;base64," + base64.b64encode(r.content).decode()
            res = requests.post(API_ANALYZE, json={"image_base64": b64}, timeout=10).json()
            return res
    except Exception as e:
        ctx.log.warn(f"img fetch err {e}")
    return {"nsfw": False}

def analyze_data_uri(data_uri):
    try:
        res = requests.post(API_ANALYZE, json={"image_base64": data_uri}, timeout=10).json()
        return res
    except Exception as e:
        ctx.log.warn(f"datauri err {e}")
    return {"nsfw": False}

def trigger_lock():
    try:
        requests.post(API_LOCK, json={"hours": 1}, timeout=5)
    except Exception as e:
        ctx.log.warn(f"failed lock call {e}")

class NSFWFilter:
    def response(self, flow: http.HTTPFlow):
        # only inspect text/html pages
        if flow.response and "text/html" in flow.response.headers.get("Content-Type",""):
            content = flow.response.get_text()
            imgs = extract_img_data_from_html(content, flow.request.pretty_url)
            # check visible text quickly
            text = re.sub(r'<[^>]+>', ' ', content)
            if any(w in text.lower() for w in ["porn","xxx","nude","hentai","erotic","sex"]):
                trigger_lock(); self.block_flow(flow); return
            # analyze images
            for src in imgs[:100]:  # limit to first 100 images
                if src.startswith("data:"):
                    res = analyze_data_uri(src)
                else:
                    res = analyze_image_url(src)
                if res.get("nsfw"):
                    trigger_lock()
                    self.block_flow(flow)
                    return

    def block_flow(self, flow):
        # replace response with local blocked page
        block_html = "<html><body style='background:#111;color:#fff;font-family:Arial;text-align:center;padding-top:20vh;'><h1>Blocked</h1><p>NSFW content detected — locked for 1 hour.</p></body></html>"
        flow.response = http.HTTPResponse.make(200, block_html, {"Content-Type":"text/html"})

addons = [NSFWFilter()]
