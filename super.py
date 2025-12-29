import streamlit as st
import sqlite3
import os
import hashlib
import time
from io import BytesIO
import base64

# -----------------------
# App Config
# -----------------------
st.set_page_config(page_title="NetFox", layout="wide", page_icon="🦊")

APP_DIR = os.path.join(os.getcwd(), "NetFox_chat_data")
os.makedirs(APP_DIR, exist_ok=True)
DB_FILE = os.path.join(APP_DIR, "netfox_chat.db")
MEDIA_DIR = os.path.join(APP_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# -----------------------
# Database Init
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            username TEXT,
            display_name TEXT,
            avatar_path TEXT,
            last_active REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_email TEXT,
            receiver_email TEXT,
            msg_type TEXT,
            content TEXT,
            timestamp REAL
        )
    """)
    conn.commit()
    conn.close()

if not os.path.exists(DB_FILE):
    init_db()

# -----------------------
# Utility Functions
# -----------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, username, display_name, avatar_bytes):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    avatar_path = None
    if avatar_bytes:
        avatar_path = os.path.join(MEDIA_DIR, f"{email}_avatar.png")
        with open(avatar_path, "wb") as f:
            f.write(avatar_bytes)
    now = time.time()
    c.execute("""
        INSERT INTO users (email, password, username, display_name, avatar_path, last_active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email, hash_password(password), username, display_name, avatar_path, now))
    conn.commit()
    conn.close()

def verify_user(email, password):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

def update_user_activity(email):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    now = time.time()
    c.execute("UPDATE users SET last_active=? WHERE email=?", (now, email))
    conn.commit()
    conn.close()

