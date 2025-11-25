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
# Paths & DB
# -----------------------
APP_DIR = os.path.join(os.path.expanduser("~"), ".snowflake_chat")
os.makedirs(APP_DIR, exist_ok=True)

DB_PATH = os.path.join(APP_DIR, "chat.db")

# -----------------------
# DB Functions
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT,
            timestamp REAL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert TEXT,
            timestamp REAL
        )
    ''')

    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    c.execute("INSERT INTO users (username,password) VALUES (?,?)", (username, hashed))
    conn.commit()
    conn.close()

def validate_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed))
    user = c.fetchone()
    conn.close()
    return user

def add_message(sender, message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender,message,timestamp) VALUES (?,?,?)",
              (sender, message, time.time()))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, sender, message FROM messages ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_message(mid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE id=?", (mid,))
    conn.commit()
    conn.close()

def add_alert(alert):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO alerts (alert,timestamp) VALUES (?,?)", (alert, time.time()))
    conn.commit()
    conn.close()

def get_alerts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, alert FROM alerts ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_alert(aid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM alerts WHERE id=?", (aid,))
    conn.commit()
    conn.close()

# Initialize DB
init_db()

# Auto refresh every 10 seconds
st_autorefresh(interval=10000, limit=None, key="refresh_key")

# -----------------------
# Login / Register
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if validate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            try:
                add_user(new_username, new_password)
                st.success("Account created! Login now.")
            except:
                st.error("Username already exists.")

    st.stop()

# -----------------------
# Main Chat UI
# -----------------------
st.title("Snowflake Chat")

col1, col2 = st.columns([3, 1])

# -----------------------
# Chat Messages
# -----------------------
with col1:
    st.subheader("Chat Messages")

    all_msgs = get_messages()

    for msg in all_msgs:
        mid, sender, text = msg
        cols = st.columns([9, 1])

        with cols[0]:
            st.write(f"**{sender}:** {text}")

        # FIXED LINE: removed the wrong ']' and made the bracket correct
        if cols[1].button("X", key=f"del_msg_{msg[0]}"):
            delete_message(mid)
            st.experimental_rerun()

    new_msg = st.text_input("Type message")
    if st.button("Send"):
        if new_msg.strip():
            add_message(st.session_state.username, new_msg)
            st.experimental_rerun()

# -----------------------
# Alerts
# -----------------------
with col2:
    st.subheader("Alerts")

    all_alerts = get_alerts()

    for msg in all_alerts:
        aid, text = msg
        cols = st.columns([9, 1])

        with cols[0]:
            st.write(text)

        # FIXED LINE (same issue)
        if cols[1].button("X", key=f"del_alert_{msg[0]}"):
            delete_alert(aid)
            st.experimental_rerun()

    new_alert = st.text_input("Create Alert")
    if st.button("Add Alert"):
        if new_alert.strip():
            add_alert(new_alert)
            st.experimental_rerun()
