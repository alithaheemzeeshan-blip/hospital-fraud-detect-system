import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import os

# ================= PAGE =================
st.set_page_config(page_title="Insurance System", layout="wide")

# ================= RESET DB (CLOUD SAFE) =================
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        policy_number TEXT PRIMARY KEY,
        policyholder_name TEXT,
        coverage_limit REAL,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_number TEXT,
        patient_name TEXT,
        hospital_name TEXT,
        treatment_type TEXT,
        claim_amount REAL,
        fraud_risk REAL,
        status TEXT,
        submission_date TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        performed_by TEXT,
        claim_id INTEGER,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= FRAUD SCORE =================
def fraud_score(status, amount, limit):
    score = 0

    if status != "Active":
        score += 40
    if amount > limit:
        score += 35
    if amount > limit * 0.9:
        score += 15

    return min(score, 100)

# ================= LOG =================
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
    st.title("Insurance System Login")

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
    st.sidebar.title("Menu")
    st.sidebar.write("Role:", st.session_state.role)

    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Add Policy", "Submit Claim", "Review Claims", "Track Claim", "Audit Log"]
    )

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.title("Dashboard")

        df = pd.read_sql("SELECT * FROM claims", conn)

        st.metric("Total Claims", len(df))
        st.dataframe(df)

    # ================= ADD POLICY =================
    elif menu == "Add Policy":
        st.title("Add Policy (Input Only)")

        with st.form("policy"):
            p = st.text_input("Policy Number")
            n = st.text_input("Policyholder Name")
            l = st.number_input("Coverage Limit", min_value=0.0)
            s = st.selectbox("Status", ["Active", "Expired"])

            submit = st.form_submit_button("Save")

            if submit:
                conn.execute("""
                    INSERT OR IGNORE INTO policies
                    VALUES (?,?,?,?)
                """, (p, n, l, s))

                conn.commit()
                st.success("Policy Added")

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":
        if st.session_state.role != "Hospital":
            st.warning("Not allowed")
        else:
            st.title("Submit Claim")

            with st.form("claim"):
                p = st.text_input("Policy Number")
                n = st.text_input("Patient Name")
                h = st.text_input("Hospital Name")
                t = st.text_input("Treatment Type")
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

                    risk = fraud_score(status, a, limit)

                    if risk > 70:
                        stt = "Rejected"
                    elif risk > 40:
                        stt = "Pending Review"
                    else:
                        stt = "Pending"

                    cur.execute("""
                        INSERT INTO claims
                        VALUES (NULL,?,?,?,?,?,?,?,?)
                    """, (p,n,h,t,a,risk,stt,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    conn.commit()
                    st.success("Submitted")

    # ================= REVIEW =================
    elif menu == "Review Claims":
        if st.session_state.role != "Insurance Officer":
            st.warning("Not allowed")
        else:
            st.title("Review Claims")

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
        st.title("Track Claim")

        cid = st.number_input("Claim ID", 1)

        if st.button("Check"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            if r:
                st.write(r)
            else:
                st.error("Not Found")

    # ================= AUDIT =================
    elif menu == "Audit Log":
        st.title("Audit Logs")

        df = pd.read_sql("SELECT * FROM audit_log", conn)
        st.dataframe(df)

    conn.close()
