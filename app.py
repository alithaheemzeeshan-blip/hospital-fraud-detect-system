import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Smart Insurance", layout="wide")

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

def safe(r, *keys):
    for k in keys:
        if k in r:
            return r[k]
    return "N/A"

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

# ================= CLEAN COMPACT UI =================
st.markdown("""
<style>

/* BACKGROUND */
body {
    background: linear-gradient(-45deg,#0f172a,#1e293b,#0b1220);
    color: white;
}

/* TITLE (COMPACT) */
.title{
    text-align:center;
    font-size:34px;
    font-weight:800;
    margin: 6px 0 0 0;
    background: linear-gradient(90deg,#00c6ff,#a855f7,#ff00cc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

/* SUBTITLE (SMALL) */
.subtitle{
    text-align:center;
    font-size:12px;
    color:#cbd5e1;
    margin: 0 0 8px 0;
}

/* LOGIN CENTER (NO EXTRA SPACE) */
.login-wrapper{
    display:flex;
    justify-content:center;
    align-items:center;
    height: calc(100vh - 120px);
}

/* LOGIN CARD COMPACT */
.login-card{
    width: 360px;
    padding: 18px;
    border-radius: 18px;

    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(14px);

    border: 1px solid rgba(255,255,255,0.15);

    box-shadow: 0 0 25px rgba(99,102,241,0.25);
}

/* HEADER */
.login-header{
    text-align:center;
    font-size:18px;
    font-weight:700;
    margin-bottom:6px;
}

/* DEMO BOX */
.demo-box{
    background: rgba(255,255,255,0.07);
    padding:10px;
    border-radius:10px;
    font-size:12px;
    margin-bottom:8px;
}

/* BUTTON */
.stButton>button{
    width:100%;
    background: linear-gradient(90deg,#4f46e5,#06b6d4);
    color:white;
    border-radius:10px;
    padding:8px;
    font-weight:600;
}

</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">🏥 Insurance AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Smart Claims System</div>', unsafe_allow_html=True)

    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    st.markdown('<div class="login-header">Login</div>', unsafe_allow_html=True)

    # DEMO INFO (COMPACT)
    st.markdown("""
    <div class="demo-box">
    Hospital: hospital@gmail.com / 123<br>
    Officer: officer@gmail.com / 123<br>
    User: user@gmail.com / 123
    </div>
    """, unsafe_allow_html=True)

    # QUICK BUTTONS (SMALL SPACE)
    c1, c2, c3 = st.columns(3)

    if c1.button("H"):
        st.session_state.demo_email = "hospital@gmail.com"
        st.session_state.demo_pw = "hospital123"
        st.session_state.demo_role = "Hospital"

    if c2.button("O"):
        st.session_state.demo_email = "officer@gmail.com"
        st.session_state.demo_pw = "officer123"
        st.session_state.demo_role = "Officer"

    if c3.button("U"):
        st.session_state.demo_email = "user@gmail.com"
        st.session_state.demo_pw = "user123"
        st.session_state.demo_role = "Policyholder"

    email = st.text_input("Email", value=st.session_state.get("demo_email", ""))
    pw = st.text_input("Password", type="password", value=st.session_state.get("demo_pw", ""))

    role = st.selectbox(
        "Role",
        ["Hospital", "Officer", "Policyholder"],
        index=["Hospital", "Officer", "Policyholder"].index(
            st.session_state.get("demo_role", "Hospital")
        )
    )

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
            st.error("Invalid")

    st.markdown("</div></div>", unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("Insurance AI")
    st.sidebar.write(st.session_state.email)

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    menu = st.sidebar.radio("Menu",
        ["Dashboard", "Submit Claim", "Review Claims", "Track", "Analytics"])

    if menu == "Dashboard":
        st.title("Dashboard")
        st.metric("Total Claims", len(df))

    elif menu == "Submit Claim":
        st.title("Submit")

        p = st.text_input("Policy")
        patient = st.text_input("Patient")
        hospital = st.text_input("Hospital")
        treatment = st.text_input("Treatment")
        amount = st.number_input("Amount", min_value=0.0)

        if st.button("Submit"):
            score, reason = ai_fraud_model(amount, 50000, hospital)

            cur = conn.cursor()
            cur.execute("""
                INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (p, patient, hospital, treatment, amount,
                  score, reason, "Pending",
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  None, None, st.session_state.email))

            conn.commit()
            st.success("Submitted")

    elif menu == "Review Claims":
        st.title("Review")

        for _, r in df.iterrows():
            st.write(r["claim_id"], r["fraud_score"], r["status"])

    elif menu == "Track":
        st.title("Track")
        cid = st.number_input("ID", min_value=1)
        if st.button("Search"):
            r = conn.cursor().execute(
                "SELECT * FROM claims WHERE claim_id=?", (cid,)
            ).fetchone()

            st.write(r if r else "Not found")

    elif menu == "Analytics":
        st.title("Analytics")
        if not df.empty:
            st.bar_chart(df["fraud_score"])
            st.line_chart(df["claim_amount"])

    conn.close()
