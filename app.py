import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

# ================= CONFIG =================
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

# ================= DB INIT =================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # USERS
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        email TEXT,
        password TEXT,
        role TEXT
    )
    """)

    # CLAIMS
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

    # DEFAULT USERS
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

# ================= SAFE GET =================
def safe(row, key):
    try:
        return row[key]
    except:
        return "N/A"

# ================= STYLE =================
st.markdown("""
<style>
body { background:#0b1220; color:white; }

.title {
    text-align:center;
    font-size:32px;
    font-weight:800;
    margin-bottom:10px;
    color:white;
}

.login-box {
    max-width:380px;
    margin:auto;
    padding:20px;
    border-radius:14px;
    background: rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.1);
}

.stButton>button {
    width:100%;
    background:#2563eb;
    color:white;
    border-radius:8px;
    padding:8px;
}

.demo {
    font-size:12px;
    color:#cbd5e1;
    margin-top:10px;
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">Smart Health Insurance System</div>', unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    email = st.text_input("Email")
    pw = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Hospital", "Officer", "Policyholder"])

    if st.button("Login"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM users
            WHERE email=? AND password=? AND role=?
        """, (email, hash_password(pw), role))

        if c.fetchone():
            st.session_state.login = True
            st.session_state.email = email
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.markdown("""
    <div class="demo">
    Demo Accounts:<br>
    Hospital: hospital@gmail.com / hospital123<br>
    Officer: officer@gmail.com / officer123<br>
    User: user@gmail.com / user123
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("Smart Insurance System")
    st.sidebar.write(st.session_state.email)

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM claims", conn)

    # ================= MENU =================
    if st.session_state.role == "Officer":
        menu = st.sidebar.radio(
            "Navigation",
            ["Dashboard", "Review Claims", "Track Claim", "Analytics"]
        )
    else:
        menu = st.sidebar.radio(
            "Navigation",
            ["Dashboard", "Submit Claim", "Track Claim", "Analytics"]
        )

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        st.title("Dashboard")

        st.metric("Total Claims", len(df))
        st.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":

        st.title("Submit Claim")

        p = st.text_input("Policy Number")
        patient = st.text_input("Patient Name")
        hospital = st.text_input("Hospital Name")
        treatment = st.text_input("Treatment Type")
        amount = st.number_input("Claim Amount", min_value=0.0)

        if st.button("Submit"):

            score, reason = ai_fraud_model(amount, 50000, hospital)

            cur = conn.cursor()

            # ✅ SAFE INSERT (THIS FIXES YOUR REVIEW PANEL ISSUE)
            cur.execute("""
            INSERT INTO claims (
                policy_number,
                patient_name,
                hospital_name,
                treatment,
                claim_amount,
                fraud_score,
                fraud_reason,
                status,
                submission_date,
                file_path,
                file_type,
                submitted_by
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p, patient, hospital, treatment, amount,
                score, reason, "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                None, None, st.session_state.email
            ))

            conn.commit()
            st.success("Claim Submitted Successfully")

    # ================= REVIEW CLAIMS =================
    elif menu == "Review Claims":

        st.title("Officer Review Panel")

        if df.empty:
            st.warning("No claims available yet.")
        else:
            for _, r in df.iterrows():

                st.write(
                    f"ID:{safe(r,'claim_id')} | "
                    f"Patient:{safe(r,'patient_name')} | "
                    f"Hospital:{safe(r,'hospital_name')} | "
                    f"Treatment:{safe(r,'treatment')} | "
                    f"Score:{safe(r,'fraud_score')} | "
                    f"Status:{safe(r,'status')}"
                )

                if safe(r, "status") == "Pending":

                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button(f"✅ Accept {r['claim_id']}", key=f"a{r['claim_id']}"):
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE claims SET status='Approved' WHERE claim_id=?",
                                (r["claim_id"],)
                            )
                            conn.commit()
                            st.rerun()

                    with c2:
                        if st.button(f"❌ Reject {r['claim_id']}", key=f"r{r['claim_id']}"):
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE claims SET status='Rejected' WHERE claim_id=?",
                                (r["claim_id"],)
                            )
                            conn.commit()
                            st.rerun()

    # ================= TRACK =================
    elif menu == "Track Claim":

        st.title("Track Claim")

        cid = st.number_input("Claim ID", min_value=1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            st.write(r if r else "Not Found")

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("Analytics")

        if not df.empty:
            st.bar_chart(df["fraud_score"])
            st.line_chart(df["claim_amount"])

    conn.close()
