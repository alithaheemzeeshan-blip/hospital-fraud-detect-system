import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import os

# ================= PAGE =================
st.set_page_config(page_title="AI Insurance System", layout="wide")

# ================= DB RESET =================
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

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        email TEXT,
        password TEXT,
        role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS policies(
        policy_number TEXT,
        policyholder_name TEXT,
        coverage_limit REAL,
        status TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS claims(
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

# ================= FRAUD =================
def fraud_analyze(status, amount, limit):
    score = 0
    reasons = []

    if status != "Active":
        score += 45
        reasons.append("Policy inactive")

    if amount > limit:
        score += 35
        reasons.append("Exceeds coverage limit")

    if amount > limit * 0.8:
        score += 15
        reasons.append("High utilization")

    return min(score, 100), ", ".join(reasons) if reasons else "Normal"

# ================= STYLE =================
st.markdown("""
<style>

.main-title{
    font-size:45px;
    text-align:center;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#0072ff,#ff00cc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.subtitle{
    text-align:center;
    color:#94a3b8;
    margin-bottom:20px;
}

/* CARD */
.card{
    background: linear-gradient(135deg,#0f172a,#1e293b);
    padding:18px;
    border-radius:18px;
    margin-bottom:12px;
    box-shadow:0px 0px 15px rgba(0,198,255,0.2);
    border:1px solid rgba(255,255,255,0.08);
}

/* BUTTON */
.stButton>button{
    background: linear-gradient(90deg,#ff00cc,#3333ff,#00c6ff);
    color:white;
    border-radius:12px;
    padding:10px 18px;
    font-weight:600;
    border:none;
    transition:0.3s;
}

.stButton>button:hover{
    transform:scale(1.05);
    box-shadow:0px 0px 15px rgba(0,198,255,0.5);
}

/* SIDEBAR */
section[data-testid="stSidebar"]{
    background: linear-gradient(180deg,#0f172a,#111827);
}

</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""

if not st.session_state.login:

    st.markdown('<div class="main-title">🏥 AI Insurance Fraud System</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Smart • Fast • Colorful • Fraud Detection Engine</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown("### 🔐 Login Portal")

        email = st.text_input("📧 Email")
        password = st.text_input("🔑 Password", type="password")
        role = st.selectbox("👤 Role", ["Hospital", "Officer", "Policyholder"])

        if st.button("🚀 LOGIN NOW"):
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=? AND password=? AND role=?",
                      (email, hash_password(password), role))
            user = c.fetchone()

            if user:
                st.session_state.login = True
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid credentials")

        st.info("Demo:\nhospital@gmail.com / hospital123\nofficer@gmail.com / officer123\nuser@gmail.com / user123")

# ================= MAIN =================
else:

    st.sidebar.title("⚡ AI Insurance Panel")
    st.sidebar.success(f"Logged in as: {st.session_state.role}")

    menu = st.sidebar.radio("Navigate",
        ["🏠 Dashboard", "➕ Submit Claim", "🧑‍💼 Review", "🔎 Track"])

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "🏠 Dashboard":
        st.markdown('<div class="main-title">Dashboard</div>', unsafe_allow_html=True)

        df = pd.read_sql("SELECT * FROM claims", conn)

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Claims", len(df))
        c2.metric("High Risk", len(df[df["fraud_score"]>70]) if not df.empty else 0)
        c3.metric("Safe", len(df[df["fraud_score"]<=40]) if not df.empty else 0)

        st.markdown("### 📊 Latest Claims")

        for _, r in df.iterrows():
            color = "🔴" if r["fraud_score"]>70 else "🟡" if r["fraud_score"]>40 else "🟢"

            st.markdown(f"""
            <div class="card">
                {color} <b>Claim ID:</b> {r['claim_id']} <br>
                <b>Policy:</b> {r['policy_number']} <br>
                <b>Amount:</b> ${r['claim_amount']} <br>
                <b>Fraud Score:</b> {r['fraud_score']} <br>
                <b>Reason:</b> {r['fraud_reason']} <br>
                <b>Status:</b> {r['status']}
            </div>
            """, unsafe_allow_html=True)

    # ================= SUBMIT =================
    elif menu == "➕ Submit Claim":
        st.title("Submit Claim")

        if st.session_state.role != "Hospital":
            st.warning("Access Denied")
        else:
            with st.form("claim"):
                p = st.text_input("Policy Number")
                n = st.text_input("Patient Name")
                h = st.text_input("Hospital Name")
                t = st.text_input("Treatment Type")
                a = st.number_input("Claim Amount", min_value=0.0)

                submit = st.form_submit_button("🚀 Submit Claim")

                if submit:
                    cur = conn.cursor()
                    cur.execute("SELECT coverage_limit,status FROM policies WHERE policy_number=?",(p,))
                    pol = cur.fetchone()

                    if pol:
                        limit, status = pol
                    else:
                        limit, status = 0, "Unknown"

                    score, reason = fraud_analyze(status,a,limit)

                    status_final = "Rejected" if score > 70 else "Pending"

                    cur.execute("""
                        INSERT INTO claims VALUES(NULL,?,?,?,?,?,?,?,?,?)
                    """,(p,n,h,t,a,score,reason,status_final,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    conn.commit()
                    st.success("Claim Submitted Successfully 🎉")

    # ================= REVIEW =================
    elif menu == "🧑‍💼 Review":
        st.title("Officer Review Panel")

        df = pd.read_sql("SELECT * FROM claims", conn)
        st.dataframe(df, use_container_width=True)

        cid = st.number_input("Claim ID",1)

        col1, col2 = st.columns(2)

        if col1.button("✅ Approve"):
            conn.execute("UPDATE claims SET status='Approved' WHERE claim_id=?", (cid,))
            conn.commit()
            st.success("Approved")

        if col2.button("❌ Reject"):
            conn.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?", (cid,))
            conn.commit()
            st.error("Rejected")

    # ================= TRACK =================
    elif menu == "🔎 Track":
        st.title("Track Claim")

        cid = st.number_input("Claim ID",1)

        if st.button("Search 🔍"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            if r:
                st.json(r)
            else:
                st.error("Not Found")

    conn.close()