def save_message(sender_email, receiver_email, msg_type, content):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    content_ref = content
    if msg_type != "text" and hasattr(content, 'read'):
        file_bytes = content.read()
        ext = os.path.splitext(content.name)[1]
        file_path = os.path.join(MEDIA_DIR, f"{sender_email}_{hashlib.md5(file_bytes).hexdigest()}{ext}")
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        content_ref = file_path
    timestamp = time.time()
    c.execute("""
        INSERT INTO messages (sender_email, receiver_email, msg_type, content, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (sender_email, receiver_email, msg_type, content_ref, timestamp))
    conn.commit()
    conn.close()
    update_user_activity(sender_email)

def load_messages(receiver_email=None):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    if receiver_email:
        c.execute("""
            SELECT sender_email, msg_type, content FROM messages
            WHERE receiver_email=? OR receiver_email IS NULL
            ORDER BY timestamp ASC
        """, (receiver_email,))
    else:
        c.execute("SELECT sender_email, msg_type, content FROM messages ORDER BY timestamp ASC")
    msgs = c.fetchall()
    conn.close()
    return msgs

def get_users():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT email, username, display_name, avatar_path FROM users")
    users = c.fetchall()
    conn.close()
    return users

def is_owner(username):
    return username == "_yes_its_dragon_"

# -----------------------
# Session State
# -----------------------
if "step" not in st.session_state:
    st.session_state.step = "login_signup"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "username" not in st.session_state:
    st.session_state.username = ""
if "display_name" not in st.session_state:
    st.session_state.display_name = ""
if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = None
if "message_sent" not in st.session_state:
    st.session_state.message_sent = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

# -----------------------
# Shiny Purple Gradient CSS
# -----------------------
st.markdown("""
<style>
body, .stApp, .main, .block-container, .css-1d391kg {
  background: linear-gradient(270deg, #4b00cc, #6b2cff, #5b1acc, #7b3eff);
  background-size: 800% 800%;
  animation: gradientAnimation 15s ease infinite;
  color: #fff !important;
}
[data-testid="stSidebar"] {
  background: linear-gradient(270deg, #6b2cff, #4b00cc, #7b3eff, #5b1acc);
  background-size: 800% 800%;
  animation: gradientAnimation 15s ease infinite;
}
button, .stButton>button {
  background: linear-gradient(135deg, #6b2cff, #7b3eff) !important;
  color: white !important;
  border: none !important;
  font-weight: bold;
}
input, textarea {
  background: rgba(255,255,255,0.15) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 5px !important;
}
.stChatMessage {
  background: rgba(255,255,255,0.05) !important;
  border-radius: 10px !important;
}
@keyframes gradientAnimation {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}
</style>
""", unsafe_allow_html=True)

# -----------------------
# Pages
# -----------------------
# ----- Login / Signup -----
if st.session_state.step == "login_signup":
    st.title("NetFox Login / Signup")
    email_input = st.text_input("Enter your NetFox email (example@netfox.ai)", placeholder="example@netfox.ai")
    password_input = st.text_input("Enter password", type="password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            if verify_user(email_input, password_input):
                st.success("Login successful!")
                st.session_state.email = email_input
                st.session_state.logged_in = True
                # get username and display_name
                conn = sqlite3.connect(DB_FILE, check_same_thread=False)
                c = conn.cursor()
                c.execute("SELECT username, display_name, avatar_path FROM users WHERE email=?", (email_input,))
                row = c.fetchone()
                conn.close()
                st.session_state.username = row[0]
                st.session_state.display_name = row[1]
                if row[2] and os.path.exists(row[2]):
                    with open(row[2], "rb") as f:
                        st.session_state.user_avatar = f.read()
                st.session_state.step = "main_chat"
            else:
                st.error("Invalid credentials or account does not exist.")
    with col2:
        if st.button("Sign Up"):
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=?", (email_input,))
            if c.fetchone():
                st.error("Email already exists. Please login.")
            elif email_input.strip() == "" or password_input.strip() == "":
                st.error("Email and password required.")
            else:
                st.session_state.email = email_input
                st.session_state.temp_password = password_input
                st.session_state.step = "profile_setup"
            conn.close()

# ----- Profile Setup -----
elif st.session_state.step == "profile_setup":
    st.title("Set Your Profile")
    username_input = st.text_input("Username")
    display_name_input = st.text_input("Display Name")
    avatar_file = st.file_uploader("Upload Avatar (optional)", type=["png","jpg","jpeg"])
    if st.button("Finish Login"):
        avatar_bytes = avatar_file.read() if avatar_file else None
        password = getattr(st.session_state, "temp_password", password_input)
        create_user(st.session_state.email, password, username_input, display_name_input, avatar_bytes)
        st.session_state.username = username_input
        st.session_state.display_name = display_name_input
        st.session_state.user_avatar = avatar_bytes
        st.session_state.logged_in = True
        st.session_state.step = "main_chat"
        st.success("Profile setup complete!")

# ----- Main Chat Page -----
elif st.session_state.logged_in or st.session_state.step == "main_chat":
    st.session_state.step = "main_chat"
    st.title(f"NetFox Chat - {st.session_state.display_name}")

    # Sidebar: Online Users + Navigation
    st.sidebar.title("Navigation")
    if st.session_state.user_avatar:
        st.sidebar.image(st.session_state.user_avatar, width=50)
    st.sidebar.write(st.session_state.display_name)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state.step = "login_signup"
        st.session_state.logged_in = False
        st.session_state.email = ""
        st.session_state.username = ""
        st.session_state.display_name = ""
        st.session_state.user_avatar = None
        st.success("Logged out.")

    # Owner tab for _yes_its_dragon_
    if is_owner(st.session_state.username):
        st.sidebar.markdown("### Owner Panel")
        if st.sidebar.button("View All Users"):
            st.subheader("All Users Data")
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            c = conn.cursor()
            c.execute("SELECT email, password, username, display_name FROM users")
            rows = c.fetchall()
            conn.close()
            for row in rows:
                st.markdown(f"**Email:** {row[0]} | **Password Hash:** {row[1]} | **Username:** {row[2]} | **Display Name:** {row[3]}")
        if st.sidebar.button("View All Messages"):
            st.subheader("All Messages")
            msgs = load_messages()
            users = get_users()
            for sender_email, msg_type, content in msgs:
                sender_name = sender_email
                for u in users:
                    if u[0] == sender_email:
                        sender_name = u[2] or u[1]
                st.markdown(f"**{sender_name}** ({msg_type}): {content}")

    # Display messages
    messages = load_messages()
    users = get_users()
    for sender_email, msg_type, content in messages:
        sender_name = sender_email
        for u in users:
            if u[0] == sender_email:
                sender_name = u[2] or u[1]
        with st.chat_message(sender_name):
            if msg_type == "text":
                st.markdown(content)
            else:
                if os.path.exists(content):
                    ext = os.path.splitext(content)[1].lower()
                    if ext in [".png", ".jpg", ".jpeg", ".gif"]:
                        st.image(content)
                    elif ext in [".mp4", ".mov", ".mkv"]:
                        st.video(content)
                    elif ext in [".mp3", ".wav", ".ogg"]:
                        st.audio(content)
                    else:
                        with open(content, "rb") as f:
                            data = f.read()
                        b64 = base64.b64encode(data).decode()
                        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(content)}">📁 Download {os.path.basename(content)}</a>'
                        st.markdown(href, unsafe_allow_html=True)
    
    # Chat input
    prompt = st.chat_input("Type your message")
    uploaded_file = st.file_uploader("Upload file", type=None, label_visibility="collapsed")
    
    if prompt and not st.session_state.message_sent:
        save_message(st.session_state.email, None, "text", prompt)
        st.session_state.message_sent = True
    if not prompt:
        st.session_state.message_sent = False
    
    if uploaded_file and not st.session_state.file_uploaded:
        save_message(st.session_state.email, None, uploaded_file.type.split("/")[0], uploaded_file)
        st.session_state.file_uploaded = True
    if uploaded_file is None:
        st.session_state.file_uploaded = False
