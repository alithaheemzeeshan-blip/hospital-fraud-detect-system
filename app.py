import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Smart Health Insurance System", layout="wide")

# ================= SAFE SESSION INIT =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""
    st.session_state.email = ""
    st.session_state.time = ""
    st.session_state.logout_confirm = False

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
    CREATE TABLE IF NOT EXISTS policies(
        policy_number TEXT,
        policyholder_name TEXT,
        coverage_limit REAL,
        status TEXT
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
        submission_date TEXT
    )
    """)

    # insert demo users only if empty
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
        reasons.append("Policy inactive or expired")

    if limit > 0:
        ratio = amount / limit
        if ratio > 1:
            score += 40
            reasons.append("Claim exceeds coverage limit")
        elif ratio > 0.8:
            score += 25
            reasons.append("High utilization of policy")
    else:
        score += 30
        reasons.append("Unknown policy detected")

    if amount > 50000:
        score += 20
        reasons.append("High-value claim anomaly")

    if "unknown" in hospital.lower():
        score += 15
        reasons.append("Unverified hospital source")

    if not reasons:
        reasons.append("Normal behavior detected")

    return min(score, 100), ", ".join(reasons)

# ================= UI STYLE =================
st.markdown("""
<style>
body {background:#0b1220; color:white;}

.title {
    text-align:center;
    font-size:40px;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#7a00ff,#ff00cc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.card {
    background: rgba(255,255,255,0.04);
    padding:15px;
    border-radius:15px;
    margin-bottom:10px;
    border:1px solid rgba(255,255,255,0.08);
}

.high{color:#ff4d4d;font-weight:800;}
.medium{color:#fbbf24;font-weight:800;}
.low{color:#22c55e;font-weight:800;}

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

    st.markdown('<div class="title">Smart Health Insurance System</div>', unsafe_allow_html=True)

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

# ================= MAIN APP =================
else:

    # SAFE SIDEBAR (NO CRASH VERSION)
    st.sidebar.title("🏥 Smart Health Insurance System")

    st.sidebar.write(f"👤 {st.session_state.get('email', '-')}")
    st.sidebar.write(f"🧩 {st.session_state.get('role', '-')}")
    st.sidebar.write(f"⏰ {st.session_state.get('time', '-')}")

    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Submit Claim", "Review Claims", "Track Claim", "Analytics"]
    )

    # ================= LOGOUT SAFE =================
    if st.sidebar.button("Logout"):
        st.session_state.logout_confirm = True

    if st.session_state.logout_confirm:
        st.sidebar.warning("Confirm Logout?")
        col1, col2 = st.sidebar.columns(2)

        if col1.button("Yes"):
            st.session_state.login = False
            st.session_state.role = ""
            st.session_state.email = ""
            st.session_state.time = ""
            st.session_state.logout_confirm = False
            st.rerun()

        if col2.button("No"):
            st.session_state.logout_confirm = False

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":

        st.markdown('<div class="title">Enterprise AI Dashboard</div>', unsafe_allow_html=True)

        df = pd.read_sql("SELECT * FROM claims", conn)

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Claims", len(df))
        c2.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)
        c3.metric("Safe", len(df[df["fraud_score"] <= 40]) if not df.empty else 0)

        st.markdown("---")

        if not df.empty:
            for _, r in df.tail(10).iterrows():

                level = "high" if r["fraud_score"] > 70 else "medium" if r["fraud_score"] > 40 else "low"

                st.markdown(f"""
                <div class="card">
                    <b>Claim ID:</b> {r['claim_id']} |
                    <span class="{level}">{r['fraud_score']}%</span><br><br>

                    Policy: {r['policy_number']}<br>
                    Amount: {r['claim_amount']}<br>
                    Reason: {r['fraud_reason']}<br>
                    Status: {r['status']}
                </div>
                """, unsafe_allow_html=True)

    # ================= SUBMIT =================
    elif menu == "Submit Claim":

        if st.session_state.role != "Hospital":
            st.warning("Access Denied")
        else:
            st.title("Submit Claim")

            with st.form("claim"):
                p = st.text_input("Policy Number")
                n = st.text_input("Patient Name")
                h = st.text_input("Hospital Name")
                t = st.text_input("Treatment Type")
                a = st.number_input("Claim Amount", min_value=0.0)

                ok = st.form_submit_button("Submit")

                if ok:
                    cur = conn.cursor()
                    cur.execute("SELECT coverage_limit,status FROM policies WHERE policy_number=?", (p,))
                    pol = cur.fetchone()

                    if pol:
                        limit, status = pol
                    else:
                        limit, status = 0, "Unknown"

                    score, reason = ai_fraud_model(status, a, limit, h)

                    final_status = "Rejected" if score > 70 else "Pending"

                    cur.execute("""
                        INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?)
                    """, (p, n, h, t, a, score, reason, final_status,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    conn.commit()

                    st.success("Claim Submitted")
                    st.info(f"Fraud Score: {score}%")
                    st.warning(f"Reason: {reason}")

    # ================= REVIEW =================
    elif menu == "Review Claims":

        if st.session_state.role != "Officer":
            st.warning("Access Denied")
        else:
            st.title("Officer Panel")

            df = pd.read_sql("SELECT * FROM claims", conn)
            st.dataframe(df, use_container_width=True)

            cid = st.number_input("Claim ID", 1)

            col1, col2 = st.columns(2)

            if col1.button("Approve"):
                conn.execute("UPDATE claims SET status='Approved' WHERE claim_id=?", (cid,))
                conn.commit()
                st.success("Approved")

            if col2.button("Reject"):
                conn.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?", (cid,))
                conn.commit()
                st.error("Rejected")

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

        st.title("AI Analytics Dashboard")

        df = pd.read_sql("SELECT * FROM claims", conn)

        if not df.empty:
            st.bar_chart(df["fraud_score"])
            st.line_chart(df["claim_amount"])

    conn.close()
