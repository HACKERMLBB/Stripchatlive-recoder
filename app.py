from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import subprocess
import sys

app = Flask(__name__)
os.makedirs("downloads", exist_ok=True)

# Fix for yt-dlp old version error - Auto Update on startup
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], check=False, timeout=60)
    print("yt-dlp updated!")
except:
    pass

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/get_m3u8", methods=["POST"])
def get_m3u8():
    url = request.json.get("url")

    # If already m3u8, return directly
    if ".m3u8" in url:
        return jsonify({"m3u8": url})

    # Find m3u8 via yt-dlp
    try:
        # Same as your code, but with YouTube fix added
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'noplaylist': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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

            # Get best quality m3u8 - No limit
            if m3u8_list:
                m3u8_list.sort(key=lambda x: (x.get('height') or 0, x.get('tbr') or 0), reverse=True)
                best_m3u8 = m3u8_list[0]['url']
                return jsonify({"m3u8": best_m3u8, "title": info.get('title')})

            return jsonify({"m3u8": info.get('url'), "title": info.get('title')})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    try:
        # Remove old file - So new download works
        if os.path.exists("downloads/video.mp4"):
            os.remove("downloads/video.mp4")
        # Same as your code, but with YouTube fix
        ydl_opts = {
            'outtmpl': 'downloads/video.mp4',
            'format': 'best',
            'quiet': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file("downloads/video.mp4", as_attachment=True, download_name="StreamX-Video.mp4")
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
