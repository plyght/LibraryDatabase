import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pandas as pd

class NotificationSystem:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"  # or whichever
        self.smtp_port = 587
        self.sender_email = os.environ.get('LIBRARY_EMAIL')
        self.sender_password = os.environ.get('LIBRARY_EMAIL_PASSWORD')

    def send_email(self, recipient_email, subject, body):
        """Send an email using SMTP with verbose console logs."""
        print(f"DEBUG [send_email]: about to send from '{self.sender_email}' to '{recipient_email}' subject='{subject}'")
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                print("DEBUG [send_email]: logging in to smtp server...")
                server.login(self.sender_email, self.sender_password)
                print("DEBUG [send_email]: login success, now sending message...")
                server.send_message(message)
            print("DEBUG [send_email]: email sent successfully => returning True")
            return True
        except Exception as e:
            print(f"DEBUG [send_email]: failed to send email => {e}")
            return False

    def check_reminders(self, db):
        """Check for due dates: 3 days before, same day, 3 days after. send email if needed"""
        print("DEBUG [check_reminders]: start checking overdue or near-due books")
        today = datetime.now().date()
        checkouts_df = db.get_all_checkouts()
        users_df = db.get_all_users()
        books_df = db.get_all_books()

        # some day-check
        # let's define "reminder windows" for demonstration:
        # 3 days before due => (due - 3) == today
        # due day => (due_date == today)
        # 3 days after => (due_date + 3) == today
        # you can expand logic as you wish

        for _, row in checkouts_df.iterrows():
            if pd.isna(row['return_date']):
                due = pd.to_datetime(row['due_date']).date()
                diff = (due - today).days
                if diff == 3 or diff == 0 or diff == -3:
                    user = users_df[users_df['user_id'] == row['user_id']]
                    if not user.empty:
                        user_email = user.iloc[0]['email']
                        user_name = user.iloc[0]['name']
                        # find the book
                        book_record = books_df[books_df['copy_ids'].str.contains(row['copy_id'], na=False)]
                        if not book_record.empty:
                            btitle = book_record.iloc[0]['title']
                            subject = "Library Reminder: Book Due Soon" if diff == 3 else (
                                "Library Reminder: Book Due Today" if diff == 0 else "Library Overdue Notice"
                            )
                            body = f"Hello {user_name},\n\n"
                            if diff == 3:
                                body += f"This is a reminder that your book '{btitle}' is due in 3 days.\n"
                            elif diff == 0:
                                body += f"Your book '{btitle}' is due today! Please return it soon.\n"
                            else:
                                body += f"Your book '{btitle}' is overdue by 3 days. please return it asap.\n"

                            body += "\nRegards,\nLibrary Management"
                            # send
                            print(f"DEBUG [check_reminders]: sending reminder to '{user_email}' about book '{btitle}' (diff={diff})")
                            ok = self.send_email(user_email, subject, body)
                            if not ok:
                                print(f"DEBUG [check_reminders]: email to {user_email} failed")
                            else:
                                print(f"DEBUG [check_reminders]: success => reminder sent to {user_email}")

    def send_debug_email(self, test_email):
        """Send a test email from admin panel, with extra logs."""
        print(f"DEBUG [send_debug_email]: about to send to {test_email}")
        sub = "Library Debug Email"
        bod = "This is a test email from the library management system debug function."
        return self.send_email(test_email, sub, bod)
