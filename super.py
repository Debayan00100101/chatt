import streamlit as st
import sqlite3
import hashlib
import os
import base64
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
import shutil
import time

st.set_page_config(page_title="Snowflake", page_icon="❄", layout="wide")

# -----------------------
# Paths & DB
# -----------------------
APP_DIR = os.path.join(os.path.expanduser("~"), ".snowflake_chat")
os.makedirs(APP_DIR, exist_ok=True)

DB_FILE = os.path.join(APP_DIR, "super_chat_app_v2.db")
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
# DB Initialization & Migration
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            avatar_path TEXT,
            msg_type TEXT,
            content TEXT,
            last_active REAL
        )
    """)
    conn.commit()
    conn.close()

def add_last_active_column():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA table_info(messages)")
    columns = [col[1] for col in c.fetchall()]
    if "last_active" not in columns:
        c.execute("ALTER TABLE messages ADD COLUMN last_active REAL")
        conn.commit()
    conn.close()

if not os.path.exists(DB_FILE):
    init_db()
else:
    add_last_active_column()  # Ensure last_active exists for old DBs

# -----------------------
# Database functions
# -----------------------
def save_message(username, avatar, msg_type, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Save avatar to file
    avatar_path = None
    if avatar:
        avatar_name = f"{username}_avatar.png"
        avatar_path = os.path.join(APP_DIR, avatar_name)
        with open(avatar_path, "wb") as f:
            f.write(avatar)

    # Save content to file if media
    if msg_type != "text" and hasattr(content, 'read'):
        ext = content.type.split("/")[-1]
        content_name = f"{username}_{hashlib.md5(content.read()).hexdigest()}.{ext}"
        content_path = os.path.join(MEDIA_DIR, content_name)
        content.seek(0)
        with open(content_path, "wb") as f:
            shutil.copyfileobj(content, f)
        content_ref = content_path
    else:
        content_ref = content if isinstance(content, str) else content.decode()

    now = time.time()
    c.execute(
        "INSERT INTO messages (username, avatar_path, msg_type, content, last_active) VALUES (?, ?, ?, ?, ?)",
        (username, avatar_path, msg_type, content_ref, now)
    )
    conn.commit()
    conn.close()

def update_last_active(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = time.time()
    c.execute("UPDATE messages SET last_active=? WHERE username=? ORDER BY id DESC LIMIT 1", (now, username))
    conn.commit()
    conn.close()

def delete_message(message_id, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT avatar_path, content FROM messages WHERE id=? AND username=?", (message_id, username))
    row = c.fetchone()
    if row:
        avatar_path, content_ref = row
        if avatar_path and os.path.exists(avatar_path):
            os.remove(avatar_path)
        if content_ref and os.path.exists(content_ref) and content_ref.startswith(MEDIA_DIR):
            os.remove(content_ref)
    c.execute("DELETE FROM messages WHERE id=? AND username=?", (message_id, username))
    conn.commit()
    conn.close()

def load_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, avatar_path, msg_type, content FROM messages ORDER BY id ASC")
    result = []
    for msg_id, username, avatar_path, msg_type, content_ref in c.fetchall():
        avatar = open(avatar_path, "rb").read() if avatar_path and os.path.exists(avatar_path) else None
        if msg_type == "text":
            content = content_ref
        else:
            content = open(content_ref, "rb").read() if content_ref and os.path.exists(content_ref) else None
        result.append({
            "id": msg_id,
            "username": username,
            "avatar": avatar,
            "type": msg_type,
            "content": content
        })
    conn.close()
    return result

def get_online_users(timeout=120):
    """Return usernames active in last `timeout` seconds"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = time.time()
    c.execute("SELECT DISTINCT username FROM messages WHERE last_active>=?", (now - timeout,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# -----------------------
# Session state defaults
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "message_sent" not in st.session_state:
    st.session_state.message_sent = False

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
            st.success("Welcome! double click")
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
            st.success(f"Welcome {username}! double click")

def display_message(msg):
    is_own_message = msg["username"] == st.session_state.get("user", "")
    avatar_img = BytesIO(msg["avatar"]) if msg["avatar"] else None

    with st.chat_message(msg["username"], avatar=avatar_img):
        st.markdown(f"**{msg['username']}**")
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "image":
            media = BytesIO(msg["content"])
            st.image(media)
        elif msg["type"] == "video":
            media = BytesIO(msg["content"])
            st.video(media)
        elif msg["type"] == "audio":
            media = BytesIO(msg["content"])
            st.audio(media)

        if is_own_message:
            if st.button("Delete", key=f"del_{msg['id']}", use_container_width=False):
                delete_message(msg["id"], msg["username"])

def show_chat_ui():
    user = st.session_state.get("user", "Anonymous")
    st.sidebar.success(f"Logged in as {user}")

    # Show online users
    online_users = get_online_users(timeout=120)
    st.sidebar.markdown("**Online Users:**")
    for u in online_users:
        st.sidebar.write(u)

    if st.sidebar.button("Log Out"):
        for key in ["user", "user_avatar", "logged_in", "access_granted", "file_uploaded", "message_sent"]:
            if key in st.session_state:
                del st.session_state[key]

    # Auto-refresh
    st_autorefresh(interval=2000, key="chat_autorefresh")

    # Update last_active timestamp
    update_last_active(user)

    st.title("Super")
    messages = load_messages()
    for msg in messages:
        display_message(msg)

    prompt = st.chat_input("Share and enjoy!")
    uploaded_file = st.file_uploader(
        "Upload image/video/audio",
        type=["png", "jpg", "jpeg", "mp4", "mp3", "wav"],
        label_visibility="collapsed",
        key="file_uploader"
    )

    if prompt and not st.session_state.message_sent:
        save_message(st.session_state["user"], st.session_state.get("user_avatar"), "text", prompt)
        st.session_state.message_sent = True
    if not prompt:
        st.session_state.message_sent = False

    if uploaded_file is not None and not st.session_state.file_uploaded:
        save_message(st.session_state["user"], st.session_state.get("user_avatar"), uploaded_file.type.split("/")[0], uploaded_file)
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
