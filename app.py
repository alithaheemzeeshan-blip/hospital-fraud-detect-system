import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

# ================= CONFIG =================
st.set_page_config(page_title="Smart Insurance AI System", layout="wide")

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

# ================= AI FRAUD MODEL =================
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

# ================= AI DECISION =================
def ai_decision(score):
    if score >= 75:
        return "Rejected", "High fraud risk"
    elif score >= 40:
        return "Review", "Moderate risk"
    else:
        return "Approved", "Low risk"

# ================= EMAIL SIM =================
def send_email(to, subject, msg):
    st.info(f"""
📧 EMAIL SIMULATION

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
        patient_name TEXT,
        hospital_name TEXT,
        treatment_type TEXT,
        claim_amount REAL,
        fraud_score REAL,
        fraud_reason TEXT,
        status TEXT,
        submission_date TEXT,
        file_path TEXT,
        file_type TEXT
    )
    """)

    conn.commit()

    # SAFE MIGRATION
    try:
        c.execute("ALTER TABLE claims ADD COLUMN submitted_by TEXT")
        conn.commit()
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
body { background:#0b1220; color:white; }

.title {
    text-align:center;
    font-size:40px;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#7a00ff,#ff00cc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.card {
    background: rgba(255,255,255,0.05);
    padding:15px;
    border-radius:12px;
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

    st.markdown('<div class="title">🏥 Smart Insurance AI System</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.subheader("Login Panel")

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

        st.markdown("""
        <div class="card">
        <b>Demo Accounts</b><br><br>
        Hospital: hospital@gmail.com / hospital123<br>
        Officer: officer@gmail.com / officer123<br>
        Policyholder: user@gmail.com / user123
        </div>
        """, unsafe_allow_html=True)

# ================= MAIN APP =================
else:

    st.sidebar.title("Insurance System")
    st.sidebar.write(st.session_state.email)
    st.sidebar.write(st.session_state.role)

    if st.session_state.role == "Policyholder":
        menu = st.sidebar.radio(
            "Menu",
            ["Dashboard", "Submit Claim", "My Claims", "Track Claim", "Analytics"]
        )
    else:
        menu = st.sidebar.radio(
            "Menu",
            ["Dashboard", "Submit Claim", "Review Claims", "Officer Analytics", "Track Claim", "Analytics"]
        )

    conn = get_conn()

    # ================= DASHBOARD =================
    if menu == "Dashboard":

        st.markdown('<div class="title">Dashboard</div>', unsafe_allow_html=True)

        df = pd.read_sql("SELECT * FROM claims", conn)

        c1,c2,c3 = st.columns(3)
        c1.metric("Total", len(df))
        c2.metric("High Risk", len(df[df["fraud_score"] > 70]) if not df.empty else 0)
        c3.metric("Safe", len(df[df["fraud_score"] <= 40]) if not df.empty else 0)

    # ================= SUBMIT CLAIM =================
    elif menu == "Submit Claim":

        st.title("Submit Claim")

        with st.form("form"):

            p = st.text_input("Policy No")
            n = st.text_input("Patient")
            h = st.text_input("Hospital")
            t = st.text_input("Treatment")
            a = st.number_input("Amount", min_value=0.0)

            file = st.file_uploader("Upload File")

            submit = st.form_submit_button("Submit")

            if submit:

                path = None
                ftype = None

                if file:
                    path = os.path.join(UPLOAD_DIR, file.name)
                    with open(path, "wb") as f:
                        f.write(file.getbuffer())
                    ftype = file.type

                score, reason = ai_fraud_model("Active", a, 50000, h)

                cur = conn.cursor()
                cur.execute("""
                INSERT INTO claims VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    p,n,h,t,a,
                    score,reason,
                    "Pending",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    path,ftype,
                    st.session_state.email
                ))

                conn.commit()

                st.success("Claim Submitted")
                st.info(reason)

    # ================= REVIEW CLAIMS (OFFICER) =================
    elif menu == "Review Claims":

        st.title("Officer Panel")

        df = pd.read_sql("SELECT * FROM claims", conn)

        for _, r in df.iterrows():

            st.markdown("---")

            st.markdown(f"""
            <div class="card">
                Claim {r['claim_id']}<br>
                Fraud: {r['fraud_score']}%<br>
                Status: {r['status']}
            </div>
            """, unsafe_allow_html=True)

            if r["status"] == "Pending":

                ai_action, reason = ai_decision(r["fraud_score"])
                st.write("🤖 AI:", ai_action, "-", reason)

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(f"Approve {r['claim_id']}", key=f"a{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?",(r["claim_id"],))
                        conn.commit()

                        send_email(r.get("submitted_by","user"),"Approved","Claim approved")
                        st.rerun()

                with col2:
                    if st.button(f"Reject {r['claim_id']}", key=f"r{r['claim_id']}"):
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?",(r["claim_id"],))
                        conn.commit()

                        send_email(r.get("submitted_by","user"),"Rejected","Claim rejected")
                        st.rerun()

                with col3:
                    if st.button(f"Auto {r['claim_id']}", key=f"auto{r['claim_id']}"):
                        decision, msg = ai_decision(r["fraud_score"])
                        cur = conn.cursor()
                        cur.execute("UPDATE claims SET status=? WHERE claim_id=?",(decision,r["claim_id"]))
                        conn.commit()

                        send_email(r.get("submitted_by","user"),decision,msg)
                        st.rerun()

    # ================= MY CLAIMS =================
    elif menu == "My Claims":

        st.title("My Claims")

        df = pd.read_sql("SELECT * FROM claims", conn)

        if "submitted_by" in df.columns:
            df = df[df["submitted_by"] == st.session_state.email]

        st.dataframe(df)

    # ================= OFFICER ANALYTICS =================
    elif menu == "Officer Analytics":

        st.title("Analytics")

        df = pd.read_sql("SELECT * FROM claims", conn)

        st.metric("Approved", len(df[df["status"]=="Approved"]))
        st.metric("Rejected", len(df[df["status"]=="Rejected"]))
        st.metric("Pending", len(df[df["status"]=="Pending"]))

        st.bar_chart(df["fraud_score"])
        st.line_chart(df["claim_amount"])

    # ================= TRACK =================
    elif menu == "Track Claim":

        st.title("Track")

        cid = st.number_input("ID",1)

        if st.button("Search"):
            cur = conn.cursor()
            cur.execute("SELECT * FROM claims WHERE claim_id=?",(cid,))
            st.write(cur.fetchone())

    # ================= ANALYTICS =================
    elif menu == "Analytics":

        st.title("Analytics")

        df = pd.read_sql("SELECT * FROM claims", conn)

        st.bar_chart(df["fraud_score"])
        st.line_chart(df["claim_amount"])

    conn.close()
