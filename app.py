from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import os
import re
import urllib.request
import urllib.parse

app = Flask(__name__)

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/play", methods=["POST"])
def play():
    url = request.json.get("url")
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            qualities = []
            seen = set()
            for f in info.get('formats', []):
                f_url = f.get('url', '')
                height = f.get('height')
                if ('.m3u8' in f_url or f.get('protocol') in ('m3u8', 'm3u8_native')) and height:
                    if height not in seen:
                        seen.add(height)
                        qualities.append({"quality": f"{height}p", "height": height, "m3u8": f_url})
            qualities.sort(key=lambda x: x['height'], reverse=True)
            if not qualities:
                return jsonify({"error": "No m3u8 found! Try another link!"})
            return jsonify({"m3u8": qualities[0]['m3u8'], "title": info.get('title', 'Video'), "qualities": qualities})
    except Exception as e:
        return jsonify({"error": str(e)})

# Proxy - NO requests library! Using urllib only!
@app.route("/proxy")
def proxy():
    m3u8_url = request.args.get("url")
    if not m3u8_url:
        return "No URL", 400
    try:
        req = urllib.request.Request(m3u8_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read()
            content_type = r.headers.get('Content-Type', '')

        # .ts File - Send As Is
        if '.ts' in m3u8_url or 'video' in content_type or 'octet' in content_type:
            return Response(content, content_type=content_type)

        # m3u8 File - Rewrite .ts URLs To Proxy
        text = content.decode('utf-8', errors='ignore')
        base = m3u8_url.rsplit('/', 1)[0] + '/'
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                if 'URI="' in line:
                    line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="/proxy?url=' + urllib.parse.quote(m.group(1) if m.group(1).startswith('http') else base + m.group(1), safe='') + '"', line)
                lines.append(line)
            else:
                full = line if line.startswith('http') else base + line
                lines.append("/proxy?url=" + urllib.parse.quote(full, safe=''))
        return Response("\n".join(lines), content_type='application/vnd.apple.mpegurl')
    except Exception as e:
        return str(e), 500

@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    quality = request.json.get("quality", "best")
    try:
        if os.path.exists("video.mp4"):
            os.remove("video.mp4")
        fmt = "best" if quality == "best" else f"best[height<={quality}]"
        with yt_dlp.YoutubeDL({'outtmpl': 'video.mp4', 'format': fmt}) as ydl:
            ydl.download([url])
        return send_file("video.mp4", as_attachment=True, download_name=f"video-{quality}p.mp4")
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
