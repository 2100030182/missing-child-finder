from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from deepface import DeepFace
import os, sqlite3, cv2, hashlib
from uuid import uuid4

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
MISSING_DIR = os.path.join(IMAGE_DIR, "missing")
FOUND_DIR = os.path.join(IMAGE_DIR, "found")
DB_PATH = os.path.join(BASE_DIR, "database.db")

os.makedirs(MISSING_DIR, exist_ok=True)
os.makedirs(FOUND_DIR, exist_ok=True)

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect(DB_PATH)

def image_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

with get_db() as con:
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS missing_children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT,
            image_hash TEXT,
            guardian_name TEXT,
            guardian_phone TEXT,
            guardian_email TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS found_children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT,
            finder_name TEXT,
            finder_phone TEXT,
            finder_email TEXT,
            found_location TEXT,
            collect_location TEXT
        )
    """)

# ---------- STATIC FILES ----------
@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/upload_missing.html")
def upload_missing_page():
    return send_from_directory(FRONTEND_DIR, "upload_missing.html")

@app.route("/upload_found.html")
def upload_found_page():
    return send_from_directory(FRONTEND_DIR, "upload_found.html")

@app.route("/style.css")
def style_css():
    return send_from_directory(FRONTEND_DIR, "style.css")

@app.route("/script.js")
def script_js():
    return send_from_directory(FRONTEND_DIR, "script.js")

@app.route("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(IMAGE_DIR, filename)

# ---------- UPLOAD MISSING ----------
@app.route("/upload-missing", methods=["POST"])
def upload_missing():
    img = request.files["image"]
    name = request.form["name"]
    phone = request.form["phone"]
    email = request.form["email"]

    fname = f"{uuid4().hex}.jpg"
    path = os.path.join(MISSING_DIR, fname)
    img.save(path)

    rel = f"missing/{fname}"
    h = image_hash(path)

    with get_db() as con:
        if con.execute("SELECT id FROM missing_children WHERE image_hash=?", (h,)).fetchone():
            return jsonify({"message": "Already reported"})

        con.execute(
            "INSERT INTO missing_children VALUES (NULL,?,?,?,?,?)",
            (rel, h, name, phone, email)
        )

    return jsonify({"message": "Missing child added"})

# ---------- UPLOAD FOUND ----------
@app.route("/upload-found", methods=["POST"])
def upload_found():
    img = request.files["image"]
    name = request.form["name"]
    phone = request.form["phone"]
    email = request.form["email"]
    found = request.form["found_location"]
    collect = request.form["collect_location"]

    fname = f"{uuid4().hex}.jpg"
    path = os.path.join(FOUND_DIR, fname)
    img.save(path)

    rel = f"found/{fname}"

    with get_db() as con:
        con.execute(
            "INSERT INTO found_children VALUES (NULL,?,?,?,?,?,?)",
            (rel, name, phone, email, found, collect)
        )

    return jsonify({"message": "Found child added"})

# ---------- LIST MISSING ----------
@app.route("/missing-children")
def missing_children():
    with get_db() as con:
        rows = con.execute(
            "SELECT image_path, guardian_name, guardian_phone, guardian_email FROM missing_children"
        ).fetchall()

    return jsonify([
        {
            "image": f"/images/{r[0]}",
            "name": r[1],
            "phone": r[2],
            "email": r[3]
        } for r in rows
    ])

# ---------- COMPARE ----------
@app.route("/compare", methods=["POST"])
def compare():
    file = request.files["image"]
    temp = os.path.join(MISSING_DIR, "temp.jpg")
    file.save(temp)

    img1 = cv2.imread(temp)
    if img1 is None:
        return jsonify({"error": "Invalid image"}), 400

    h = image_hash(temp)
    matches = []

    with get_db() as con:
        found = con.execute("SELECT * FROM found_children").fetchall()
        missing = con.execute("SELECT id FROM missing_children WHERE image_hash=?", (h,)).fetchone()

    for r in found:
        try:
            img2 = cv2.imread(os.path.join(IMAGE_DIR, r[1]))
            if img2 is None:
                continue

            if DeepFace.verify(img1, img2, model_name="VGG-Face", detector_backend="opencv")["verified"]:
                matches.append({
                    "finder_name": r[2],
                    "phone": r[3],
                    "email": r[4],
                    "found_location": r[5],
                    "collect_location": r[6]
                })
        except:
            pass

    return jsonify({
        "match": bool(matches),
        "results": matches,
        "already_reported": bool(missing)
    })

# ---------- OPTION 1: CLEAR ALL (ALWAYS ENABLED) ----------
@app.route("/reset-all", methods=["POST"])
def reset_all():
    for folder in [MISSING_DIR, FOUND_DIR]:
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))

    with get_db() as con:
        con.execute("DELETE FROM missing_children")
        con.execute("DELETE FROM found_children")

    return jsonify({"message": "ALL DATA CLEARED"})

# ---------- OPTION 2: CLEAR MATCHED (ONLY AFTER MATCH) ----------
@app.route("/clear-matched", methods=["POST"])
def clear_matched():
    for folder in [MISSING_DIR, FOUND_DIR]:
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))

    with get_db() as con:
        con.execute("DELETE FROM missing_children")
        con.execute("DELETE FROM found_children")

    return jsonify({"message": "MATCHED DATA CLEARED"})

if __name__ == "__main__":
    app.run(debug=True)
