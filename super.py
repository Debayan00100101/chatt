import streamlit as st
import sqlite3
import hashlib
import os
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
import time
import shutil

st.set_page_config(page_title="Snowflake", page_icon="❄", layout="wide")

# -----------------------
# Paths & DB
# -----------------------
APP_DIR = os.path.join(os.path.expanduser("~"), ".snowflake_chat")
os.makedirs(APP_DIR, exist_ok=True)

DB_FILE = os.path.join(APP_DIR, "chat_app.db")
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Messages table
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            msg_type TEXT,
            content TEXT,
            timestamp REAL
        )
    """)
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            last_active REAL
        )
    """)
    conn.commit()
    conn.close()

if not os.path.exists(DB_FILE):
    init_db()

# -----------------------
# User functions
# -----------------------
def register_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = time.time()
    c.execute("""
        INSERT INTO users (username, last_active)
        VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET last_active=excluded.last_active
    """, (username, now))
    conn.commit()
    conn.close()

def update_user_activity(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = time.time()
    c.execute("UPDATE users SET last_active=? WHERE username=?", (now, username))
    conn.commit()
    conn.close()

def get_online_users(timeout=15):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = time.time()
    c.execute("SELECT username FROM users WHERE last_active>=?", (now - timeout,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def check_left_users(timeout=15):
    """Check users who have become inactive and mark them as left"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = time.time()
    c.execute("SELECT username FROM users WHERE last_active<?", (now - timeout,))
    left_users = [row[0] for row in c.fetchall()]
    for username in left_users:
        save_system_message(f"{username} left the chat")
        c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

# -----------------------
# Message functions
# -----------------------
def save_message(username, msg_type, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = time.time()
    c.execute("INSERT INTO messages (username, msg_type, content, timestamp) VALUES (?, ?, ?, ?)",
              (username, msg_type, content, now))
    conn.commit()
    conn.close()
    update_user_activity(username)

def save_system_message(content):
    save_message("System", "text", content)

def load_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, msg_type, content FROM messages ORDER BY id ASC")
    messages = [{"id": row[0], "username": row[1], "type": row[2], "content": row[3]} for row in c.fetchall()]
    conn.close()
    return messages

# -----------------------
# Session defaults
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
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
            st.success("Welcome!")
        else:
            st.error("Incorrect secret code. Access denied.")

def show_profile_setup():
    st.title("Set Your Username")
    username = st.text_input("Enter your username:")
    if st.button("Enter Chat"):
        if username.strip() == "":
            st.error("Please enter a username.")
        else:
            st.session_state["user"] = username
            st.session_state["logged_in"] = True
            register_user(username)
            save_system_message(f"{username} joined the chat!")

def display_message(msg):
    if msg["username"] == "System":
        st.markdown(f"**⚠ {msg['content']}**")
    else:
        st.markdown(f"**{msg['username']}**: {msg['content']}")

def show_chat_ui():
    user = st.session_state.get("user", "Anonymous")
    st.sidebar.success(f"Logged in as {user}")

    # Auto-refresh every 2 seconds
    st_autorefresh(interval=2000, key="chat_autorefresh")

    # Update heartbeat
    update_user_activity(user)

    # Check for users who left
    check_left_users(timeout=15)

    # Show online users
    online_users = get_online_users(timeout=15)
    st.sidebar.markdown("**Online Users:**")
    for u in online_users:
        st.sidebar.write(u)

    if st.sidebar.button("Log Out"):
        save_system_message(f"{user} left the chat")
        for key in ["user", "logged_in", "message_sent"]:
            if key in st.session_state:
                del st.session_state[key]

    # Show messages
    messages = load_messages()
    for msg in messages:
        display_message(msg)

    # Chat input
    prompt = st.chat_input("Type a message...")
    if prompt and not st.session_state.message_sent:
        save_message(user, "text", prompt)
        st.session_state.message_sent = True
    if not prompt:
        st.session_state.message_sent = False

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
