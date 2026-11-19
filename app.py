from flask import Flask, request, jsonify, send_file
import yt_dlp
import os

app = Flask(__name__)
os.makedirs("downloads", exist_ok=True)

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/get_m3u8", methods=["POST"])
def get_m3u8():
    url = request.json.get("url")
    # link eka m3u8 nam eka kelinma denawa
    if ".m3u8" in url:
        return jsonify({"m3u8": url})
    # nathnam yt-dlp walin m3u8 hoyanawa
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            # best m3u8 eka hoyanawa
            m3u8 = info.get('url')
            if info.get('formats'):
                for f in info['formats']:
                    if f.get('protocol') == 'm3u8_native' or '.m3u8' in str(f.get('url','')):
                        m3u8 = f['url']
                        break
            return jsonify({"m3u8": m3u8, "title": info.get('title')})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    try:
        with yt_dlp.YoutubeDL({'outtmpl': 'downloads/video.mp4', 'format': 'best'}) as ydl:
            ydl.download([url])
        return send_file("downloads/video.mp4", as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
