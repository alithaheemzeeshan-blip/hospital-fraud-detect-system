import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="Smart Health Insurance System",
    layout="wide"
)

# ---------------- DATABASE ----------------
def get_connection():
    return sqlite3.connect("insurance.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_number TEXT UNIQUE,
        policyholder_name TEXT,
        coverage_limit REAL,
        status TEXT
    )
    """)

    cursor.execute("""
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

    cursor.execute("""
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
def check_fraud(policy_status, claim_amount, coverage_limit):
    if policy_status != "Active":
        return "High Risk"
    elif claim_amount > coverage_limit:
        return "High Risk"
    elif claim_amount > coverage_limit * 0.8:
        return "Medium Risk"
    else:
        return "Low Risk"

# ---------------- HEADER ----------------
st.title("Smart Health Insurance Claim Processing and Fraud Detection System")
st.write("A web-based application for claim submission, policy verification, fraud risk checking, and claim tracking.")

role = st.sidebar.selectbox(
    "Select User Role",
    ["Hospital", "Insurance Officer", "Policyholder"]
)

# ---------------- HOSPITAL DASHBOARD ----------------
if role == "Hospital":
    st.header("Hospital Dashboard")

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM claims", conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Claims", len(df))
    col2.metric("Pending Claims", len(df[df["status"] == "Pending"]) if not df.empty else 0)
    col3.metric("Approved Claims", len(df[df["status"] == "Approved"]) if not df.empty else 0)
    col4.metric("Rejected Claims", len(df[df["status"] == "Rejected"]) if not df.empty else 0)

    st.subheader("Submit New Insurance Claim")

    with st.form("claim_form"):
        policy_number = st.text_input("Policy Number")
        patient_name = st.text_input("Patient Name")
        hospital_name = st.text_input("Hospital Name")
        treatment_type = st.selectbox(
            "Treatment Type",
            ["Surgery", "Medicine", "Emergency", "Lab Test", "Other"]
        )
        claim_amount = st.number_input("Claim Amount", min_value=0.0, step=1000.0)

        submitted = st.form_submit_button("Submit Claim")

        if submitted:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT coverage_limit, status FROM policies WHERE policy_number=?",
                (policy_number,)
            )
            policy = cursor.fetchone()

            if policy:
                coverage_limit, policy_status = policy
                fraud_risk = check_fraud(policy_status, claim_amount, coverage_limit)

                if policy_status != "Active":
                    claim_status = "Rejected"
                else:
                    claim_status = "Pending"

                cursor.execute("""
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
                    fraud_risk,
                    claim_status,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                conn.commit()
                st.success(f"Claim submitted successfully! Fraud Risk: {fraud_risk}")
            else:
                st.error("Invalid Policy Number!")

    st.subheader("Submitted Claims")
    df = pd.read_sql_query("SELECT * FROM claims", conn)
    st.dataframe(df, use_container_width=True)

    conn.close()

# ---------------- OFFICER DASHBOARD ----------------
elif role == "Insurance Officer":
    st.header("Insurance Officer Dashboard")

    conn = get_connection()
    cursor = conn.cursor()

    df = pd.read_sql_query("SELECT * FROM claims", conn)
    st.subheader("All Submitted Claims")
    st.dataframe(df, use_container_width=True)

    st.subheader("Review Claim")

    claim_id = st.number_input("Enter Claim ID", min_value=1, step=1)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Approve Claim"):
            cursor.execute(
                "UPDATE claims SET status='Approved' WHERE claim_id=?",
                (claim_id,)
            )
            conn.commit()
            st.success("Claim approved successfully!")

    with col2:
        if st.button("Reject Claim"):
            cursor.execute(
                "UPDATE claims SET status='Rejected' WHERE claim_id=?",
                (claim_id,)
            )
            conn.commit()
            st.error("Claim rejected!")

    with col3:
        if st.button("Request More Info"):
            cursor.execute(
                "UPDATE claims SET status='Request Info' WHERE claim_id=?",
                (claim_id,)
            )
            conn.commit()
            st.warning("More information requested!")

    conn.close()

# ---------------- POLICYHOLDER DASHBOARD ----------------
elif role == "Policyholder":
    st.header("Policyholder Claim Tracking")

    claim_id = st.number_input("Enter Claim ID", min_value=1, step=1)

    if st.button("Check Claim Status"):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT claim_id, policy_number, patient_name, claim_amount,
               fraud_risk, status, submission_date
        FROM claims
        WHERE claim_id=?
        """, (claim_id,))

        result = cursor.fetchone()

        if result:
            st.success("Claim Found")

            st.write(f"**Claim ID:** {result[0]}")
            st.write(f"**Policy Number:** {result[1]}")
            st.write(f"**Patient Name:** {result[2]}")
            st.write(f"**Claim Amount:** {result[3]}")
            st.write(f"**Fraud Risk:** {result[4]}")
            st.write(f"**Current Status:** {result[5]}")
            st.write(f"**Submission Date:** {result[6]}")
        else:
            st.error("Claim not found!")

        conn.close()