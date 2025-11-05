import streamlit as st
import sqlite3
import hashlib
import os
import base64
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
st.set_page_config(page_title="Snowflake", page_icon="data:image/png;base64,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", layout="wide")

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
    st.title("Snowflake Secure Group Login")
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


