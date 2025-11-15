import pyodbc
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import traceback

# ------------------------------------------------------
# LOGGING FUNCTION
# ------------------------------------------------------
LOG_FILE = "DailyAttendanceMailLog.txt"

def log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

log("\n------------------ SCRIPT STARTED ------------------")

try:
    # ------------------------------------------------------
    # SQL SERVER CONNECTION
    # ------------------------------------------------------
    conn = pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=103.172.150.57,1434;'
        'DATABASE=ETime;'
        'UID=pbi;'
        'PWD=K091Gvpj4%p.;'
    )
    log("Connected to SQL Server successfully.")

except Exception as e:
    log("ERROR connecting to SQL Server: " + str(e))
    log(traceback.format_exc())
    raise SystemExit("SQL Connection Error")

# Yesterday’s date
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
formatted_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

# ------------------------------------------------------
# FETCH DATA
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
"""

try:
    df = pd.read_sql(query, conn)
    log(f"Fetched {len(df)} attendance records.")

except Exception as e:
    log("ERROR fetching SQL data: " + str(e))
    log(traceback.format_exc())
    raise SystemExit("SQL Query Error")

if df.empty:
    log("No attendance data for yesterday. Script ended.")
    exit()

# ------------------------------------------------------
# SMTP SETTINGS
# ------------------------------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "sejalexportshr@gmail.com"
SENDER_PASSWORD = "eywluoohqmrdrgxd"  # Gmail App Password

# ------------------------------------------------------
# EMAIL FUNCTION
# ------------------------------------------------------
def send_email(to_email, employee_name, in_time, out_time):
    subject = f"Attendance Details for {formatted_date}"
    body = f"""Hello {employee_name},

Date : {formatted_date}

In Time - {in_time}
Out Time - {out_time}

This is a system Generated Email.
"""

    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        log(f"MAIL SENT ✔ → {to_email} ({employee_name})")

    except Exception as e:
        log(f"MAIL FAILED ✖ → {to_email} ({employee_name}) | ERROR: {str(e)}")
        log(traceback.format_exc())

# ------------------------------------------------------
# SEND BULK EMAILS
# ------------------------------------------------------
for index, row in df.iterrows():
    email = row["Email"].strip()
    name = row["EmployeeName"]
    in_time = row["InTime"]
    out_time = row["OutTime"]

    if not email:
        log(f"SKIPPED (No Email) → EmployeeID {row['EmployeeID']}")
        continue

    send_email(email, name, in_time, out_time)

# ------------------------------------------------------
# SCRIPT END
# ------------------------------------------------------
log("------------------ SCRIPT COMPLETED ------------------\n")

print("🎉 All mails processed! Check log file for details.")
