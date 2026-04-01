from flask import Flask, request, render_template, send_file, jsonify, session, redirect, url_for
import yt_dlp
import tempfile
import os
import uuid
import threading

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# 👥 USERS
USERS = {
    "himanshu": "7323996467",
    "admin": "7323996467"
}

progress_data = {}

# 🔐 LOGIN
@app.route("/", methods=["GET", "POST"])
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


# 🏠 HOME
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    return render_template("index.html")


# 🎬 GET VIDEO INFO
@app.route('/get_info', methods=['POST'])
def get_info():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"})

    url = request.json.get('url')

    try:
       ydl_opts = {
    'format': f'bestvideo[height<={height}]+bestaudio/best',
    'outtmpl': output_path,
    'merge_output_format': 'mp4',
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'cookiefile': 'cookies.txt',
    'progress_hooks': [progress_hook]
}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get('formats', [])

        qualities = []
        added = set()

        for f in formats:
            if f.get('height') in [360, 480, 720, 1080]:
                q = f"{f.get('height')}p"
                if q not in added and f.get('filesize'):
                    size = round(f.get('filesize') / (1024*1024), 2)
                    qualities.append({
                        "quality": q,
                        "size": f"{size} MB"
                    })
                    added.add(q)

        return jsonify({
            "title": info.get('title'),
            "thumbnail": info.get('thumbnail'),
            "qualities": qualities
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ⬇ DOWNLOAD
@app.route('/download', methods=['POST'])
def download():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"})

    try:
        url = request.form.get('url')
        quality = request.form.get('quality')

        unique_id = str(uuid.uuid4())
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"{unique_id}.mp4")

        height = quality.replace("p", "")

        progress_data[unique_id] = {
            "progress": "0%",
            "done": False
        }

        def progress_hook(d):
            if d['status'] == 'downloading':
                progress_data[unique_id]["progress"] = d.get('_percent_str', "0%")
            elif d['status'] == 'finished':
                progress_data[unique_id]["progress"] = "100%"

        ydl_opts = {
            'format': f'bestvideo[height={height}]+bestaudio/best',
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'cookiefile': 'cookies.txt',   # 🔐 IMPORTANT
            'progress_hooks': [progress_hook]
        }

        def run():
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    progress_data[unique_id]["file"] = output_path
    progress_data[unique_id]["done"] = True

        threading.Thread(target=run).start()

        return jsonify({"id": unique_id})

    except Exception as e:
        return jsonify({"error": str(e)})


# 📊 PROGRESS
@app.route('/progress/<id>')
def progress(id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"})

    data = progress_data.get(id)

    if not data:
        return jsonify({})

    return jsonify({
        "progress": data.get("progress"),
        "done": data.get("done")
    })


# 📥 GET FILE
@app.route('/get_file/<id>')
def get_file(id):
    if "user" not in session:
        return redirect("/")

    data = progress_data.get(id)

    if data and data.get("done"):
        return send_file(data["file"], as_attachment=True)

    return "File not ready"


# 🚪 LOGOUT
@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
