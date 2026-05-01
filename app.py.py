import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Smart Insurance System", layout="wide")

# ---------------- MODERN CSS ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(56,189,248,0.25), transparent 40%),
        radial-gradient(circle at bottom right, rgba(99,102,241,0.2), transparent 40%),
        linear-gradient(135deg, #020617, #0f172a, #111827);
    color: white;
}

.main-title {
    font-size: 48px;
    font-weight: 800;
    background: linear-gradient(90deg, #38bdf8, #22d3ee, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
}

.sub-title {
    text-align: center;
    color: #cbd5e1;
    margin-bottom: 30px;
}

.card {
    background: rgba(15,23,42,0.7);
    backdrop-filter: blur(15px);
    padding: 25px;
    border-radius: 20px;
    border: 1px solid rgba(148,163,184,0.2);
    box-shadow: 0px 10px 40px rgba(0,0,0,0.4);
}

.metric-card {
    background: linear-gradient(135deg, #0284c7, #4f46e5);
    padding: 25px;
    border-radius: 20px;
    text-align: center;
    font-weight: bold;
    transition: 0.3s;
}

.metric-card:hover {
    transform: translateY(-5px);
}

.stButton button {
    background: linear-gradient(90deg, #0284c7, #2563eb);
    color: white;
    border-radius: 12px;
    padding: 10px 25px;
    font-weight: bold;
}

.stButton button:hover {
    background: linear-gradient(90deg, #0369a1, #1d4ed8);
}

[data-testid="stSidebar"] {
    background: #020617;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE ----------------
def get_conn():
    return sqlite3.connect("insurance.db", check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        email TEXT, password TEXT, role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS policies(
        policy_number TEXT, coverage_limit REAL, status TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS claims(
        claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_number TEXT, patient_name TEXT, hospital_name TEXT,
        treatment_type TEXT, claim_amount REAL,
        fraud_risk TEXT, status TEXT, submission_date TEXT
    )""")

    c.execute("""INSERT OR IGNORE INTO users VALUES
        ('hospital@gmail.com','1234','Hospital'),
        ('officer@gmail.com','1234','Insurance Officer'),
        ('user@gmail.com','1234','Policyholder')
    """)

    c.execute("""INSERT OR IGNORE INTO policies VALUES
        ('POL123',50000,'Active'),
        ('POL456',30000,'Active'),
        ('POL789',20000,'Expired')
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- FRAUD ----------------
def fraud_check(status, amount, limit):
    if status != "Active":
        return "High Risk"
    elif amount > limit:
        return "High Risk"
    elif amount > limit * 0.8:
        return "Medium Risk"
    return "Low Risk"

# ---------------- LOGIN STATE ----------------
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""

# ---------------- LOGIN PAGE ----------------
if not st.session_state.login:
    st.markdown('<div class="main-title">🏥 Smart Insurance System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Claim Processing • Fraud Detection • Tracking</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,1.2,1])

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔐 Login")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Hospital","Insurance Officer","Policyholder"])

        if st.button("Login"):
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=? AND password=? AND role=?",
                      (email,password,role))
            user = c.fetchone()
            conn.close()

            if user:
                st.session_state.login = True
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid Login")

        st.info("""
Hospital: hospital@gmail.com / 1234  
Officer: officer@gmail.com / 1234  
User: user@gmail.com / 1234
""")
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- MAIN APP ----------------
else:
    st.sidebar.title("🏥 Dashboard")
    st.sidebar.write(f"Role: {st.session_state.role}")

    menu = st.sidebar.radio("Menu",
        ["Dashboard","Submit Claim","Review Claims","Track Claim"])

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()

    # ---------------- DASHBOARD ----------------
    if menu == "Dashboard":
        st.markdown('<div class="main-title">Dashboard</div>', unsafe_allow_html=True)

        df = pd.read_sql("SELECT * FROM claims", conn)

        total = len(df)
        pending = len(df[df.status=="Pending"]) if not df.empty else 0
        approved = len(df[df.status=="Approved"]) if not df.empty else 0
        rejected = len(df[df.status=="Rejected"]) if not df.empty else 0

        c1,c2,c3,c4 = st.columns(4)

        with c1:
            st.markdown(f'<div class="metric-card">Total<br><h1>{total}</h1></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card">Pending<br><h1>{pending}</h1></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card">Approved<br><h1>{approved}</h1></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card">Rejected<br><h1>{rejected}</h1></div>', unsafe_allow_html=True)

        st.dataframe(df, use_container_width=True)

    # ---------------- SUBMIT CLAIM ----------------
    elif menu == "Submit Claim":
        if st.session_state.role != "Hospital":
            st.warning("Only Hospital can submit")
        else:
            st.markdown('<div class="main-title">Submit Claim</div>', unsafe_allow_html=True)

            policy = st.text_input("Policy Number")
            name = st.text_input("Patient Name")
            hospital = st.text_input("Hospital Name")
            type = st.selectbox("Treatment", ["Surgery","Emergency","Other"])
            amount = st.number_input("Amount", min_value=0.0)

            if st.button("Submit"):
                c = conn.cursor()
                c.execute("SELECT coverage_limit,status FROM policies WHERE policy_number=?",(policy,))
                p = c.fetchone()

                if p:
                    limit,status = p
                    risk = fraud_check(status,amount,limit)
                    stat = "Rejected" if status!="Active" else "Pending"

                    c.execute("""INSERT INTO claims
                    (policy_number,patient_name,hospital_name,treatment_type,
                    claim_amount,fraud_risk,status,submission_date)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (policy,name,hospital,type,amount,risk,stat,str(datetime.now())))

                    conn.commit()
                    st.success(f"Submitted! Risk: {risk}")
                else:
                    st.error("Invalid Policy")

    # ---------------- OFFICER ----------------
    elif menu == "Review Claims":
        if st.session_state.role != "Insurance Officer":
            st.warning("Only Officer")
        else:
            df = pd.read_sql("SELECT * FROM claims", conn)
            st.dataframe(df)

            cid = st.number_input("Claim ID", min_value=1)

            if st.button("Approve"):
                conn.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",(cid,))
                conn.commit()
                st.success("Approved")

            if st.button("Reject"):
                conn.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",(cid,))
                conn.commit()
                st.error("Rejected")

    # ---------------- TRACK ----------------
    elif menu == "Track Claim":
        cid = st.number_input("Claim ID", min_value=1)

        if st.button("Check"):
            c = conn.cursor()
            c.execute("SELECT * FROM claims WHERE claim_id=?",(cid,))
            r = c.fetchone()

            if r:
                st.success(f"Status: {r[7]} | Risk: {r[6]}")
            else:
                st.error("Not found")

    conn.close()
