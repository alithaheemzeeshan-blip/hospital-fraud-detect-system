import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

# ================= CONFIG =================
st.set_page_config(page_title="AI Health Insurance System", layout="wide")

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

# ================= AI FRAUD =================
def ai_fraud_model(amount, limit, hospital):
    score = 0
    reason = []

    if amount > limit:
        score += 40
        reason.append("Over limit")

    if amount > 50000:
        score += 20
        reason.append("High amount")

    if "unknown" in hospital.lower():
        score += 15
        reason.append("Unverified hospital")

    return min(score, 100), ", ".join(reason)

# ================= AI DECISION =================
def ai_decision(score):
    if score >= 75:
        return "Rejected", "High risk"
    elif score >= 40:
        return "Review", "Medium risk"
    else:
        return "Approved", "Low risk"

# ================= EMAIL SIM =================
def send_email(to, subject, msg):
    st.info(f"""
📧 EMAIL SENT (SIMULATION)

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
        patient TEXT,
        hospital TEXT,
        treatment TEXT,
        amount REAL,
        fraud_score REAL,
        reason TEXT,
        status TEXT,
        date TEXT,
        file TEXT,
        type TEXT,
        submitted_by TEXT
    )
    """)

    conn.commit()

    # safe migration
    try:
        c.execute("ALTER TABLE claims ADD COLUMN submitted_by TEXT")
    except:
        pass

    # demo users
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

# ================= STYLE =================
st.markdown("""
<style>
.title{
text-align:center;
font-size:40px;
font-weight:bold;
background:linear-gradient(90deg,#00c6ff,#7a00ff);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
}

.card{
background:rgba(255,255,255,0.05);
padding:12px;
border-radius:12px;
margin:10px 0;
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">AI Insurance System</div>', unsafe_allow_html=True)

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
    ### Demo Accounts
    Hospital: hospital@gmail.com / hospital123  
    Officer: officer@gmail.com / officer123  
    Policyholder: user@gmail.com / user123
    """)

# ================= MAIN APP =================
else:

    st.sidebar.title("Insurance System")
    st.sidebar.write(st.session_state.email)
    st.sidebar.write(st.session_state.role)

    # 🚪 LOGOUT FIXED
    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    # ================= ROLE MENUS =================
    if st.session_state.role == "Policyholder":
        menu = st.sidebar.radio("Menu",
            ["Dashboard", "Submit Claim", "My Claims", "Track", "Analytics"])

    elif st.session_state.role == "Hospital":
        menu = st.sidebar.radio("Menu",
            ["Dashboard", "Submit Claim", "Review Claims", "Analytics"])

    else:  # Officer
        menu = st.sidebar.radio("Menu",
            ["Dashboard", "Review Claims", "Officer Analytics", "Track", "Analytics"])

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.title("Dashboard")
        df = pd.read_sql("SELECT * FROM claims", conn)
        st.metric("Total Claims", len(df))

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":

        st.title("Submit Claim")

        p = st.text_input("Policy")
        patient = st.text_input("Patient")
        hospital = st.text_input("Hospital")
        treatment = st.text_input("Treatment")
        amount = st.number_input("Amount", 0.0)

        if st.button("Submit"):

            score, reason = ai_fraud_model(amount, 50000, hospital)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p, patient, hospital, treatment, amount,
                score, reason,
                "Pending",
                datetime.now().strftime("%Y-%m-%d"),
                None, None,
                st.session_state.email
            ))

            conn.commit()
            st.success("Claim Submitted")

    # ================= REVIEW CLAIMS =================
    elif menu == "Review Claims":

        st.title("Officer Review")

        df = pd.read_sql("SELECT * FROM claims", conn)

        for _, r in df.iterrows():

            st.markdown(f"""
            <div class="card">
            ID: {r['claim_id']} | Score: {r['fraud_score']} | Status: {r['status']}
            </div>
            """, unsafe_allow_html=True)

            if r["status"] == "Pending":

                decision, msg = ai_decision(r["fraud_score"])

                st.write("AI Suggestion:", decision, msg)

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(f"Approve {r['claim_id']}", key=f"a{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",(r['claim_id'],))
                        conn.commit()
                        send_email(r.get("submitted_by","user"),"Approved","Claim Approved")
                        st.rerun()

                with col2:
                    if st.button(f"Reject {r['claim_id']}", key=f"r{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",(r['claim_id'],))
                        conn.commit()
                        send_email(r.get("submitted_by","user"),"Rejected","Claim Rejected")
                        st.rerun()

                with col3:
                    if st.button(f"Auto {r['claim_id']}", key=f"auto{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status=? WHERE claim_id=?",
                                    (decision, r['claim_id']))
                        conn.commit()
                        st.rerun()

    # ================= MY CLAIMS =================
    elif menu == "My Claims":

        st.title("My Claims")

        df = pd.read_sql("SELECT * FROM claims", conn)

        my = df[df["submitted_by"] == st.session_state.email]

        st.dataframe(my)

    # ================= OFFICER ANALYTICS =================
    elif menu == "Officer Analytics":

        st.title("Officer Analytics")

        df = pd.read_sql("SELECT * FROM claims", conn)

        st.metric("Approved", len(df[df["status"]=="Approved"]))
        st.metric("Rejected", len(df[df["status"]=="Rejected"]))
        st.metric("Pending", len(df[df["status"]=="Pending"]))

        st.bar_chart(df["fraud_score"])

    # ================= TRACK =================
    elif menu == "Track":

        st.title("Track Claim")

        cid = st.number_input("ID", 1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?",(cid,))
            st.write(cur.fetchone())

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("Analytics")

        df = pd.read_sql("SELECT * FROM claims", conn)

        st.bar_chart(df["fraud_score"])
        st.line_chart(df["amount"])
