import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import random
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Smart Health Insurance System", layout="centered")

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

# ================= SMART AI FRAUD MODEL =================
def ai_fraud_model(amount, limit, hospital, treatment):

    score = 0
    reasons = []

    # Amount risk
    if amount <= 5000:
        score += 5
    elif amount <= 20000:
        score += 15
    elif amount <= 50000:
        score += 30
        reasons.append("Moderate-high claim amount")
    else:
        score += 50
        reasons.append("Very high claim amount")

    # Limit check
    if amount > limit:
        score += 25
        reasons.append("Exceeds policy limit")

    # Hospital risk
    bad_hospitals = ["unknown", "fake", "clinic", "small"]
    if any(x in hospital.lower() for x in bad_hospitals):
        score += 20
        reasons.append("Suspicious hospital")

    # Treatment risk
    high_risk = ["surgery", "cancer", "heart", "dialysis"]
    if any(t in treatment.lower() for t in high_risk):
        score += 20
    else:
        score += 5

    # randomness (real-world uncertainty)
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
body {background: #0f172a; color:white;}
.title {text-align:center;font-size:34px;font-weight:900;
background:linear-gradient(90deg,#00c6ff,#ff00cc,#22c55e);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;}

.card {
padding:12px;margin:10px 0;border-radius:12px;
background:rgba(255,255,255,0.07);
}

.low{color:#22c55e;font-weight:700;}
.medium{color:#facc15;font-weight:700;}
.high{color:#ef4444;font-weight:700;}

.stButton>button{
background:linear-gradient(90deg,#4f46e5,#06b6d4,#a855f7);
color:white;font-weight:700;width:100%;
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">🏥 Smart Health Insurance AI System</div>', unsafe_allow_html=True)

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

    st.markdown("---")
    st.markdown("""
### Demo Logins
Hospital: hospital@gmail.com / hospital123  
Officer: officer@gmail.com / officer123  
User: user@gmail.com / user123  
""")

# ================= MAIN =================
else:

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    if not df.empty:
        df["fraud_score"] = pd.to_numeric(df["fraud_score"], errors="coerce").fillna(0)

    st.sidebar.write(f"Logged in: {st.session_state.email}")
    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    menu = st.sidebar.radio("Menu",
        ["Dashboard", "Submit Claim", "Review Claims", "Track Claim", "Analytics"]
    )

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.markdown('<div class="title">Dashboard</div>', unsafe_allow_html=True)

        total = len(df)
        approved = len(df[df["status"] == "Approved"]) if not df.empty else 0
        rejected = len(df[df["status"] == "Rejected"]) if not df.empty else 0
        pending = len(df[df["status"] == "Pending"]) if not df.empty else 0

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total", total)
        c2.metric("Approved", approved)
        c3.metric("Rejected", rejected)
        c4.metric("Pending", pending)

    # ================= SUBMIT =================
    elif menu == "Submit Claim":

        st.title("Submit Claim")

        p = st.text_input("Policy No")
        patient = st.text_input("Patient Name")
        hospital = st.text_input("Hospital")
        treatment = st.selectbox("Treatment", ["Surgery","Cancer","Heart","Dialysis","General"])
        amount = st.number_input("Amount", min_value=0.0)

        if st.button("Submit"):

            score, reasons, label = ai_fraud_model(amount, 50000, hospital, treatment)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p, patient, hospital, treatment, amount,
                score, str(reasons), "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                None, None, st.session_state.email
            ))

            conn.commit()

            st.success(f"Submitted! Risk: {label} ({score}%)")
            st.info("Reasons: " + ", ".join(reasons))

    # ================= OFFICER =================
    elif menu == "Review Claims":

        st.title("Officer Panel")

        if not df.empty:
            st.download_button(
                "📥 Download Report CSV",
                df.to_csv(index=False),
                "claims_report.csv"
            )

        for _, r in df.iterrows():

            score = float(r["fraud_score"])

            if score < 40:
                risk = "LOW"
                color = "low"
            elif score < 70:
                risk = "MEDIUM"
                color = "medium"
            else:
                risk = "HIGH"
                color = "high"

            st.markdown(f"""
            <div class="card">
            <b>ID:</b> {r['claim_id']} |
            <b>Patient:</b> {r['patient_name']}<br>
            <b>Score:</b> {score}% <span class="{color}">{risk}</span><br>
            <b>Reason:</b> {r['fraud_reason']}<br>
            <b>Status:</b> {r['status']}
            </div>
            """, unsafe_allow_html=True)

            if r["status"] == "Pending":

                c1,c2 = st.columns(2)

                with c1:
                    if st.button(f"Approve {r['claim_id']}", key=f"a{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",
                                    (r["claim_id"],))
                        conn.commit()
                        st.rerun()

                with c2:
                    if st.button(f"Reject {r['claim_id']}", key=f"r{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",
                                    (r["claim_id"],))
                        conn.commit()
                        st.rerun()

    # ================= TRACK =================
    elif menu == "Track Claim":

        st.title("Track Claim")

        cid = st.number_input("Claim ID", min_value=1)

        if st.button("Search"):
            r = df[df["claim_id"] == cid]
            st.write(r if not r.empty else "Not found")

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("Analytics")

        if not df.empty:
            st.subheader("Fraud Score Distribution")
            st.bar_chart(df["fraud_score"])

            st.subheader("Claim Amount Trend")
            st.line_chart(df["claim_amount"])
