import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

# ================= PAGE CONFIG =================
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
        reasons.append("Over limit claim")

    if amount > 50000:
        score += 20
        reasons.append("High value claim")

    if "unknown" in hospital.lower():
        score += 15
        reasons.append("Unverified hospital")

    return min(score, 100), ", ".join(reasons) if reasons else "Normal case"

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

# ================= MODERN CSS =================
st.markdown("""
<style>

body {
    background: linear-gradient(135deg,#0f172a,#1e293b,#0b1220);
    color: white;
}

/* TITLE */
.title{
    text-align:center;
    font-size:40px;
    font-weight:900;
    background:linear-gradient(90deg,#00c6ff,#7a00ff,#ff00cc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    margin-top:20px;
}

/* LOGIN WRAPPER */
.login-wrapper{
    display:flex;
    justify-content:center;
    align-items:center;
    height:85vh;
}

/* LOGIN CARD */
.login-card{
    width: 380px;
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(14px);
    border-radius: 22px;
    padding: 25px;
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 10px 40px rgba(0,0,0,0.4);
}

/* HEADER */
.login-header{
    text-align:center;
    font-size:22px;
    font-weight:700;
    margin-bottom:10px;
}

/* DEMO BOX */
.demo-box{
    background: rgba(255,255,255,0.08);
    padding:12px;
    border-radius:12px;
    font-size:13px;
    margin-bottom:12px;
}

/* BUTTON */
.stButton>button{
    width:100%;
    background: linear-gradient(90deg,#4f46e5,#06b6d4);
    color:white;
    border-radius:12px;
    padding:10px;
    font-weight:bold;
    border:none;
}

.stButton>button:hover{
    transform: scale(1.02);
    transition: 0.2s;
}

</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">🏥 Smart Health Insurance App</div>', unsafe_allow_html=True)

    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    st.markdown('<div class="login-header">🔐 Welcome Back</div>', unsafe_allow_html=True)

    # DEMO INFO
    st.markdown("""
    <div class="demo-box">
    <b>🧪 Demo Accounts</b><br><br>
    👨‍⚕️ Hospital: hospital@gmail.com / hospital123<br>
    🧑‍💼 Officer: officer@gmail.com / officer123<br>
    👤 User: user@gmail.com / user123
    </div>
    """, unsafe_allow_html=True)

    # QUICK DEMO BUTTONS
    c1, c2, c3 = st.columns(3)

    if c1.button("Hospital"):
        st.session_state.demo_email = "hospital@gmail.com"
        st.session_state.demo_pw = "hospital123"
        st.session_state.demo_role = "Hospital"

    if c2.button("Officer"):
        st.session_state.demo_email = "officer@gmail.com"
        st.session_state.demo_pw = "officer123"
        st.session_state.demo_role = "Officer"

    if c3.button("User"):
        st.session_state.demo_email = "user@gmail.com"
        st.session_state.demo_pw = "user123"
        st.session_state.demo_role = "Policyholder"

    # INPUTS
    email = st.text_input("📧 Email", value=st.session_state.get("demo_email", ""))
    pw = st.text_input("🔑 Password", type="password", value=st.session_state.get("demo_pw", ""))

    role = st.selectbox(
        "👤 Role",
        ["Hospital", "Officer", "Policyholder"],
        index=["Hospital", "Officer", "Policyholder"].index(
            st.session_state.get("demo_role", "Hospital")
        )
    )

    # LOGIN
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

    st.markdown("</div></div>", unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("🏥 Smart Insurance System")
    st.sidebar.write(st.session_state.email)
    st.sidebar.write(st.session_state.role)

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    if st.session_state.role == "Officer":
        menu = st.sidebar.radio("Navigation",
            ["Dashboard", "Review Claims", "Track Claim", "Analytics"])
    else:
        menu = st.sidebar.radio("Navigation",
            ["Dashboard", "Submit Claim", "Track Claim", "Analytics"])

    # DASHBOARD
    if menu == "Dashboard":
        st.title("Enterprise AI Dashboard")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Claims", len(df))
        c2.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)
        c3.metric("Safe", len(df[df["fraud_score"] <= 40]) if not df.empty else 0)

    # SUBMIT CLAIM
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
                score, reason,
                "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                None, None,
                st.session_state.email
            ))

            conn.commit()
            st.success("Claim Submitted")

    # REVIEW CLAIMS
    elif menu == "Review Claims":
        st.title("Officer Review Panel")

        for _, r in df.iterrows():
            st.write(f"ID: {r['claim_id']} | Fraud: {r['fraud_score']} | Status: {r['status']}")

            if r["status"] == "Pending":
                c1, c2 = st.columns(2)

                if c1.button(f"Approve {r['claim_id']}", key=f"a{r['claim_id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",
                                (r['claim_id'],))
                    conn.commit()
                    st.rerun()

                if c2.button(f"Reject {r['claim_id']}", key=f"r{r['claim_id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",
                                (r['claim_id'],))
                    conn.commit()
                    st.rerun()

    # TRACK
    elif menu == "Track Claim":
        st.title("Track Claim")

        cid = st.number_input("Enter Claim ID", min_value=1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            if r:
                st.success("Found Claim")
                st.write(r)
            else:
                st.error("Not found")

    # ANALYTICS
    elif menu == "Analytics":
        st.title("Analytics")
        if not df.empty:
            st.bar_chart(df["fraud_score"])
            st.line_chart(df["claim_amount"])

    conn.close()
