import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import plotly.express as px

# ================= PAGE =================
st.set_page_config(page_title="Smart Insurance Pro", layout="wide")

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
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
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

    # demo users
    c.execute("""
    INSERT OR IGNORE INTO users (email, password, role)
    VALUES
    ('hospital@gmail.com', ?, 'Hospital'),
    ('officer@gmail.com', ?, 'Insurance Officer'),
    ('user@gmail.com', ?, 'Policyholder')
    """, (hash_password("1234"), hash_password("1234"), hash_password("1234")))

    # demo policies
    c.execute("""
    INSERT OR IGNORE INTO policies VALUES
    ('POL123','Ali Khan',50000,'Active'),
    ('POL456','Sara Ahmed',30000,'Active'),
    ('POL789','Usman Ali',20000,'Expired')
    """)

    conn.commit()
    conn.close()

init_db()

# ================= FRAUD ENGINE =================
def fraud_score(status, amount, limit, hospital):
    score = 0

    if status != "Active":
        score += 40
    if amount > limit:
        score += 35
    if amount > limit * 0.9:
        score += 15
    if "unknown" in hospital.lower():
        score += 20

    return min(score, 100)

# ================= LOGGING =================
def log(action, user, cid):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO audit_log(action,performed_by,claim_id,timestamp)
        VALUES(?,?,?,?)
    """, (action, user, cid, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""

# ================= LOGIN =================
if not st.session_state.login:
    st.title("🏥 Smart Insurance System")

    email = st.text_input("Email")
    pw = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Hospital", "Insurance Officer", "Policyholder"])

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
            st.error("Invalid login")

# ================= APP =================
else:
    st.sidebar.title("🏥 Insurance System")
    st.sidebar.write(f"Role: {st.session_state.role}")

    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Submit Claim", "Review Claims", "Track Claim", "Analytics", "Audit Log"]
    )

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.title("📊 Dashboard")

        df = pd.read_sql("SELECT * FROM claims", conn)

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Claims", len(df))
        col2.metric("Approved", len(df[df["status"]=="Approved"]) if not df.empty else 0)
        col3.metric("Rejected", len(df[df["status"]=="Rejected"]) if not df.empty else 0)

        st.dataframe(df)

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":
        if st.session_state.role != "Hospital":
            st.warning("Only Hospital users allowed")
        else:
            st.title("📝 Submit Claim")

            with st.form("claim"):
                p = st.text_input("Policy Number")
                n = st.text_input("Patient Name")
                h = st.text_input("Hospital Name")
                t = st.selectbox("Treatment", ["Surgery","Medicine","Emergency"])
                a = st.number_input("Claim Amount", min_value=0.0)

                submit = st.form_submit_button("Submit")

                if submit:
                    cur = conn.cursor()
                    cur.execute("SELECT coverage_limit,status FROM policies WHERE policy_number=?",(p,))
                    pol = cur.fetchone()

                    if pol:
                        limit, status = pol
                    else:
                        limit, status = 0, "Unknown"

                    risk = fraud_score(status,a,limit,h)

                    if risk > 70:
                        staus = "Rejected"
                    elif risk > 40:
                        staus = "Pending Review"
                    else:
                        staus = "Pending"

                    cur.execute("""
                        INSERT INTO claims
                        (policy_number,patient_name,hospital_name,treatment_type,
                        claim_amount,fraud_risk,status,submission_date)
                        VALUES (?,?,?,?,?,?,?,?)
                    """,(p,n,h,t,a,risk,staus,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    conn.commit()
                    st.success("Claim Submitted Successfully")

    # ================= REVIEW =================
    elif menu == "Review Claims":
        if st.session_state.role != "Insurance Officer":
            st.warning("Only Officers allowed")
        else:
            st.title("🧑‍💼 Review Claims")

            df = pd.read_sql("SELECT * FROM claims", conn)
            st.dataframe(df)

            cid = st.number_input("Claim ID", 1)

            if st.button("Approve"):
                conn.execute("UPDATE claims SET status='Approved' WHERE claim_id=?", (cid,))
                log("Approved", st.session_state.role, cid)
                conn.commit()

            if st.button("Reject"):
                conn.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?", (cid,))
                log("Rejected", st.session_state.role, cid)
                conn.commit()

    # ================= TRACK =================
    elif menu == "Track Claim":
        st.title("🔎 Track Claim")

        cid = st.number_input("Claim ID", 1)

        if st.button("Check"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            if r:
                st.write(r)
            else:
                st.error("Not Found")

    # ================= ANALYTICS =================
    elif menu == "Analytics":
        st.title("📊 Analytics")

        df = pd.read_sql("SELECT * FROM claims", conn)

        if not df.empty:
            fig1 = px.bar(df, x="status", color="status", title="Claim Status Distribution")
            st.plotly_chart(fig1, use_container_width=True)

            fig2 = px.scatter(df, x="claim_amount", y="fraud_risk", color="status",
                              title="Fraud vs Claim Amount")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data available")

    # ================= AUDIT =================
    elif menu == "Audit Log":
        st.title("📜 Audit Logs")

        df = pd.read_sql("SELECT * FROM audit_log", conn)
        st.dataframe(df)

    conn.close()
