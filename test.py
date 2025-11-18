import pyodbc
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import sys
import traceback

# ------------------------------------------------------
# FIX PATH FOR EXE (log file, DB, etc.)
# ------------------------------------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, "DailyAttendanceMailLog.txt")


# ------------------------------------------------------
# LOGGING FUNCTION
# ------------------------------------------------------
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full = f"[{timestamp}] {message}"
    print(full, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full + "\n")


# ------------------------------------------------------
# FATAL ERROR HANDLER (Keeps CMD Open)
# ------------------------------------------------------
def fatal_error(e):
    error_text = traceback.format_exc()
    log("❌ FATAL ERROR:")
    log(error_text)

    print("\n⚠ Program stopped due to an error.")
    input("Press ENTER to close...")
    sys.exit()


# ------------------------------------------------------
# MAIN SCRIPT INSIDE TRY BLOCK
# ------------------------------------------------------
try:

    # ------------------------------------------------------
    # **NEW: Skip processing if yesterday was Sunday**
    # ------------------------------------------------------
    yesterday_date = datetime.now() - timedelta(days=1)

    if yesterday_date.weekday() == 6:  # Sunday = 6
        log("⛔ Yesterday was Sunday — No attendance mail will be sent.")
        print("Yesterday was Sunday. No emails sent. Press ENTER to close.")
        input()
        sys.exit()

    # SQL SERVER CONNECTION
    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};'
            'SERVER=103.172.150.57,1434;'
            'DATABASE=ETime;'
            'UID=pbi;'
            'PWD=K091Gvpj4%p.;'
        )
        log("Connected to SQL Server")
    except Exception as e:
        fatal_error(e)

    # Yesterday’s date formatted
    yesterday = yesterday_date.strftime("%Y-%m-%d")
    formatted_date = yesterday_date.strftime("%d-%m-%Y")

    # ------------------------------------------------------
    # FETCH ATTENDANCE FROM VIEW
    # **NEW: Only fetch records where InTime OR OutTime exists**
    # ------------------------------------------------------
    query = f"""
    SELECT 
        EmployeeID,
        EmployeeName,
        LTRIM(RTRIM(Email)) AS Email,
        CONVERT(VARCHAR(8), InTime, 108) AS InTime,
        CONVERT(VARCHAR(8), OutTime, 108) AS OutTime,
        AttendanceDate
    FROM vw_DailyInOutMail
    WHERE AttendanceDate = '{yesterday}'
      AND (InTime IS NOT NULL OR OutTime IS NOT NULL)
    """

    try:
        df = pd.read_sql(query, conn)
        log("Attendance data fetched successfully")
    except Exception as e:
        fatal_error(e)

    if df.empty:
        log("❌ No attendance with In/Out time for yesterday.")
        print("No employees with In/Out time. Press ENTER to exit.")
        input()
        sys.exit()

    # ------------------------------------------------------
    # SMTP SETTINGS
    # ------------------------------------------------------
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    SENDER_EMAIL = "sejalexportshr@gmail.com"
    SENDER_PASSWORD = "eywluoohqmrdrgxd"  # App Password


    # ------------------------------------------------------
    # EMAIL FUNCTION
    # ------------------------------------------------------
    def send_email(to_email, subject, body):
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            return True
        except Exception:
            log(f"❌ ERROR sending to {to_email}: {traceback.format_exc()}")
            return False


    # ------------------------------------------------------
    # START BULK EMAIL PROCESS
    # ------------------------------------------------------
    print("\n=================================================")
    print("🚀 Starting Daily Attendance Email Process")
    print("=================================================\n")

    total = len(df)
    success_count = 0
    failed_count = 0

    log(f"Sending emails to {total} employees")
    email_subject = f"Attendance Details for {formatted_date}"

    for _, row in df.iterrows():

        # Validate email
        to_email = row["Email"]

        if not to_email or str(to_email).strip() == "" or str(to_email).lower() == "none":
            log(f"⚠ Skipped {row['EmployeeName']} — Missing or invalid email")
            continue

        to_email = str(to_email).strip()
        emp_name = row["EmployeeName"]

        print(f"📨 Sending to: {emp_name} <{to_email}> ... ", end="", flush=True)

        email_body = f"""Hello {emp_name},

Date : {formatted_date}

In Time - {row['InTime']}
Out Time - {row['OutTime']}

This is a system Generated Email.
"""

        if send_email(to_email, email_subject, email_body):
            print("✔ SUCCESS")
            log(f"Email sent successfully to {to_email}")
            success_count += 1
        else:
            print("✖ FAILED")
            failed_count += 1


    # ------------------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------------------
    print("\n=================================================")
    print("📊 DAILY ATTENDANCE EMAIL REPORT")
    print("=================================================")
    print(f"✔ Success : {success_count}")
    print(f"✖ Failed  : {failed_count}")
    print(f"📁 Log file: {LOG_FILE}")
    print("=================================================\n")

    log(f"Process Completed | Success: {success_count} | Failed: {failed_count}")

    input("Press ENTER to close...")

except Exception as e:
    fatal_error(e)
