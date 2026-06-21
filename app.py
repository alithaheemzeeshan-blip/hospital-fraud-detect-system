import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Smart Health Insurance System", layout="wide")

# ================= FILE STORAGE =================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""
    st.session_state.email = ""
    st.session_state.time = ""

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
        treatment_type TEXT,
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

# ================= AI FRAUD ENGINE =================
def ai_fraud_model(status, amount, limit, hospital):
    score = 0
    reasons = []

    if status != "Active":
        score += 45
        reasons.append("Inactive policy")

    if limit > 0:
        ratio = amount / limit
        if ratio > 1:
            score += 40
            reasons.append("Over limit claim")
        elif ratio > 0.8:
            score += 25
            reasons.append("High usage policy")
    else:
        score += 30
        reasons.append("Unknown policy")

    if amount > 50000:
        score += 20
        reasons.append("High value claim")

    if "unknown" in hospital.lower():
        score += 15
        reasons.append("Unverified hospital")

    return min(score, 100), ", ".join(reasons) if reasons else "Normal case"

# ================= STYLE =================
st.markdown("""
<style>
body { background:#0b1220; color:white; }

.title {
    text-align:center;
    font-size:42px;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#7a00ff,#ff00cc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.card {
    background: rgba(255,255,255,0.05);
    padding:15px;
    border-radius:15px;
    margin-top:10px;
    border:1px solid rgba(255,255,255,0.1);
}

.stButton>button {
    background: linear-gradient(90deg,#4f46e5,#06b6d4);
    color:white;
    border-radius:10px;
    padding:8px 14px;
}
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if not st.session_state.login:

    st.markdown('<div class="title">🏥 Smart Health Insurance System</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.subheader("🔐 Login Panel")

        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Hospital", "Officer", "Policyholder"])

        if st.button("Login"):
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=? AND password=? AND role=?",
                      (email, hash_password(pw), role))
            user = c.fetchone()

            if user:
                st.session_state.login = True
                st.session_state.role = role
                st.session_state.email = email
                st.session_state.time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.rerun()
            else:
                st.error("Invalid login")

        # ================= DEMO CREDENTIALS =================
        st.markdown("### 🔑 Demo Login Credentials")

        st.markdown("""
        <div class="card">
        <b>🏥 Hospital</b><br>
        hospital@gmail.com / hospital123<br><br>

        <b>🧑‍⚕️ Officer</b><br>
        officer@gmail.com / officer123<br><br>

        <b>👤 Policyholder</b><br>
        user@gmail.com / user123
        </div>
        """, unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("🏥 Smart Insurance System")
    st.sidebar.write(st.session_state.email)
    st.sidebar.write(st.session_state.role)
    st.sidebar.write(st.session_state.time)

    # ================= ROLE BASED MENU =================
    if st.session_state.role == "Policyholder":
        menu = st.sidebar.radio(
            "Navigation",
            ["Dashboard", "Submit Claim", "My Claims", "Track Claim", "Analytics"]
        )
    else:
        menu = st.sidebar.radio(
            "Navigation",
            ["Dashboard", "Submit Claim", "Review Claims", "Track Claim", "Analytics"]
        )

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":

        st.markdown('<div class="title">Enterprise AI Dashboard</div>', unsafe_allow_html=True)

        df = pd.read_sql("SELECT * FROM claims", conn)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Claims", len(df))
        c2.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)
        c3.metric("Safe", len(df[df["fraud_score"] <= 40]) if not df.empty else 0)

        if not df.empty:
            for _, r in df.tail(6).iterrows():

                st.markdown(f"""
                <div class="card">
                    <b>Claim ID:</b> {r['claim_id']}<br>
                    🏥 {r['hospital_name']}<br>
                    💊 {r['treatment_type']}<br>
                    💰 {r['claim_amount']}<br>
                    🧠 {r['fraud_reason']}<br>
                    📌 {r['status']}
                </div>
                """, unsafe_allow_html=True)

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":

        st.title("Submit Claim")

        with st.form("claim"):

            p = st.text_input("Policy Number")
            n = st.text_input("Patient Name")
            h = st.text_input("Hospital Name")
            t = st.text_input("Treatment Type")
            a = st.number_input("Claim Amount", min_value=0.0)

            uploaded_file = st.file_uploader("Upload Report", type=["pdf", "png", "jpg", "jpeg"])

            submit = st.form_submit_button("Submit Claim")

            if submit:

                file_path = None
                file_type = None

                if uploaded_file:
                    file_type = uploaded_file.type
                    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                limit, status = 50000, "Active"

                score, reason = ai_fraud_model(status, a, limit, h)

                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    p, n, h, t, a,
                    score, reason,
                    "Pending",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    file_path,
                    file_type,
                    st.session_state.email
                ))

                conn.commit()

                st.success("Claim Submitted Successfully")
                st.info(f"Fraud Score: {score}%")
                st.warning(reason)

    # ================= REVIEW CLAIMS =================
    elif menu == "Review Claims":

        st.title("Officer Review Panel")

        df = pd.read_sql("SELECT * FROM claims", conn)

        for _, row in df.iterrows():

            st.markdown("---")
            st.write(row.to_dict())

            if row["status"] == "Pending":

                if st.button(f"Approve {row['claim_id']}", key=f"a{row['claim_id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",
                                (row["claim_id"],))
                    conn.commit()
                    st.rerun()

                if st.button(f"Reject {row['claim_id']}", key=f"r{row['claim_id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",
                                (row["claim_id"],))
                    conn.commit()
                    st.rerun()

    # ================= MY CLAIMS (POLICYHOLDER) =================
    elif menu == "My Claims":

        st.title("👤 My Claims Dashboard")

        df = pd.read_sql("SELECT * FROM claims", conn)
        my_df = df[df["submitted_by"] == st.session_state.email]

        if my_df.empty:
            st.info("No claims submitted yet.")
        else:
            for _, r in my_df.iterrows():
                st.markdown(f"""
                <div class="card">
                    <b>Claim ID:</b> {r['claim_id']}<br>
                    🏥 {r['hospital_name']}<br>
                    💊 {r['treatment_type']}<br>
                    💰 {r['claim_amount']}<br>
                    🧠 {r['fraud_score']}%<br>
                    📌 {r['status']}<br>
                    🕒 {r['submission_date']}
                </div>
                """, unsafe_allow_html=True)

    # ================= TRACK =================
    elif menu == "Track Claim":

        st.title("Track Claim")

        cid = st.number_input("Claim ID", 1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?", (cid,))
            r = cur.fetchone()

            if r:
                st.json(r)
            else:
                st.error("Not Found")

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("Analytics Dashboard")

        df = pd.read_sql("SELECT * FROM claims", conn)

        if not df.empty:
            st.bar_chart(df["fraud_score"])
            st.line_chart(df["claim_amount"])

    conn.close()
