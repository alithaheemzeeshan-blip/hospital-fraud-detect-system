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

# ================= FRAUD MODEL (FIXED) =================
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

# ================= STYLE =================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg,#0b1220,#111827,#0f172a);
    color: white;
}

.title {
    text-align:center;
    font-size:36px;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#ff00cc,#22c55e);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.card {
    padding:14px;
    margin:8px 0;
    border-radius:14px;
    background: rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.12);
}

.stat {
    padding:16px;
    border-radius:12px;
    text-align:center;
    background: rgba(255,255,255,0.08);
}

.low {color:#22c55e; font-weight:700;}
.medium {color:#facc15; font-weight:700;}
.high {color:#ef4444; font-weight:700;}

.stButton>button {
    width:100%;
    border-radius:10px;
    background: linear-gradient(90deg,#4f46e5,#06b6d4,#a855f7);
    color:white;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">🏥 Smart Health Insurance System 💙</div>', unsafe_allow_html=True)

    email = st.text_input("📧 Email")
    pw = st.text_input("🔑 Password", type="password")
    role = st.selectbox("👤 Role", ["Hospital", "Officer", "Policyholder"])

    if st.button("🚀 Login"):
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
            st.error("❌ Invalid credentials")

    st.markdown("---")
    st.markdown("""
### 🔑 Demo Logins

🏥 Hospital → hospital@gmail.com / hospital123  
🕵️ Officer → officer@gmail.com / officer123  
👨‍⚕️ User → user@gmail.com / user123
""")

# ================= MAIN =================
else:

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    # FIX: ensure numeric (THIS fixes your 0 risk problem)
    if not df.empty:
        df["fraud_score"] = pd.to_numeric(df["fraud_score"], errors="coerce").fillna(0)

    st.sidebar.title("🏥 Insurance System")
    st.sidebar.write(st.session_state.email)

    if st.sidebar.button("🚪 Logout"):
        st.session_state.login = False
        st.rerun()

    menu = st.sidebar.radio("Menu",
        ["Dashboard", "Submit Claim", "Review Claims", "Track Claim", "Analytics"]
    )

    # ================= DASHBOARD (IMPROVED) =================
    if menu == "Dashboard":
        st.markdown('<div class="title">📊 Dashboard</div>', unsafe_allow_html=True)

        total = len(df)
        approved = len(df[df["status"] == "Approved"]) if not df.empty else 0
        rejected = len(df[df["status"] == "Rejected"]) if not df.empty else 0
        pending = len(df[df["status"] == "Pending"]) if not df.empty else 0
        high_risk = len(df[df["fraud_score"] > 70]) if not df.empty else 0

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.markdown(f"<div class='stat'>📄<br><b>{total}</b><br>Total</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat'>✅<br><b>{approved}</b><br>Approved</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat'>❌<br><b>{rejected}</b><br>Rejected</div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat'>⏳<br><b>{pending}</b><br>Pending</div>", unsafe_allow_html=True)
        c5.markdown(f"<div class='stat'>⚠️<br><b>{high_risk}</b><br>High Risk</div>", unsafe_allow_html=True)

    # ================= SUBMIT CLAIM (WITH IMAGE UPLOAD) =================
    elif menu == "Submit Claim":

        st.title("📝 Submit Claim")

        p = st.text_input("📄 Policy Number")
        patient = st.text_input("👤 Patient Name")
        hospital = st.text_input("🏥 Hospital Name")

        treatment = st.selectbox("🏥 Treatment Type", [
            "General Checkup","Emergency","Surgery","Heart Surgery",
            "Cancer","Dialysis","Maternity","Dental","Eye","Orthopedic","Other"
        ])

        amount = st.number_input("💰 Claim Amount", min_value=0.0)

        uploaded_file = st.file_uploader("📤 Upload Medical Report (Image/PDF)")

        file_path = None
        file_type = None

        if uploaded_file is not None:
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())
            file_type = uploaded_file.type
            st.success("📁 File Uploaded Successfully")

        if st.button("🚀 Submit Claim"):

            score, reason = ai_fraud_model(amount, 50000, hospital)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p, patient, hospital, treatment, amount,
                score, reason, "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                file_path, file_type, st.session_state.email
            ))

            conn.commit()
            st.success("✅ Claim Submitted")

    # ================= REVIEW =================
    elif menu == "Review Claims":

        st.title("🕵️ Officer Panel")

        for _, r in df.iterrows():

            score = float(r["fraud_score"])

            if score < 40:
                risk = "LOW"
                cls = "low"
            elif score < 70:
                risk = "MEDIUM"
                cls = "medium"
            else:
                risk = "HIGH"
                cls = "high"

            st.markdown(f"""
            <div class="card">
                <b>ID:</b> {r['claim_id']} |
                <b>Patient:</b> {r['patient_name']} |
                <b>Hospital:</b> {r['hospital_name']}<br>
                <b>Treatment:</b> {r['treatment']}<br>
                <b>Score:</b> {score}% <span class="{cls}">{risk}</span><br>
                <b>Status:</b> {r['status']}<br>
                <b>Reason:</b> {r['fraud_reason']}
            </div>
            """, unsafe_allow_html=True)

    # ================= TRACK =================
    elif menu == "Track Claim":

        st.title("📍 Track Claim")

        cid = st.number_input("Enter Claim ID", min_value=1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()
            st.write(r if r else "❌ Not Found")

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("📈 Analytics")

        if not df.empty:
            st.bar_chart(df["fraud_score"])
            st.line_chart(df["claim_amount"])

    conn.close()
