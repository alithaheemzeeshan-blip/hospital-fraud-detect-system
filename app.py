import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import os

# ================= PAGE =================
st.set_page_config(page_title="Insurance AI System", layout="wide")

# ================= RESET DB =================
if os.path.exists("insurance.db"):
    os.remove("insurance.db")

# ================= DB =================
def get_conn():
    return sqlite3.connect("insurance.db", check_same_thread=False)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ================= INIT DB =================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        email TEXT,
        password TEXT,
        role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS policies (
        policy_number TEXT,
        policyholder_name TEXT,
        coverage_limit REAL,
        status TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS claims (
        claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_number TEXT,
        patient_name TEXT,
        hospital_name TEXT,
        treatment_type TEXT,
        claim_amount REAL,
        fraud_score REAL,
        fraud_reason TEXT,
        status TEXT,
        submission_date TEXT
    )""")

    users = [
        ("hospital@gmail.com", hash_password("hospital123"), "Hospital"),
        ("officer@gmail.com", hash_password("officer123"), "Officer"),
        ("user@gmail.com", hash_password("user123"), "Policyholder"),
    ]

    c.executemany("INSERT INTO users VALUES (?,?,?)", users)

    conn.commit()
    conn.close()

init_db()

# ================= FRAUD ENGINE + EXPLANATION =================
def fraud_analyze(status, amount, limit):
    score = 0
    reasons = []

    # Rule 1
    if status != "Active":
        score += 45
        reasons.append("Policy is not active")

    # Rule 2
    if amount > limit:
        score += 35
        reasons.append("Claim exceeds coverage limit")

    # Rule 3
    if amount > limit * 0.8:
        score += 15
        reasons.append("High utilization (above 80% of coverage)")

    if not reasons:
        reasons.append("No anomaly detected")

    score = min(score, 100)

    return score, ", ".join(reasons)

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""

# ================= UI STYLE =================
st.markdown("""
<style>
.main-title{
    text-align:center;
    font-size:40px;
    font-weight:800;
    color:#38bdf8;
}

.card{
    background:#0f172a;
    padding:20px;
    border-radius:15px;
    margin-bottom:10px;
    box-shadow:0px 0px 10px rgba(56,189,248,0.2);
}

.good{color:#22c55e;}
.bad{color:#ef4444;}
.warn{color:#f59e0b;}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:
    st.markdown('<div class="main-title">Insurance Fraud AI System</div>', unsafe_allow_html=True)

    email = st.text_input("Email")
    pw = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Hospital", "Officer", "Policyholder"])

    if st.button("Login"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=? AND role=?",
                  (email, hash_password(pw), role))
        user = c.fetchone()
        conn.close()

        if user:
            st.session_state.login = True
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid Login")

# ================= MAIN APP =================
else:
    st.sidebar.title("AI Insurance System")
    menu = st.sidebar.radio("Menu", ["Dashboard", "Submit Claim", "Review Claims", "Track Claim"])

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.markdown("## 📊 Claims Overview")

        df = pd.read_sql("SELECT * FROM claims", conn)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(df))
        col2.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)
        col3.metric("Safe", len(df[df["fraud_score"] <= 40]) if not df.empty else 0)

        for _, row in df.iterrows():
            color = "bad" if row["fraud_score"] > 70 else "warn" if row["fraud_score"] > 40 else "good"

            st.markdown(f"""
            <div class="card">
                <b>Claim ID:</b> {row['claim_id']}<br>
                <b>Policy:</b> {row['policy_number']}<br>
                <b>Amount:</b> {row['claim_amount']}<br>
                <b>Fraud Score:</b> <span class="{color}">{row['fraud_score']}</span><br>
                <b>Reason:</b> {row['fraud_reason']}<br>
                <b>Status:</b> {row['status']}
            </div>
            """, unsafe_allow_html=True)

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":
        if st.session_state.role != "Hospital":
            st.warning("Access Denied")
        else:
            st.title("Submit Claim")

            with st.form("claim"):
                p = st.text_input("Policy Number")
                n = st.text_input("Patient Name")
                h = st.text_input("Hospital")
                t = st.text_input("Treatment")
                a = st.number_input("Amount", min_value=0.0)

                submit = st.form_submit_button("Submit")

                if submit:
                    cur = conn.cursor()
                    cur.execute("SELECT coverage_limit,status FROM policies WHERE policy_number=?",(p,))
                    pol = cur.fetchone()

                    if pol:
                        limit, status = pol
                    else:
                        limit, status = 0, "Unknown"

                    score, reason = fraud_analyze(status, a, limit)

                    status_final = "Rejected" if score > 70 else "Pending Review"

                    cur.execute("""
                        INSERT INTO claims(policy_number,patient_name,hospital_name,
                        treatment_type,claim_amount,fraud_score,fraud_reason,status,submission_date)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """,(p,n,h,t,a,score,reason,status_final,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    conn.commit()
                    st.success("Claim Submitted")

                    st.info(f"Fraud Score: {score}")
                    st.warning(f"Reason: {reason}")

    # ================= REVIEW =================
    elif menu == "Review Claims":
        st.title("Officer Review")

        df = pd.read_sql("SELECT * FROM claims", conn)
        st.dataframe(df)

        cid = st.number_input("Claim ID",1)

        if st.button("Approve"):
            conn.execute("UPDATE claims SET status='Approved' WHERE claim_id=?", (cid,))
            conn.commit()
            st.success("Approved")

        if st.button("Reject"):
            conn.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?", (cid,))
            conn.commit()
            st.error("Rejected")

    # ================= TRACK =================
    elif menu == "Track Claim":
        st.title("Track Claim")

        cid = st.number_input("Claim ID",1)

        if st.button("Check"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            if r:
                st.json(r)
            else:
                st.error("Not Found")

    conn.close()
