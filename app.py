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

# ================= FRAUD MODEL =================
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
    font-size:34px;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#ff00cc,#22c55e);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.card {
    padding:12px;
    margin:8px 0;
    border-radius:12px;
    background: rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.1);
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

    st.markdown('<div class="card">🔐 Login to access your dashboard</div>', unsafe_allow_html=True)

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
    ### 🔑 Demo Login Credentials

    🏥 **Hospital**
    - 📧 hospital@gmail.com
    - 🔑 hospital123

    🕵️ **Officer**
    - 📧 officer@gmail.com
    - 🔑 officer123

    👨‍⚕️ **Policyholder**
    - 📧 user@gmail.com
    - 🔑 user123
    """)

# ================= MAIN APP =================
else:

    st.sidebar.title("🏥 Insurance System")
    st.sidebar.write(st.session_state.email)

    if st.sidebar.button("🚪 Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    if st.session_state.role == "Officer":
        menu = st.sidebar.radio("Menu",
            ["Dashboard", "Review Claims", "Track Claim", "Analytics"])
    else:
        menu = st.sidebar.radio("Menu",
            ["Dashboard", "Submit Claim", "Track Claim", "Analytics"])

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.title("📊 Dashboard")

        st.metric("📄 Total Claims", len(df))
        st.metric("⚠️ High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":

        st.title("📝 Submit Claim")

        p = st.text_input("📄 Policy Number")
        patient = st.text_input("👤 Patient Name")
        hospital = st.text_input("🏥 Hospital Name")

        treatment = st.selectbox(
            "🏥 Treatment Type",
            [
                "General Checkup",
                "Emergency Treatment",
                "Surgery",
                "Heart Surgery",
                "Cancer Treatment",
                "Dialysis",
                "Maternity Care",
                "Dental Treatment",
                "Eye Surgery",
                "Orthopedic Surgery",
                "Physiotherapy",
                "COVID-19 Treatment",
                "Neurology Treatment",
                "Skin Treatment",
                "ENT Treatment",
                "Other"
            ]
        )

        amount = st.number_input("💰 Claim Amount", min_value=0.0)

        if st.button("📤 Submit Claim"):

            score, reason = ai_fraud_model(amount, 50000, hospital)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p,
                patient,
                hospital,
                treatment,
                amount,
                score,
                reason,
                "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                None,
                None,
                st.session_state.email
            ))

            conn.commit()
            st.success("✅ Claim Submitted Successfully")

    # ================= REVIEW CLAIMS =================
    elif menu == "Review Claims":

        st.title("🕵️ Officer Panel")

        for _, r in df.iterrows():

            score = r["fraud_score"]

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
                <b>Risk Score:</b> {score}% |
                <span class="{cls}">{risk} RISK</span><br>
                <b>Reason:</b> {r['fraud_reason']}<br>
                <b>Status:</b> {r['status']}
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
