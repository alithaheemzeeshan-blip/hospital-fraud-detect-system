import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Smart Health Insurance System",
    page_icon="🏥",
    layout="wide"
)

# ---------------- CSS ----------------
st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at top left, rgba(56,189,248,0.25), transparent 40%),
        radial-gradient(circle at bottom right, rgba(99,102,241,0.2), transparent 40%),
        linear-gradient(135deg, #020617, #0f172a, #111827);
    color: white;
}

.main-title {
    font-size: 46px;
    font-weight: 800;
    background: linear-gradient(90deg, #38bdf8, #22d3ee, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
}

.sub-title {
    text-align: center;
    color: #cbd5e1;
    font-size: 18px;
    margin-bottom: 30px;
}

.card {
    background: rgba(15,23,42,0.75);
    padding: 30px;
    border-radius: 22px;
    border: 1px solid rgba(148,163,184,0.25);
    box-shadow: 0px 15px 45px rgba(0,0,0,0.45);
}

.metric-card {
    background: linear-gradient(135deg, #0284c7, #4f46e5);
    padding: 25px;
    border-radius: 20px;
    text-align: center;
    font-weight: bold;
    box-shadow: 0px 10px 35px rgba(37,99,235,0.35);
}

.metric-card h1 {
    font-size: 42px;
}

.stButton button {
    background: linear-gradient(90deg, #0284c7, #2563eb);
    color: white;
    border-radius: 12px;
    padding: 10px 25px;
    border: none;
    font-weight: bold;
}

.stButton button:hover {
    background: linear-gradient(90deg, #0369a1, #1d4ed8);
    color: white;
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
        policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_number TEXT UNIQUE,
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
        fraud_risk TEXT,
        status TEXT,
        submission_date TEXT
    )
    """)

    c.execute("""
    INSERT OR IGNORE INTO users (email, password, role)
    VALUES
    ('hospital@gmail.com', '1234', 'Hospital'),
    ('officer@gmail.com', '1234', 'Insurance Officer'),
    ('user@gmail.com', '1234', 'Policyholder')
    """)

    c.execute("""
    INSERT OR IGNORE INTO policies
    (policy_number, policyholder_name, coverage_limit, status)
    VALUES
    ('POL123', 'Ali Khan', 50000, 'Active'),
    ('POL456', 'Sara Ahmed', 30000, 'Active'),
    ('POL789', 'Usman Ali', 20000, 'Expired')
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- FRAUD CHECK ----------------
def fraud_check(policy_status, claim_amount, coverage_limit):
    if policy_status == "Unknown":
        return "Medium Risk"
    elif policy_status != "Active":
        return "High Risk"
    elif claim_amount > coverage_limit:
        return "High Risk"
    elif claim_amount > coverage_limit * 0.8:
        return "Medium Risk"
    else:
        return "Low Risk"

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = ""

# ---------------- LOGIN PAGE ----------------
if not st.session_state.logged_in:
    st.markdown('<div class="main-title">🏥 Smart Health Insurance System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Claim Processing • Policy Verification • Fraud Detection • Claim Tracking</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.subheader("🔐 Login Panel")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Select Role", ["Hospital", "Insurance Officer", "Policyholder"])

        if st.button("Login"):
            conn = get_conn()
            c = conn.cursor()

            c.execute(
                "SELECT * FROM users WHERE email=? AND password=? AND role=?",
                (email, password, role)
            )

            user = c.fetchone()
            conn.close()

            if user:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid email, password, or role")

        st.info("""
Demo Login:

Hospital: hospital@gmail.com / 1234  
Officer: officer@gmail.com / 1234  
Policyholder: user@gmail.com / 1234
""")

        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- MAIN APP ----------------
else:
    st.sidebar.title("🏥 Smart Insurance")
    st.sidebar.success(f"Logged in as: {st.session_state.role}")

    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Submit Claim", "Review Claims", "Track Claim"]
    )

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.role = ""
        st.rerun()

    conn = get_conn()

    # ---------------- DASHBOARD ----------------
    if menu == "Dashboard":
        st.markdown('<div class="main-title">Dashboard Overview</div>', unsafe_allow_html=True)

        df = pd.read_sql_query("SELECT * FROM claims", conn)

        total = len(df)
        pending = len(df[df["status"].isin(["Pending", "Pending Verification"])]) if not df.empty else 0
        approved = len(df[df["status"] == "Approved"]) if not df.empty else 0
        rejected = len(df[df["status"] == "Rejected"]) if not df.empty else 0

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f'<div class="metric-card">Total Claims<h1>{total}</h1></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card">Pending Claims<h1>{pending}</h1></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card">Approved Claims<h1>{approved}</h1></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card">Rejected Claims<h1>{rejected}</h1></div>', unsafe_allow_html=True)

        st.subheader("Recent Claims")
        st.dataframe(df, use_container_width=True)

    # ---------------- SUBMIT CLAIM ----------------
    elif menu == "Submit Claim":
        if st.session_state.role != "Hospital":
            st.warning("Only Hospital users can submit claims.")
        else:
            st.markdown('<div class="main-title">Submit New Claim</div>', unsafe_allow_html=True)

            with st.form("claim_form"):
                col1, col2 = st.columns(2)

                with col1:
                    policy_number = st.text_input("Policy Number")
                    patient_name = st.text_input("Patient Name")
                    hospital_name = st.text_input("Hospital Name")

                with col2:
                    treatment_type = st.selectbox(
                        "Treatment Type",
                        ["Surgery", "Medicine", "Emergency", "Lab Test", "Other"]
                    )
                    claim_amount = st.number_input("Claim Amount", min_value=0.0, step=1000.0)
                    st.file_uploader("Upload Claim Document", type=["pdf", "jpg", "png"])

                submit = st.form_submit_button("Submit Claim")

                if submit:
                    if not policy_number or not patient_name or not hospital_name:
                        st.error("Please fill all required fields.")
                    else:
                        c = conn.cursor()

                        c.execute(
                            "SELECT coverage_limit, status FROM policies WHERE policy_number=?",
                            (policy_number,)
                        )

                        policy = c.fetchone()

                        if policy:
                            coverage_limit, policy_status = policy
                            risk = fraud_check(policy_status, claim_amount, coverage_limit)

                            if policy_status != "Active":
                                claim_status = "Rejected"
                            else:
                                claim_status = "Pending"
                        else:
                            coverage_limit = 0
                            policy_status = "Unknown"
                            risk = "Medium Risk"
                            claim_status = "Pending Verification"

                        c.execute("""
                        INSERT INTO claims
                        (policy_number, patient_name, hospital_name, treatment_type,
                         claim_amount, fraud_risk, status, submission_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            policy_number,
                            patient_name,
                            hospital_name,
                            treatment_type,
                            claim_amount,
                            risk,
                            claim_status,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))

                        conn.commit()

                        st.success("Claim submitted successfully!")
                        st.info(f"Policy Status: {policy_status}")
                        st.warning(f"Fraud Risk: {risk}")
                        st.info(f"Claim Status: {claim_status}")

    # ---------------- REVIEW CLAIMS ----------------
    elif menu == "Review Claims":
        if st.session_state.role != "Insurance Officer":
            st.warning("Only Insurance Officers can review claims.")
        else:
            st.markdown('<div class="main-title">Officer Review Screen</div>', unsafe_allow_html=True)

            df = pd.read_sql_query("SELECT * FROM claims", conn)
            st.dataframe(df, use_container_width=True)

            claim_id = st.number_input("Enter Claim ID", min_value=1, step=1)

            c1, c2, c3 = st.columns(3)
            cur = conn.cursor()

            with c1:
                if st.button("Approve Claim"):
                    cur.execute("UPDATE claims SET status='Approved' WHERE claim_id=?", (claim_id,))
                    conn.commit()
                    st.success("Claim approved successfully!")
                    st.rerun()

            with c2:
                if st.button("Reject Claim"):
                    cur.execute("UPDATE claims SET status='Rejected' WHERE claim_id=?", (claim_id,))
                    conn.commit()
                    st.error("Claim rejected!")
                    st.rerun()

            with c3:
                if st.button("Request More Info"):
                    cur.execute("UPDATE claims SET status='Request Info' WHERE claim_id=?", (claim_id,))
                    conn.commit()
                    st.warning("More information requested!")
                    st.rerun()

    # ---------------- TRACK CLAIM ----------------
    elif menu == "Track Claim":
        st.markdown('<div class="main-title">Claim Tracking</div>', unsafe_allow_html=True)

        claim_id = st.number_input("Enter Claim ID", min_value=1, step=1)

        if st.button("Check Status"):
            c = conn.cursor()

            c.execute("""
            SELECT claim_id, policy_number, patient_name, hospital_name,
                   treatment_type, claim_amount, fraud_risk, status, submission_date
            FROM claims
            WHERE claim_id=?
            """, (claim_id,))

            result = c.fetchone()

            if result:
                st.success("Claim Found")

                col1, col2 = st.columns(2)

                with col1:
                    st.info(f"Claim ID: {result[0]}")
                    st.info(f"Policy Number: {result[1]}")
                    st.info(f"Patient Name: {result[2]}")
                    st.info(f"Hospital Name: {result[3]}")

                with col2:
                    st.warning(f"Treatment Type: {result[4]}")
                    st.warning(f"Claim Amount: {result[5]}")
                    st.warning(f"Fraud Risk: {result[6]}")
                    st.warning(f"Current Status: {result[7]}")

                st.write(f"Submission Date: {result[8]}")
            else:
                st.error("Claim not found")

    conn.close()
