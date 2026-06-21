import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Smart Health Insurance System", layout="wide")

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

# ================= AI =================
def ai_fraud_model(amount, limit, hospital):
    score = 0
    reasons = []

    if amount > limit:
        score += 40
        reasons.append("Over limit")

    if amount > 50000:
        score += 20
        reasons.append("High amount")

    if "unknown" in hospital.lower():
        score += 15
        reasons.append("Unverified hospital")

    return min(score, 100), ", ".join(reasons) if reasons else "Normal"

# ================= INIT DB (CLEAN) =================
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
        reason TEXT,
        status TEXT,
        date TEXT,
        submitted_by TEXT
    )
    """)

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

# ================= SAFE GET FUNCTION =================
def safe(r, key, default="N/A"):
    return r[key] if key in r else default

# ================= UI =================
st.markdown("""
<style>
body {background:#0b1220;color:white;}
.title{
text-align:center;
font-size:42px;
font-weight:900;
background:linear-gradient(90deg,#00c6ff,#7a00ff,#ff00cc);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
}
.card{
background:rgba(255,255,255,0.04);
padding:15px;
border-radius:15px;
margin:10px 0;
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">🏥 Smart Health Insurance System</div>', unsafe_allow_html=True)

    email = st.text_input("Email")
    pw = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Hospital", "Officer", "Policyholder"])

    if st.button("Login"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=? AND role=?",
                  (email, hash_password(pw), role))

        if c.fetchone():
            st.session_state.login = True
            st.session_state.email = email
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid login")

# ================= MAIN =================
else:

    st.sidebar.write(st.session_state.email)
    st.sidebar.write(st.session_state.role)

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    menu = st.sidebar.radio("Menu", ["Dashboard", "Submit Claim", "Review Claims", "Analytics"])

    # ================= DASHBOARD =================
    if menu == "Dashboard":

        st.title("Dashboard")

        st.metric("Total Claims", len(df))

    # ================= SUBMIT =================
    elif menu == "Submit Claim":

        st.title("Submit Claim")

        p = st.text_input("Policy Number")
        patient = st.text_input("Patient Name")
        hospital = st.text_input("Hospital Name")
        treatment = st.text_input("Treatment")
        amount = st.number_input("Amount", 0.0)

        if st.button("Submit"):

            score, reason = ai_fraud_model(amount, 50000, hospital)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?)
            """, (
                p, patient, hospital, treatment,
                amount, score, reason,
                "Pending",
                datetime.now().strftime("%Y-%m-%d"),
                st.session_state.email
            ))

            conn.commit()
            st.success("Submitted")

    # ================= REVIEW =================
    elif menu == "Review Claims":

        st.title("Review Claims")

        for _, r in df.iterrows():

            st.markdown(f"""
            <div class="card">
                ID: {r['claim_id']}<br>
                🏥 Hospital: {r.get('hospital_name','N/A')}<br>
                👤 Patient: {r.get('patient_name','N/A')}<br>
                💊 Treatment: {r.get('treatment','N/A')}<br>
                💰 Amount: {r.get('claim_amount','N/A')}<br>
                📌 Status: {r.get('status','N/A')}
            </div>
            """, unsafe_allow_html=True)

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("Analytics")

        if "fraud_score" in df.columns:
            st.bar_chart(df["fraud_score"])

        if "claim_amount" in df.columns:
            st.line_chart(df["claim_amount"])
