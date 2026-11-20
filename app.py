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

    # 1. Link eka already m3u8 nam, eka kelinma denawa
    # Limit na, ena widiyatama denawa
    if ".m3u8" in url:
        return jsonify({"m3u8": url})

    # 2. Nathnam yt-dlp walin m3u8 hoyanawa
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)

            # Playlist ekak nam palaweni eka
            if 'entries' in info and info['entries']:
                info = info['entries'][0]

            formats = info.get('formats', [])
            m3u8_list = []

            # Thiyena okkoma m3u8 tika ekathu karanawa
            for f in formats:
                f_url = f.get('url', '')
                protocol = f.get('protocol', '')
                if protocol in ('m3u8_native', 'm3u8') or '.m3u8' in f_url:
                    m3u8_list.append(f)

            # M3U8 ekak thibboth, hodama eka (quality wedi eka) denawa
            # 480p / 720p kiyala limit ekak NA
            # Ena widiyatama, hodama quality eka denawa
            if m3u8_list:
                # height / tbr anuwa sort karala hodama eka gannawa
                # Limit karanne na, thiyena hodama eka witharai gannawa
                m3u8_list.sort(key=lambda x: (x.get('height') or 0, x.get('tbr') or 0), reverse=True)
                best_m3u8 = m3u8_list[0]['url']
                return jsonify({"m3u8": best_m3u8, "title": info.get('title')})

            # M3U8 ekakma nathnam, yt-dlp denna best link eka denawa
            return jsonify({"m3u8": info.get('url'), "title": info.get('title')})

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
