from flask import Flask, request, jsonify, send_file
import yt_dlp
import os

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
