import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import os

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Smart Insurance Pro", layout="wide")

# ================= DB RESET (CLEAN RUN) =================
if os.path.exists("insurance.db"):
    os.remove("insurance.db")

# ================= CONNECTION =================
def get_conn():
    return sqlite3.connect("insurance.db", check_same_thread=False)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ================= INIT DB =================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT,
        role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS policies (
        policy_number TEXT PRIMARY KEY,
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
        fraud_risk REAL,
        status TEXT,
        submission_date TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        performed_by TEXT,
        claim_id INTEGER,
        timestamp TEXT
    )""")

    # ================= USERS (LOGIN WORKING) =================
    users = [
        ("hospital@gmail.com", hash_password("hospital123"), "Hospital"),
        ("officer@gmail.com", hash_password("officer123"), "Insurance Officer"),
        ("user@gmail.com", hash_password("user123"), "Policyholder"),
    ]

    c.executemany("INSERT INTO users VALUES (NULL,?,?,?)", users)

    conn.commit()
    conn.close()

init_db()

# ================= FRAUD =================
def fraud_score(status, amount, limit):
    score = 0
    if status != "Active":
        score += 40
    if amount > limit:
        score += 35
    if amount > limit * 0.9:
        score += 15
    return min(score, 100)

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""

# ================= CUSTOM CSS =================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #0f172a, #1e293b);
}

.big-title {
    text-align:center;
    font-size:42px;
    font-weight:800;
    color:#38bdf8;
    margin-bottom:10px;
}

.sub {
    text-align:center;
    color:#94a3b8;
    margin-bottom:30px;
}

.login-box {
    background:#0f172a;
    padding:30px;
    border-radius:20px;
    box-shadow:0px 0px 20px rgba(56,189,248,0.3);
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="big-title">🏥 Smart Insurance System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">Secure • Fast • Fraud Detection Enabled</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)

        email = st.text_input("📧 Email")
        password = st.text_input("🔑 Password", type="password")
        role = st.selectbox("👤 Role", ["Hospital", "Insurance Officer", "Policyholder"])

        if st.button("Login 🚀"):
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=? AND password=? AND role=?",
                      (email, hash_password(password), role))
            user = c.fetchone()
            conn.close()

            if user:
                st.session_state.login = True
                st.session_state.role = role
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid Credentials")

        st.markdown("### 🔐 Demo Login")
        st.info("hospital@gmail.com / hospital123\nofficer@gmail.com / officer123\nuser@gmail.com / user123")

        st.markdown('</div>', unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("🏥 Insurance Pro")
    st.sidebar.success(f"Role: {st.session_state.role}")

    menu = st.sidebar.radio("Navigation",
        ["Dashboard", "Submit Claim", "Review Claims", "Track Claim", "Audit Log"])

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.markdown("## 📊 Dashboard Overview")

        df = pd.read_sql("SELECT * FROM claims", conn)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Claims", len(df))
        col2.metric("Approved", len(df[df["status"]=="Approved"]) if not df.empty else 0)
        col3.metric("Rejected", len(df[df["status"]=="Rejected"]) if not df.empty else 0)

        st.dataframe(df, use_container_width=True)

    # ================= SUBMIT =================
    elif menu == "Submit Claim":
        st.title("📝 Submit Claim")

        if st.session_state.role != "Hospital":
            st.warning("Access Denied")
        else:
            with st.form("claim"):
                p = st.text_input("Policy Number")
                n = st.text_input("Patient Name")
                h = st.text_input("Hospital Name")
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

                    risk = fraud_score(status,a,limit)
                    status_final = "Rejected" if risk > 70 else "Pending Review"

                    cur.execute("""
                        INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?)
                    """,(p,n,h,t,a,risk,status_final,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    conn.commit()
                    st.success("Claim Submitted")

    # ================= REVIEW =================
    elif menu == "Review Claims":
        st.title("🧑‍💼 Review")

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
        st.title("🔎 Track")

        cid = st.number_input("Claim ID",1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            if r:
                st.write(r)
            else:
                st.error("Not found")

    # ================= AUDIT =================
    elif menu == "Audit Log":
        st.title("📜 Logs")

        df = pd.read_sql("SELECT * FROM audit_log", conn)
        st.dataframe(df)

    conn.close()
