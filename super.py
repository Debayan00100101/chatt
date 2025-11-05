import streamlit as st
import sqlite3
import hashlib
import os
import base64
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
st.set_page_config(page_title="Super", page_icon="🎓", layout="wide")

def _secure_secret_hash():
    parts = ["73757065723030313030313031"]
    secret_bytes = bytes.fromhex("".join(parts))
    return hashlib.sha256(secret_bytes).hexdigest()


SECRET_CODE_HASH = _secure_secret_hash()
DB_FILE = "super_chat_app_v2.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            avatar BLOB,
            msg_type TEXT,
            content BLOB
        )
    """)
    conn.commit()
    conn.close()


def save_message(username, avatar, msg_type, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    avatar_blob = base64.b64encode(avatar).decode() if isinstance(avatar, bytes) else None
    content_blob = base64.b64encode(content.read()).decode() if hasattr(content, 'read') else content
    c.execute("INSERT INTO messages (username, avatar, msg_type, content) VALUES (?, ?, ?, ?)",
              (username, avatar_blob, msg_type, content_blob))
    conn.commit()
    conn.close()


def delete_message(message_id, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE id = ? AND username = ?", (message_id, username))
    conn.commit()
    conn.close()


def load_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, avatar, msg_type, content FROM messages ORDER BY id ASC")
    result = []
    for msg_id, username, avatar_b64, msg_type, content_b64 in c.fetchall():
        avatar = base64.b64decode(avatar_b64) if avatar_b64 else None
        if msg_type == "text":
            content = content_b64  # plain text string
        else:
            content = base64.b64decode(content_b64) if content_b64 else None  # binary media
        result.append({"id": msg_id, "username": username, "avatar": avatar, "type": msg_type, "content": content})
    conn.close()
    return result


if not os.path.exists(DB_FILE):
    init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "message_sent" not in st.session_state:
    st.session_state.message_sent = False


def show_login_ui():
    st.title("Super Secure Group Login")
    secret_input = st.text_input("Enter school Group Secret Code", type="password", placeholder="Secret Code")
    if st.button("Unlock"):
        entered_hash = hashlib.sha256(secret_input.encode()).hexdigest()
        if entered_hash == SECRET_CODE_HASH:
            st.session_state["access_granted"] = True
            st.success("Access code verified. Please set up your profile.")
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
            st.success(f"Welcome {username}!")


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

    if st.sidebar.button("Log Out"):
        for key in ["user", "user_avatar", "logged_in", "access_granted", "file_uploaded", "message_sent"]:
            if key in st.session_state:
                del st.session_state[key]

    # Auto-refresh every 2 seconds
    st_autorefresh(interval=2000, key="chat_autorefresh")

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


if __name__ == "__main__":
    if st.session_state.get("logged_in", False):
        show_chat_ui()
    elif st.session_state.get("access_granted", False):
        show_profile_setup()
    else:
        show_login_ui()

