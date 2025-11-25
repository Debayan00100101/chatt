import streamlit as st
import sqlite3
import hashlib
import os
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
import shutil
import time
import base64

st.set_page_config(page_title="Snowflake", page_icon="❄", layout="wide")

# -----------------------
# Paths & DB (PERMANENT STORAGE)
# -----------------------
APP_DIR = os.path.join(os.getcwd(), "snowflake_chat_data")
os.makedirs(APP_DIR, exist_ok=True)

DB_FILE = os.path.join(APP_DIR, "super_chat_delete_alert.db")
MEDIA_DIR = os.path.join(APP_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# -----------------------
# Secret code
# -----------------------
def _secure_secret_hash():
    parts = ["73757065723030313030313031"]
    secret_bytes = bytes.fromhex("".join(parts))
    return hashlib.sha256(secret_bytes).hexdigest()

SECRET_CODE_HASH = _secure_secret_hash()

# -----------------------
# DB Initialization
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            avatar_path TEXT,
            msg_type TEXT,
            content TEXT,
            timestamp REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            avatar_path TEXT,
            last_active REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS system_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            timestamp REAL
        )
    """)
    conn.commit()
    conn.close()

if not os.path.exists(DB_FILE):
    init_db()

# -----------------------
# User functions
# -----------------------
def register_user(username, avatar):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    avatar_path = None
    if avatar:
        avatar_name = f"{username}_avatar.png"
        avatar_path = os.path.join(APP_DIR, avatar_name)
        with open(avatar_path, "wb") as f:
            f.write(avatar)
    now = time.time()
    c.execute("""
        INSERT INTO users (username, avatar_path, last_active)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET avatar_path=excluded.avatar_path, last_active=excluded.last_active
    """, (username, avatar_path, now))
    conn.commit()
    conn.close()
    save_system_message(f"{username} joined the chat")

def update_user_activity(username):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    now = time.time()
    c.execute("UPDATE users SET last_active=? WHERE username=?", (now, username))
    conn.commit()
    conn.close()

def remove_user(username):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

def get_online_users(timeout=15):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    now = time.time()
    c.execute("SELECT username, avatar_path FROM users WHERE last_active>=?", (now - timeout,))
    users = [{"username": row[0], "avatar_path": row[1]} for row in c.fetchall()]
    conn.close()
    return users

# -----------------------
# Message functions
# -----------------------
def save_message(username, avatar, msg_type, content):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()

    avatar_path = None
    if avatar:
        avatar_name = f"{username}_avatar.png"
        avatar_path = os.path.join(APP_DIR, avatar_name)
        with open(avatar_path, "wb") as f:
            f.write(avatar)

    if msg_type != "text" and hasattr(content, 'read'):
        ext = content.type.split("/")[-1] if hasattr(content, 'type') else "bin"
        content_bytes = content.read()
        content_name = f"{username}_{hashlib.md5(content_bytes).hexdigest()}.{ext}"
        content_path = os.path.join(MEDIA_DIR, content_name)
        with open(content_path, "wb") as f:
            f.write(content_bytes)
        content_ref = content_path
    else:
        content_ref = content if isinstance(content, str) else content.decode()

    now = time.time()
    c.execute(
        "INSERT INTO messages (username, avatar_path, msg_type, content, timestamp) VALUES (?, ?, ?, ?, ?)",
        (username, avatar_path, msg_type, content_ref, now)
    )
    conn.commit()
    conn.close()
    update_user_activity(username)

def load_messages():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT id, username, avatar_path, msg_type, content FROM messages ORDER BY id ASC")
    result = []
    for msg_id, username, avatar_path, msg_type, content_ref in c.fetchall():
        avatar = open(avatar_path, "rb").read() if avatar_path and os.path.exists(avatar_path) else None
        result.append({
            "id": msg_id,
            "username": username,
            "avatar": avatar,
            "type": msg_type,
            "content": content_ref
        })
    conn.close()
    return result

def delete_message(msg_id, username):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT username, content FROM messages WHERE id=?", (msg_id,))
    row = c.fetchone()
    if row and row[0] == username:
        content_path = row[1]
        if os.path.exists(content_path):
            try:
                os.remove(content_path)
            except:
                pass
        c.execute("DELETE FROM messages WHERE id=?", (msg_id,))
    conn.commit()
    conn.close()

def save_system_message(text):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    now = time.time()
    c.execute("INSERT INTO system_messages (content, timestamp) VALUES (?, ?)", (text, now))
    conn.commit()
    conn.close()

def load_system_messages(limit=50):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT id, content FROM system_messages ORDER BY id DESC LIMIT ?", (limit,))
    msgs = [{"id": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return msgs[::-1]

# -----------------------
# Session defaults
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "message_sent" not in st.session_state:
    st.session_state.message_sent = False
if "dismissed_alerts" not in st.session_state:
    st.session_state.dismissed_alerts = set()

# -----------------------
# UI Components
# -----------------------
def show_login_ui():
    st.title("Snowflake Secure Group Login")
    secret_input = st.text_input("Enter school Group Secret Code", type="password", placeholder="Secret Code")
    if st.button("Unlock"):
        entered_hash = hashlib.sha256(secret_input.encode()).hexdigest()
        if entered_hash == SECRET_CODE_HASH:
            st.session_state["access_granted"] = True
            st.success("Access granted! double click")
        else:
            st.error("Incorrect secret code. Access denied.")

def show_profile_setup():
    st.title("Set Your Username and profile picture")
    username = st.text_input("Enter your username:")
    avatar = st.file_uploader("Upload your profile picture (optional)", type=["png", "jpg", "jpeg"])
    if st.button("Enter Chat"):
        if username.strip() == "":
            st.error("Please enter a username.")
        else:
            st.session_state["user"] = username
            st.session_state["user_avatar"] = avatar.read() if avatar else None
            st.session_state["logged_in"] = True
            register_user(username, st.session_state.get("user_avatar"))

# -----------------------
# Display messages
# -----------------------
def display_message(msg, current_user):
    avatar_img = BytesIO(msg["avatar"]) if msg["avatar"] else None
    with st.chat_message(msg["username"], avatar=avatar_img):
        cols = st.columns([10, 1])
        cols[0].markdown(f"**{msg['username']}**")
        if msg["username"] == current_user:
            if cols[1].button("delete", key=f"delmsg_{msg['id']}"):
                delete_message(msg["id"], current_user)
                
        if msg["type"] == "text":
            st.markdown(msg["content"])
        else:
            file_path = msg["content"]
            if not os.path.exists(file_path):
                st.warning("File missing.")
                return
            ext = os.path.splitext(file_path)[1].lower()

            if ext in [".png", ".jpg", ".jpeg", ".gif"]:
                st.image(file_path, use_container_width=True)
            elif ext in [".mp4", ".mov", ".mkv"]:
                st.video(file_path)
            elif ext in [".mp3", ".wav", ".ogg"]:
                st.audio(file_path)
            elif ext in [".pdf", ".txt"]:
                if ext == ".pdf":
                    with open(file_path, "rb") as f:
                        pdf_data = f.read()
                    b64_pdf = base64.b64encode(pdf_data).decode("utf-8")
                    pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600px"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                else:
                    with open(file_path, "r", errors="ignore") as f:
                        st.text(f.read())
            else:
                with open(file_path, "rb") as f:
                    data = f.read()
                b64 = base64.b64encode(data).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(file_path)}">📁 Download {os.path.basename(file_path)}</a>'
                st.markdown(href, unsafe_allow_html=True)

# -----------------------
# Chat UI
# -----------------------
def show_chat_ui():
    user = st.session_state.get("user", "Anonymous")
    st_autorefresh(interval=2000, key="chat_autorefresh")
    update_user_activity(user)

    st.sidebar.markdown("### Online Users")
    online_users = get_online_users(timeout=15)
    for u in online_users:
        avatar_data = open(u["avatar_path"], "rb").read() if u["avatar_path"] and os.path.exists(u["avatar_path"]) else None
        cols = st.sidebar.columns([1, 3])
        if avatar_data:
            cols[0].image(avatar_data, width=30)
        cols[1].write(u["username"])

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Alerts")

    system_msgs = load_system_messages(limit=20)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()

    for msg in system_msgs:
        if msg["id"] not in st.session_state.dismissed_alerts:
            cols = st.sidebar.columns([4, 1])
            cols[0].info(msg["content"])
            if cols[1].button("X", key=f"del_alert_{msg['id']}"):
                if user == "Debayan":
                    c.execute("DELETE FROM system_messages WHERE id=?", (msg["id"],))
                    conn.commit()
                else:
                    st.session_state.dismissed_alerts.add(msg["id"])
    conn.close()

    if st.sidebar.button("Log Out"):
        save_system_message(f"{user} left the chat")
        remove_user(user)
        for key in ["user", "user_avatar", "logged_in", "access_granted", "file_uploaded", "message_sent"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.dismissed_alerts.clear()

    messages = load_messages()
    for msg in messages:
        display_message(msg, user)

    prompt = st.chat_input("Share and enjoy!")
    uploaded_file = st.file_uploader(
        "Upload image/video/audio/document",
        type=None,
        label_visibility="collapsed",
        key="file_uploader"
    )

    if prompt and not st.session_state.message_sent:
        save_message(user, st.session_state.get("user_avatar"), "text", prompt)
        st.session_state.message_sent = True
    if not prompt:
        st.session_state.message_sent = False

    if uploaded_file is not None and not st.session_state.file_uploaded:
        save_message(user, st.session_state.get("user_avatar"), uploaded_file.type.split("/")[0], uploaded_file)
        st.session_state.file_uploaded = True
    if uploaded_file is None:
        st.session_state.file_uploaded = False

# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    if st.session_state.get("logged_in", False):
        show_chat_ui()
    elif st.session_state.get("access_granted", False):
        show_profile_setup()
    else:
        show_login_ui()
