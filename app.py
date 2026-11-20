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
    if not url:
        return jsonify({"error": "No URL!"})

    # Direct m3u8 දුන්නොත් ඒකම දෙනවා
    if ".m3u8" in url:
        return jsonify({
            "m3u8": url,
            "title": "Direct m3u8",
            "formats": [{"quality": "Direct", "height": 0, "m3u8": url, "ext": "m3u8", "filesize": 0, "tbr": 0, "fps": 0, "vcodec": "", "acodec": ""}],
            "qualities": [{"quality": "Direct", "height": 0, "m3u8": url}],
            "direct_mp4": [],
            "all_formats": []
        })

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]

            formats = info.get('formats', [])

            # 1. m3u8 ඔක්කොම
            m3u8_list = []
            # 2. Direct MP4 / WEBM ඔක්කොම
            direct_list = []
            # 3. Audio Only ඔක්කොම
            audio_list = []
            # 4. හැම Format එකම
            all_formats = []

            for f in formats:
                f_url = f.get('url', '') or ''
                protocol = f.get('protocol', '') or ''
                ext = f.get('ext', '') or ''
                height = f.get('height') or 0
                width = f.get('width') or 0
                tbr = f.get('tbr') or 0
                fps = f.get('fps') or 0
                vcodec = f.get('vcodec', '') or ''
                acodec = f.get('acodec', '') or ''
                filesize = f.get('filesize') or f.get('filesize_approx') or 0
                format_id = f.get('format_id', '') or ''
                format_note = f.get('format_note', '') or ''

                item = {
                    "format_id": format_id,
                    "quality": f"{height}p" if height else (format_note or format_id or "Unknown"),
                    "height": height,
                    "width": width,
                    "m3u8": f_url,
                    "url": f_url,
                    "ext": ext,
                    "protocol": protocol,
                    "filesize": filesize,
                    "tbr": tbr,
                    "fps": fps,
                    "vcodec": vcodec,
                    "acodec": acodec,
                    "format_note": format_note
                }
                all_formats.append(item)

                is_m3u8 = protocol in ('m3u8_native', 'm3u8') or '.m3u8' in f_url
                if is_m3u8:
                    m3u8_list.append(item)
                elif vcodec != 'none' and ext in ('mp4', 'webm', 'mkv', 'mov'):
                    direct_list.append(item)
                elif vcodec == 'none' and acodec != 'none':
                    audio_list.append(item)

            # m3u8 හොඳම එක උඩට
            m3u8_list.sort(key=lambda x: (x['height'], x['tbr']), reverse=True)
            direct_list.sort(key=lambda x: (x['height'], x['tbr']), reverse=True)
            audio_list.sort(key=lambda x: x['tbr'], reverse=True)
            all_formats.sort(key=lambda x: (x['height'], x['tbr']), reverse=True)

            # Quality Buttons වලට - Duplicate අයින් කරලා
            qualities = []
            seen = set()
            for f in m3u8_list:
                if f['height'] not in seen and f['height'] > 0:
                    seen.add(f['height'])
                    qualities.append({"quality": f"{f['height']}p", "height": f['height'], "m3u8": f['m3u8']})

            best_m3u8 = m3u8_list[0]['m3u8'] if m3u8_list else (direct_list[0]['url'] if direct_list else info.get('url'))
            best_mp4 = direct_list[0]['url'] if direct_list else ""

            return jsonify({
                "m3u8": best_m3u8,
                "best_mp4": best_mp4,
                "title": info.get('title', 'Video'),
                "uploader": info.get('uploader', ''),
                "uploader_url": info.get('uploader_url', ''),
                "duration": info.get('duration', 0),
                "view_count": info.get('view_count', 0),
                "like_count": info.get('like_count', 0),
                "thumbnail": info.get('thumbnail', ''),
                "description": (info.get('description', '') or '')[:500],
                "webpage_url": info.get('webpage_url', url),
                "is_live": info.get('is_live', False),
                "formats": m3u8_list,
                "qualities": qualities,
                "direct_mp4": direct_list,
                "audio_only": audio_list,
                "all_formats": all_formats,
                "total_formats": len(all_formats)
            })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/proxy")
def proxy():
    m3u8_url = request.args.get("url")
    if not m3u8_url:
        return "No URL", 400
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Referer": "https://stripchat.com/",
        "Origin": "https://stripchat.com",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(m3u8_url, headers=headers, timeout=30, stream=True)
        # .ts / .m4s / .key වගේ කෑලි - Binary විදිහටම
        if ".m3u8" not in m3u8_url:
            return Response(r.iter_content(chunk_size=8192), content_type=r.headers.get('Content-Type', 'video/MP2T'))
        # m3u8 - ඇතුලේ .ts ඔක්කොම Proxy හරහා
        text = r.text
        base = m3u8_url.rsplit('/', 1)[0] + '/'
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                if 'URI="' in line:
                    line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="/proxy?url=' + requests.utils.quote(m.group(1) if m.group(1).startswith('http') else base + m.group(1), safe='') + '"', line)
                lines.append(line)
            else:
                full = line if line.startswith('http') else base + line
                lines.append("/proxy?url=" + requests.utils.quote(full, safe=''))
        return Response("\n".join(lines), content_type="application/vnd.apple.mpegurl")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    quality = request.json.get("quality", "best")
    format_id = request.json.get("format_id", "")
    try:
        if os.path.exists("downloads/video.mp4"):
            os.remove("downloads/video.mp4")
        # Format ID දුන්නොත් ඒක, Quality දුන්නොත් ඒ Height එක, නැත්නම් Best
        if format_id:
            fmt = format_id + "+bestaudio/best"
        elif quality == "best":
            fmt = "best"
        elif quality == "audio":
            fmt = "bestaudio"
        else:
            fmt = f"best[height<={quality}]"
        with yt_dlp.YoutubeDL({'outtmpl': 'downloads/video.mp4', 'format': fmt}) as ydl:
            ydl.download([url])
        return send_file("downloads/video.mp4", as_attachment=True, download_name=f"StreamX-Video.mp4")
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
