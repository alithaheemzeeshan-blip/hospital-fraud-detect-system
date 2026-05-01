import sqlite3

def create_database():
    conn = sqlite3.connect("insurance.db")
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # POLICIES TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_number TEXT UNIQUE,
        policyholder_name TEXT,
        coverage_limit REAL,
        status TEXT
    )
    """)

    # CLAIMS TABLE
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

    conn.commit()
    conn.close()
    print("Database created successfully!")

# RUN FUNCTION
create_database()
def insert_data():
    import sqlite3
    conn = sqlite3.connect("insurance.db")
    cursor = conn.cursor()

    # Sample Policy
    cursor.execute("""
    INSERT OR IGNORE INTO policies 
    (policy_number, policyholder_name, coverage_limit, status)
    VALUES 
    ('POL123', 'Ali Khan', 50000, 'Active')
    """)

    # Sample User
    cursor.execute("""
    INSERT OR IGNORE INTO users 
    (name, email, password, role)
    VALUES 
    ('Hospital User', 'hospital@gmail.com', '1234', 'Hospital')
    """)

    conn.commit()
    conn.close()
    print("Data inserted!")

insert_data()
