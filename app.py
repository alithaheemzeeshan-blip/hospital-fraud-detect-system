import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Smart Health Insurance System", layout="centered")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""
    st.session_state.email = ""

# ================= DB =================
def get_conn():
    return sqlite3.connect("insurance.db", check_same_thread=False)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ================= AI MODEL =================
def ai_fraud_model(amount, limit, hospital):
    score = 0
    reasons = []

    if amount > limit:
        score += 40
        reasons.append("Over limit")

    if amount > 50000:
        score += 20
        reasons.append("High value")

    if "unknown" in hospital.lower():
        score += 15
        reasons.append("Unverified hospital")

    return min(score, 100), ", ".join(reasons) if reasons else "Normal"

# ================= INIT DB =================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        email TEXT,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS claims(
        claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_number TEXT,
        patient_name TEXT,
        hospital_name TEXT,
        treatment TEXT,
        claim_amount REAL,
        fraud_score REAL,
        fraud_reason TEXT,
        status TEXT,
        submission_date TEXT,
        file_path TEXT,
        file_type TEXT,
        submitted_by TEXT
    )
    """)

    conn.commit()

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        users = [
            ("hospital@gmail.com", hash_password("hospital123"), "Hospital"),
            ("officer@gmail.com", hash_password("officer123"), "Officer"),
            ("user@gmail.com", hash_password("user123"), "Policyholder"),
        ]
        c.executemany("INSERT INTO users VALUES (?,?,?)", users)

    conn.commit()
    conn.close()

init_db()

# ================= IMPROVED COLORFUL UI =================
st.markdown("""
<style>

body {
    background: linear-gradient(135deg,#0f172a,#1e293b,#0b1220);
    color: white;
}

/* APP TITLE (ORIGINAL NAME RESTORED) */
.title {
    text-align:center;
    font-size:34px;
    font-weight:900;
    margin-top:10px;
    background: linear-gradient(90deg,#00c6ff,#ff00cc,#a855f7,#22c55e);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

/* LOGIN CARD */
.login-card {
    max-width: 380px;
    margin: auto;
    margin-top: 20px;
    padding: 22px;
    border-radius: 18px;

    background: rgba(255,255,255,0.07);
    backdrop-filter: blur(15px);

    border: 1px solid rgba(255,255,255,0.15);

    box-shadow: 0 0 30px rgba(168,85,247,0.25);
}

/* LOGIN TITLE */
.login-title {
    text-align:center;
    font-size:18px;
    font-weight:700;
    margin-bottom:10px;
    color:#ffffff;
}

/* DEMO BOX (COLORED) */
.demo-box {
    margin-top:12px;
    padding:12px;
    border-radius:12px;
    font-size:12px;

    background: rgba(0,0,0,0.25);
    border-left: 3px solid #a855f7;
}

/* BUTTON */
.stButton>button {
    width:100%;
    border-radius:10px;
    background: linear-gradient(90deg,#4f46e5,#06b6d4,#a855f7);
    color:white;
    padding:10px;
    font-weight:700;
}

/* INPUT CLEAN */
input {
    border-radius:8px !important;
}

</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    # 🔥 PROJECT NAME (RESTORED ORIGINAL)
    st.markdown('<div class="title">🏥 Smart Health Insurance System</div>', unsafe_allow_html=True)

    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    st.markdown('<div class="login-title">🔐 Login Portal</div>', unsafe_allow_html=True)

    # INPUTS
    email = st.text_input("Email")
    pw = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Hospital", "Officer", "Policyholder"])

    # LOGIN BUTTON
    if st.button("Login"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM users
            WHERE email=? AND password=? AND role=?
        """, (email, hash_password(pw), role))

        if c.fetchone():
            st.session_state.login = True
            st.session_state.email = email
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid credentials")

    # ================= DEMO OPTIONS (NOW BELOW LOGIN) =================
    st.markdown("""
    <div class="demo-box">
    <b>🧪 Demo Accounts</b><br><br>
    👨‍⚕️ Hospital: hospital@gmail.com / hospital123<br>
    🧑‍💼 Officer: officer@gmail.com / officer123<br>
    👤 Policyholder: user@gmail.com / user123
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("Smart Insurance System")
    st.sidebar.write(st.session_state.email)

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Submit Claim", "Review Claims", "Track Claim", "Analytics"]
    )

    if menu == "Dashboard":
        st.title("Dashboard")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Claims", len(df))
        c2.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)
        c3.metric("Safe", len(df[df["fraud_score"] <= 40]) if not df.empty else 0)

    elif menu == "Submit Claim":
        st.title("Submit Claim")

        p = st.text_input("Policy Number")
        patient = st.text_input("Patient Name")
        hospital = st.text_input("Hospital Name")
        treatment = st.text_input("Treatment Type")
        amount = st.number_input("Claim Amount", min_value=0.0)

        if st.button("Submit"):
            score, reason = ai_fraud_model(amount, 50000, hospital)

            cur = conn.cursor()
            cur.execute("""
                INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p, patient, hospital, treatment, amount,
                score, reason, "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                None, None, st.session_state.email
            ))

            conn.commit()
            st.success("Claim Submitted")

    elif menu == "Review Claims":
        st.title("Officer Panel")

        for _, r in df.iterrows():
            st.write(f"ID:{r['claim_id']} | Score:{r['fraud_score']} | {r['status']}")

    elif menu == "Track Claim":
        st.title("Track Claim")

        cid = st.number_input("Claim ID", min_value=1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            st.write(r if r else "Not Found")

    elif menu == "Analytics":
        st.title("Analytics")

        if not df.empty:
            st.bar_chart(df["fraud_score"])
            st.line_chart(df["claim_amount"])

    conn.close()
