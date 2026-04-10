from flask import Flask, render_template, request, redirect, session
#from flask_socketio import SocketIO, send
import os
import cloudinary
import cloudinary.uploader
import psycopg2
from dotenv import load_dotenv

# ---------- LOAD ENV ----------
load_dotenv()

# ---------- ENV CONFIG ----------
ENV = os.getenv("ENV", "local")
DATABASE_URL = os.getenv("DATABASE_URL")

print("ENV:", ENV)
print("Using DB:", DATABASE_URL)

# ---------- CLOUDINARY CONFIG (ONLY PROD) ----------
if ENV == "production":
    cloudinary.config(
        cloud_name=os.getenv("CLOUD_NAME"),
        api_key=os.getenv("API_KEY"),
        api_secret=os.getenv("API_SECRET")
    )

# ---------- DB CONNECTION ----------
def get_connection():
    try:
        if ENV == "production":
            return psycopg2.connect(DATABASE_URL, sslmode='require')
        else:
            return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print("DB Connection Error:", e)
        raise

# ---------- APP ----------
app = Flask(__name__)
app.secret_key = "campus_exchange_secret"
# socketio = SocketIO(app)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ACCESS_CODE = "admin123"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------- DATABASE ----------
def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            title TEXT,
            category TEXT,
            price TEXT,
            description TEXT,
            image TEXT,
            status TEXT DEFAULT 'available'
        )
    """)

    conn.commit()
    conn.close()

# Run once
if ENV == "local":
    init_db()

# ---------- HOME ----------
@app.route("/")
def home():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM items")
    items = c.fetchall()

    conn.close()
    return render_template("index.html", items=items)

# ---------- UPLOAD ----------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        try:
            title = request.form.get("title")
            price = request.form.get("price")
            description = request.form.get("description")
            category = "furniture"

            files = request.files.getlist("images")
            image_names = []

            for file in files:
                if file and file.filename != "":
                    if ENV == "local":
                        # ✅ Save locally
                        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                        file.save(filepath)
                        image_names.append("/" + filepath)
                    else:
                        # ✅ Upload to Cloudinary (production)
                        upload_result = cloudinary.uploader.upload(file)
                        image_url = upload_result.get("secure_url")
                        image_names.append(image_url)

            images_string = ",".join(image_names)

            conn = get_connection()
            c = conn.cursor()

            c.execute(
                "INSERT INTO items (title, category, price, description, image) VALUES (%s,%s,%s,%s,%s)",
                (title, category, price, description, images_string)
            )

            conn.commit()
            conn.close()

            return redirect("/")

        except Exception as e:
            print("UPLOAD ERROR:", e)
            return f"Upload Failed: {e}"

    return render_template("upload.html")

# ---------- DELETE ----------
@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    if not session.get("admin"):
        return redirect("/login")

    conn = get_connection()
    c = conn.cursor()

    c.execute("DELETE FROM items WHERE id=%s", (item_id,))
    conn.commit()
    conn.close()

    return redirect("/manage")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("code") == ACCESS_CODE:
            session["admin"] = True
            return redirect("/manage")
        return "Wrong Access Code"

    return render_template("login.html")

# ---------- MANAGE ----------
@app.route("/manage")
def manage():
    if not session.get("admin"):
        return redirect("/login")

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM items")
    items = c.fetchall()

    conn.close()
    return render_template("manage.html", items=items)

# ---------- CHAT ----------
#@app.route("/chat")
#def chat():
#    return render_template("chat.html")
#
#@socketio.on("message")
#def handle_message(msg):
#   send(msg, broadcast=True)

# ---------- RUN ----------
#if __name__ == "__main__":
#    socketio.run(app, debug=(ENV == "local"))