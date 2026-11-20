from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import os
import requests
import re

app = Flask(__name__)
os.makedirs("downloads", exist_ok=True)

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/get_m3u8", methods=["POST"])
def get_m3u8():
    url = request.json.get("url")
    if ".m3u8" in url:
        return jsonify({"m3u8": url})
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            formats = info.get('formats', [])
            m3u8_list = []
            for f in formats:
                f_url = f.get('url', '')
                protocol = f.get('protocol', '')
                if protocol in ('m3u8_native', 'm3u8') or '.m3u8' in f_url:
                    m3u8_list.append(f)
            if m3u8_list:
                m3u8_list.sort(key=lambda x: (x.get('height') or 0, x.get('tbr') or 0), reverse=True)
                best_m3u8 = m3u8_list[0]['url']
                return jsonify({"m3u8": best_m3u8, "title": info.get('title')})
            return jsonify({"m3u8": info.get('url'), "title": info.get('title')})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/proxy")
def proxy():
    m3u8_url = request.args.get("url")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://stripchat.com/",
        "Origin": "https://stripchat.com"
    }
    try:
        r = requests.get(m3u8_url, headers=headers, timeout=15)
        text = r.text
        base = m3u8_url.rsplit('/', 1)[0] + '/'
        text = re.sub(r'\n(?!#)([^\n]+)', lambda m: '\n' + (m.group(1) if m.group(1).startswith('http') else base + m.group(1)), text)
        return Response(text, content_type="application/vnd.apple.mpegurl")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    try:
        if os.path.exists("downloads/video.mp4"):
            os.remove("downloads/video.mp4")
        with yt_dlp.YoutubeDL({'outtmpl': 'downloads/video.mp4', 'format': 'best'}) as ydl:
            ydl.download([url])
        return send_file("downloads/video.mp4", as_attachment=True, download_name="StreamX-Video.mp4")
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
