import pyodbc
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import sys
import traceback
import time

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

def wait_for_exit(message="Press ENTER to close..."):
    try:
        if sys.stdin and sys.stdin.isatty():
            input(message)
    except (RuntimeError, EOFError):
        pass

def fatal_error(e):
    error_text = traceback.format_exc()
    log("❌ FATAL ERROR:")
    log(error_text)
    wait_for_exit("Press ENTER to close...")
    sys.exit()

# ------------------------------------------------------
# SAFE WAIT FUNCTION (for manual run only)
# ------------------------------------------------------
def wait_for_exit(message="Press ENTER to close..."):
    """
    Safely wait for user input only if running in an interactive console.
    In Task Scheduler / non-interactive mode, it will just skip.
    """
    try:
        if sys.stdin and sys.stdin.isatty():
            input(message)
    except (RuntimeError, EOFError):
        # No stdin available (Task Scheduler / service / etc.)
        pass


# ------------------------------------------------------
# FATAL ERROR HANDLER
# ------------------------------------------------------
def fatal_error(e):
    error_text = traceback.format_exc()
    log("❌ FATAL ERROR:")
    log(error_text)

    print("\n⚠ Program stopped due to an error.")
    wait_for_exit("Press ENTER to close...")
    sys.exit()


# ------------------------------------------------------
# MAIN SCRIPT INSIDE TRY BLOCK
# ------------------------------------------------------
try:
    yesterday_date = datetime.now() - timedelta(days=1)

    # Skip Sunday
    if yesterday_date.weekday() == 6:
        log("⛔ Yesterday was Sunday — No attendance mail will be sent.")
        sys.exit()

    yesterday = yesterday_date.strftime("%Y-%m-%d")
    formatted_date = yesterday_date.strftime("%d-%m-%Y")

    # SQL CONNECTION
    conn = pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=103.172.150.57,1434;'
        'DATABASE=ETime;'
        'UID=pbi;'
        'PWD=K091Gvpj4%p.;'
    )
    log("✅ Connected to SQL Server")

    # FETCH ATTENDANCE
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

    df = pd.read_sql(query, conn)
    log("✅ Attendance data fetched successfully")

    if df.empty:
        log("❌ No attendance records found.")
        sys.exit()

    # ------------------------------------------------------
    # SMTP SETTINGS
    # ------------------------------------------------------
    SMTP_SERVER = "email-smtp.ap-south-1.amazonaws.com"
    SMTP_PORT = 587

    SENDER_EMAIL = "sejalexphr@sejal.co"  # Must be verified domain email

    SMTP_USERNAME = "AKIA6JRM5VFG5ILJIBM6"
    SMTP_PASSWORD = "BHduWNkoL7vyUEMPgvqag80u5UW2ICTBBp36/E3U7GKC"

    # CONNECT ONCE (IMPORTANT)
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=60)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    log("✅ Connected to Amazon SES SMTP")

    # ------------------------------------------------------
    # EMAIL FUNCTION
    # ------------------------------------------------------
    def send_email(server, to_email, subject, body):
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = f"Attendance System <{SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Reply-To"] = SENDER_EMAIL

        try:
            server.send_message(msg)
            return True
        except Exception as e:
            log(f"❌ Failed sending to {to_email}: {e}")
            return False


    # ------------------------------------------------------
    # START BULK EMAIL PROCESS
    # ------------------------------------------------------
    success_count = 0
    failed_count = 0

    email_subject = f"Attendance Details for {formatted_date}"

    for _, row in df.iterrows():
        to_email = str(row["Email"]).strip()

        if not to_email or to_email.lower() == "none":
            log(f"⚠ Skipped {row['EmployeeName']} — Invalid email")
            continue

        emp_name = row["EmployeeName"]

        email_body = f"""Hello {emp_name},

Date : {formatted_date}

In Time - {row['InTime']}
Out Time - {row['OutTime']}

This is a system generated attendance email.
"""

        msg = MIMEText(email_body, "plain")
        msg["Subject"] = email_subject
        msg["From"] = f"Attendance System <{SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Reply-To"] = SENDER_EMAIL

        try:
            server.send_message(msg)
            log(f"✅ Email sent successfully to {to_email}")
            success_count += 1
        except Exception as e:
            log(f"❌ Email failed for {to_email}: {e}")
            failed_count += 1

        time.sleep(2)  # SES throttle safety

    server.quit()

    log(f"Process Completed | Success: {success_count} | Failed: {failed_count}")

    wait_for_exit("Press ENTER to close...")

except Exception as e:
    fatal_error(e)

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

    wait_for_exit("Press ENTER to close...")

except Exception as e:
    fatal_error(e)
