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

# ================= SAFE GET =================
def safe(r, *keys):
    for k in keys:
        if k in r:
            return r[k]
    return "N/A"

# ================= AI FRAUD =================
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

# ================= AI DECISION =================
def ai_decision(score):
    if score >= 75:
        return "Rejected", "High fraud risk"
    elif score >= 40:
        return "Review", "Medium risk"
    else:
        return "Approved", "Low risk"

# ================= EMAIL SIM =================
def send_email(to, subject, msg):
    st.info(f"""
📧 EMAIL (SIMULATION)

To: {to}
Subject: {subject}

Message:
{msg}
""")

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

    try:
        c.execute("ALTER TABLE claims ADD COLUMN submitted_by TEXT")
    except:
        pass

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

# ================= ORIGINAL UI =================
st.markdown("""
<style>

body {
    background:#0b1220;
    color:white;
}

.title {
    text-align:center;
    font-size:42px;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#7a00ff,#ff00cc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.card {
    background: rgba(255,255,255,0.04);
    padding:15px;
    border-radius:15px;
    margin-bottom:10px;
    border:1px solid rgba(255,255,255,0.08);
}

.high{color:#ff4d4d;font-weight:800;}
.medium{color:#fbbf24;font-weight:800;}
.low{color:#22c55e;font-weight:800;}

.stButton>button {
    background: linear-gradient(90deg,#4f46e5,#06b6d4);
    color:white;
    border-radius:10px;
    padding:8px 14px;
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

    st.markdown("""
    <div class="card">
    Demo:
    hospital@gmail.com / hospital123  
    officer@gmail.com / officer123  
    user@gmail.com / user123
    </div>
    """, unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("🏥 Smart Insurance System")
    st.sidebar.write(st.session_state.email)
    st.sidebar.write(st.session_state.role)

    if st.sidebar.button("🚪 Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    menu = st.sidebar.radio("Menu", ["Dashboard", "Submit Claim", "Review Claims", "Analytics"])

    # ================= DASHBOARD =================
    if menu == "Dashboard":

        st.markdown('<div class="title">Enterprise AI Dashboard</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Claims", len(df))
        c2.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)
        c3.metric("Safe", len(df[df["fraud_score"] <= 40]) if not df.empty else 0)

        if not df.empty:
            for _, r in df.tail(6).iterrows():

                level = "high" if r["fraud_score"] > 70 else "medium" if r["fraud_score"] > 40 else "low"

                st.markdown(f"""
                <div class="card">
                    <b>ID:</b> {safe(r,'claim_id')} |
                    <span class="{level}">{safe(r,'fraud_score')}%</span><br><br>

                    🏥 {safe(r,'hospital_name')}<br>
                    👤 {safe(r,'patient_name')}<br>
                    💊 {safe(r,'treatment')}<br>
                    💰 {safe(r,'claim_amount')}<br>
                    📌 {safe(r,'status')}
                </div>
                """, unsafe_allow_html=True)

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":

        st.title("Submit Claim")

        p = st.text_input("Policy Number")
        patient = st.text_input("Patient Name")
        hospital = st.text_input("Hospital Name")

        treatment = st.selectbox("Treatment Type", [
            "General Checkup","Emergency Care","Surgery","Cardiology",
            "Orthopedic","Neurology","Dental","Maternity","Radiology","ICU"
        ])

        amount = st.number_input("Claim Amount", min_value=0.0)

        uploaded_file = st.file_uploader("Upload Medical Image", type=["jpg","jpeg","png"])

        file_path = None
        file_type = None

        if uploaded_file:
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            file_type = "image"

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
                file_path,
                file_type,
                st.session_state.email
            ))

            conn.commit()
            st.success("Claim Submitted")

    # ================= REVIEW CLAIMS =================
    elif menu == "Review Claims":

        st.title("Officer Review Panel")

        for _, r in df.iterrows():

            st.markdown(f"""
            <div class="card">
                <b>ID:</b> {safe(r,'claim_id')} |
                <span class="medium">{safe(r,'fraud_score')}%</span><br>
                🏥 {safe(r,'hospital_name')} | 👤 {safe(r,'patient_name')}<br>
                💊 {safe(r,'treatment')}<br>
                📌 {safe(r,'status')}
            </div>
            """, unsafe_allow_html=True)

            if r["status"] == "Pending":

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(f"Approve {r['claim_id']}", key=f"a{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",(r['claim_id'],))
                        conn.commit()
                        st.rerun()

                with col2:
                    if st.button(f"Reject {r['claim_id']}", key=f"r{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",(r['claim_id'],))
                        conn.commit()
                        st.rerun()

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("Analytics")

        if "fraud_score" in df.columns:
            st.bar_chart(df["fraud_score"])

        if "claim_amount" in df.columns:
            st.line_chart(df["claim_amount"])

    conn.close()
