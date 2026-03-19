from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, send
import sqlite3
import os
import cloudinary
import cloudinary.uploader


app = Flask(__name__)
app.secret_key = "campus_exchange_secret"
socketio = SocketIO(app)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

cloudinary.config(
    cloud_name="dz830khhh",
    api_key="331372578728144",
    api_secret="C8NABLICiVuqfqVCrDobU7leAK4"
)

ACCESS_CODE = "admin123"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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


# ---------- status ----------
def add_status_column():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    try:
        c.execute("ALTER TABLE items ADD COLUMN status TEXT DEFAULT 'available'")
    except:
        pass

    conn.commit()
    conn.close()

add_status_column()

# ---------- HOME ----------
@app.route("/")
def home():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM items")
    items = c.fetchall()

    conn.close()

    return render_template("index.html", items=items)


# ---------- UPLOAD ----------
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":

        title = request.form["title"]
        price = request.form["price"]
        description = request.form["description"]

        # category optional
        category = "furniture"

        files = request.files.getlist("images")

        image_names = []

        for file in files:

            if file.filename != "":

                filename = file.filename

              # filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

              # file.save(filepath)

              # image_names.append(filename)

            upload_result = cloudinary.uploader.upload(file)
            image_url = upload_result["secure_url"]

            image_names.append(image_url)

        images_string = ",".join(image_names)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute(
            "INSERT INTO items (title, category, price, description, image) VALUES (?,?,?,?,?)",
            (title, category, price, description, images_string)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("upload.html")


# ---------- DELETE ----------
@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()

    conn.close()

    return redirect("/manage")



# ---------- Sold / Available----------

@app.route("/mark_sold/<int:item_id>")
def mark_sold(item_id):

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("UPDATE items SET status=? WHERE id=?", ("sold", item_id))

    conn.commit()
    conn.close()

    return redirect("/manage")



@app.route("/mark_available/<int:item_id>")
def mark_available(item_id):

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("UPDATE items SET status=? WHERE id=?", ("available", item_id))

    conn.commit()
    conn.close()

    return redirect("/manage")


# ---------- LOGIN ACESS----------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        code = request.form["code"]

        if code == ACCESS_CODE:
            session["admin"] = True
            return redirect("/manage")

        else:
            return "Wrong Access Code"

    return render_template("login.html")

# ---------- MANAGE PAGE ----------
@app.route("/manage")
def manage():

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM items")
    items = c.fetchall()

    conn.close()



    return render_template("manage.html", items=items)

# ---------- LOGOUT ROUTE ----------
@app.route("/logout")
def logout():

    session.pop("admin", None)

    return redirect("/")

# ---------- CHAT ----------
@app.route("/chat")
def chat():
    return render_template("chat.html")


@socketio.on("message")
def handle_message(msg):
    send(msg, broadcast=True)


# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
