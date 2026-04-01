from flask import Flask, request, render_template, send_file, jsonify, session, redirect, url_for
from pytubefix import YouTube
import tempfile
import os
import uuid
import time
import threading

app = Flask(__name__)
app.secret_key = "supersecretkey123"   # 🔐 change this

# 👥 USERS
USERS = {
    "himanshu": "7323996467",
    "admin": "7323996467"
}

progress_data = {}

# 🔐 LOGIN PAGE
@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS and USERS[username] == password:
            session["user"] = username
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# 🏠 HOME (Protected)
@app.route('/home')
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


# 🎬 Fetch video info (Protected)
@app.route('/get_info', methods=['POST'])
def get_info():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"})

    url = request.json.get('url')

    try:
        yt = YouTube(url)
        streams = yt.streams.filter(file_extension='mp4')

        best = {}
        for s in streams:
            if s.resolution and s.filesize:
                res = s.resolution
                if res not in best or s.filesize > best[res].filesize:
                    best[res] = s

        qualities = []
        for q in ["360p", "480p", "720p", "1080p"]:
            if q in best:
                size = round(best[q].filesize / (1024*1024), 2)
                qualities.append({
                    "quality": q,
                    "size": f"{size} MB"
                })

        if not qualities:
            fallback = yt.streams.filter(progressive=True).first()
            if fallback:
                size = round(fallback.filesize / (1024*1024), 2)
                qualities.append({
                    "quality": fallback.resolution,
                    "size": f"{size} MB"
                })

        return jsonify({
            "title": yt.title,
            "thumbnail": yt.thumbnail_url,
            "qualities": qualities
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ⬇ Download (Protected)
@app.route('/download', methods=['POST'])
def download():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"})

    try:
        url = request.form.get('url')
        quality = request.form.get('quality')

        yt = YouTube(url)
        unique_id = str(uuid.uuid4())
        temp_dir = tempfile.gettempdir()

        progress_data[unique_id] = {
            "downloaded": 0,
            "total": 0,
            "start_time": time.time(),
            "done": False
        }

        if quality in ["480p", "720p"]:
            stream = yt.streams.filter(progressive=True, file_extension='mp4', res=quality).first()

            if not stream:
                stream = yt.streams.filter(progressive=True, file_extension='mp4')\
                                   .order_by('resolution')\
                                   .desc()\
                                   .first()

            total_size = stream.filesize
            progress_data[unique_id]["total"] = total_size

            def progress_callback(stream, chunk, bytes_remaining):
                downloaded = total_size - bytes_remaining
                progress_data[unique_id]["downloaded"] = downloaded

            yt.register_on_progress_callback(progress_callback)

            file_path = stream.download(output_path=temp_dir, filename=f"{unique_id}.mp4")

            progress_data[unique_id]["done"] = True
            progress_data[unique_id]["file"] = file_path

        elif quality == "1080p":
            video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', res="1080p").first()
            audio_stream = yt.streams.filter(only_audio=True).first()

            if not video_stream or not audio_stream:
                return jsonify({"error": "1080p not available"})

            video_size = video_stream.filesize or 0
            audio_size = audio_stream.filesize or 0
            total_size = video_size + audio_size

            progress_data[unique_id]["total"] = total_size

            video_path = os.path.join(temp_dir, f"video_{unique_id}.mp4")
            audio_path = os.path.join(temp_dir, f"audio_{unique_id}.mp4")

            def download_video():
                video_stream.download(output_path=temp_dir, filename=f"video_{unique_id}.mp4")
                progress_data[unique_id]["downloaded"] += video_size

            def download_audio():
                audio_stream.download(output_path=temp_dir, filename=f"audio_{unique_id}.mp4")
                progress_data[unique_id]["downloaded"] += audio_size

            t1 = threading.Thread(target=download_video)
            t2 = threading.Thread(target=download_audio)

            t1.start()
            t2.start()
            t1.join()
            t2.join()

            output_path = os.path.join(temp_dir, f"final_{unique_id}.mp4")

            os.system(f'ffmpeg -y -i "{video_path}" -i "{audio_path}" -c:v copy -c:a copy "{output_path}"')

            progress_data[unique_id]["done"] = True
            progress_data[unique_id]["file"] = output_path

        return jsonify({"id": unique_id})

    except Exception as e:
        return jsonify({"error": str(e)})


# 📊 Progress (Protected)
@app.route('/progress/<id>')
def progress(id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"})

    data = progress_data.get(id)

    if not data:
        return jsonify({})

    downloaded = data["downloaded"]
    total = data["total"]
    elapsed = time.time() - data["start_time"]

    speed = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0
    remaining = (total - downloaded) / 1024 / 1024 / speed if speed > 0 else 0

    return jsonify({
        "downloaded": downloaded,
        "total": total,
        "speed": round(speed, 2),
        "eta": round(remaining, 2),
        "done": data["done"]
    })


# 📥 File download (Protected)
@app.route('/get_file/<id>')
def get_file(id):
    if "user" not in session:
        return redirect("/")

    data = progress_data.get(id)

    if data and data.get("done"):
        return send_file(data["file"], as_attachment=True)

    return "File not ready"


# 🚪 Logout
@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)