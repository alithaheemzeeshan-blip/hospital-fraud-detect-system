import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import random
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Smart Health Insurance AI", layout="centered")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.email = ""
    st.session_state.role = ""

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

# ================= AI FRAUD MODEL =================
def ai_fraud_model(amount, limit, hospital, treatment):

    score = 0
    reasons = []

    if amount <= 5000:
        score += 5
    elif amount <= 20000:
        score += 15
    elif amount <= 50000:
        score += 30
        reasons.append("Medium-high claim amount")
    else:
        score += 50
        reasons.append("Very high claim amount")

    if amount > limit:
        score += 25
        reasons.append("Exceeds policy limit")

    bad_hospitals = ["unknown", "fake", "clinic", "small"]
    if any(x in hospital.lower() for x in bad_hospitals):
        score += 20
        reasons.append("Suspicious hospital")

    high_risk_treatments = ["surgery", "cancer", "heart", "dialysis"]
    if any(t in treatment.lower() for t in high_risk_treatments):
        score += 20
    else:
        score += 5

    score += random.randint(0, 10)
    score = min(score, 100)

    if score < 40:
        label = "LOW"
    elif score < 70:
        label = "MEDIUM"
    else:
        label = "HIGH"

    if not reasons:
        reasons = ["Normal claim pattern"]

    return score, reasons, label

# ================= STYLE =================
st.markdown("""
<style>
body {background:#0f172a;color:white;}

.title{
text-align:center;
font-size:36px;
font-weight:900;
background:linear-gradient(90deg,#00c6ff,#ff00cc,#22c55e);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
}

.card{
padding:14px;
margin:10px 0;
border-radius:14px;
background:rgba(255,255,255,0.08);
border:1px solid rgba(255,255,255,0.12);
}

.stat{
padding:18px;
border-radius:14px;
text-align:center;
background:linear-gradient(135deg,#1e3a8a,#0ea5e9,#22c55e);
color:white;
font-weight:700;
}

.low{color:#22c55e;font-weight:700;}
.medium{color:#facc15;font-weight:700;}
.high{color:#ef4444;font-weight:700;}

.stButton>button{
width:100%;
border-radius:10px;
background:linear-gradient(90deg,#4f46e5,#06b6d4,#a855f7);
color:white;
font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">🏥 Smart Health Insurance AI System</div>', unsafe_allow_html=True)

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
            st.error("❌ Invalid login")

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

    if not df.empty:
        df["fraud_score"] = pd.to_numeric(df["fraud_score"], errors="coerce").fillna(0)

    st.sidebar.title("🏥 Smart Insurance AI")
    st.sidebar.write(f"👤 {st.session_state.email} ({st.session_state.role})")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.login = False
        st.rerun()

    # ================= ROLE MENU CONTROL =================
    if st.session_state.role == "Officer":
        menu = st.sidebar.radio("Menu",
            ["📊 Dashboard", "🕵️ Review Claims", "📍 Track Claim", "📈 Analytics"]
        )
    else:
        menu = st.sidebar.radio("Menu",
            ["📊 Dashboard", "📝 Submit Claim", "📍 Track Claim", "📈 Analytics"]
        )

    # ================= DASHBOARD =================
    if menu == "📊 Dashboard":

        st.markdown('<div class="title">📊 Dashboard Overview</div>', unsafe_allow_html=True)

        total = len(df)
        approved = len(df[df["status"] == "Approved"]) if not df.empty else 0
        rejected = len(df[df["status"] == "Rejected"]) if not df.empty else 0
        pending = len(df[df["status"] == "Pending"]) if not df.empty else 0

        c1, c2, c3, c4 = st.columns(4)

        c1.markdown(f"<div class='stat'>📄 Total<br>{total}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat'>✅ Approved<br>{approved}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat'>❌ Rejected<br>{rejected}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat'>⏳ Pending<br>{pending}</div>", unsafe_allow_html=True)

    # ================= SUBMIT CLAIM =================
    elif menu == "📝 Submit Claim":

        st.markdown('<div class="title">📝 Submit Claim</div>', unsafe_allow_html=True)

        p = st.text_input("📄 Policy Number")
        patient = st.text_input("👤 Patient Name")
        hospital = st.text_input("🏥 Hospital Name")
        treatment = st.selectbox("🏥 Treatment", ["Surgery","Cancer","Heart","Dialysis","General"])
        amount = st.number_input("💰 Claim Amount", min_value=0.0)

        uploaded_file = st.file_uploader("📷 Upload Medical Report")

        file_path, file_type = None, None

        if uploaded_file:
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())
            file_type = uploaded_file.type
            st.success("📁 File Uploaded")

        if st.button("🚀 Submit Claim"):

            score, reasons, label = ai_fraud_model(amount, 50000, hospital, treatment)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p, patient, hospital, treatment, amount,
                score, str(reasons), "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                file_path, file_type, st.session_state.email
            ))

            conn.commit()

            st.success(f"Submitted ✔ Risk: {label} ({score}%)")
            st.info("Reason: " + ", ".join(reasons))

    # ================= OFFICER PANEL =================
    elif menu == "🕵️ Review Claims":

        st.markdown('<div class="title">🕵️ Officer Panel</div>', unsafe_allow_html=True)

        if not df.empty:
            st.download_button("📥 Download Report CSV",
                               df.to_csv(index=False),
                               "claims_report.csv")

        for _, r in df.iterrows():

            score = float(r["fraud_score"])

            if score < 40:
                risk, cls = "LOW", "low"
            elif score < 70:
                risk, cls = "MEDIUM", "medium"
            else:
                risk, cls = "HIGH", "high"

            st.markdown(f"""
            <div class="card">
            <b>🆔 ID:</b> {r['claim_id']} |
            <b>👤 Patient:</b> {r['patient_name']}<br>
            <b>🏥 Hospital:</b> {r['hospital_name']}<br>
            <b>💰 Score:</b> {score}% <span class="{cls}">{risk}</span><br>
            <b>📌 Status:</b> {r['status']}<br>
            <b>🧠 Reason:</b> {r['fraud_reason']}
            </div>
            """, unsafe_allow_html=True)

            if r["status"] == "Pending":

                c1, c2 = st.columns(2)

                with c1:
                    if st.button(f"✅ Approve {r['claim_id']}", key=f"a{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",
                                    (r["claim_id"],))
                        conn.commit()
                        st.rerun()

                with c2:
                    if st.button(f"❌ Reject {r['claim_id']}", key=f"r{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",
                                    (r["claim_id"],))
                        conn.commit()
                        st.rerun()

    # ================= TRACK CLAIM =================
    elif menu == "📍 Track Claim":

        st.title("📍 Track Claim")

        cid = st.number_input("Enter Claim ID", min_value=1)

        if st.button("Search"):
            result = df[df["claim_id"] == cid]
            st.write(result if not result.empty else "❌ Not Found")

    # ================= ANALYTICS =================
    elif menu == "📈 Analytics":

        st.markdown('<div class="title">📈 Analytics Dashboard</div>', unsafe_allow_html=True)

        if not df.empty:
            st.subheader("📊 Fraud Score Distribution")
            st.bar_chart(df["fraud_score"])

            st.subheader("💰 Claim Amount Trend")
            st.line_chart(df["claim_amount"])
