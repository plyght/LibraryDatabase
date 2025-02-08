import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pandas as pd

class NotificationSystem:
    def __init__(self):
        # by default, read from environment or empty
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.environ.get('LIBRARY_EMAIL','')
        self.sender_password = os.environ.get('LIBRARY_EMAIL_PASSWORD','')

    def update_credentials(self, new_email, new_password):
        """Change the sender email/password at runtime."""
        print(f"DEBUG [update_credentials]: updating to '{new_email}'")
        self.sender_email = new_email
        self.sender_password = new_password

    def send_email(self, recipient_email, subject, body):
        print(f"DEBUG [send_email]: from='{self.sender_email}', to='{recipient_email}', subject='{subject}'")
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
            print("DEBUG [send_email]: email sent => returning True")
            return True
        except Exception as e:
            print(f"DEBUG [send_email]: failed => {e}")
            return False

    def check_reminders(self, db):
        print("DEBUG [check_reminders]: checking overdue or near-due books")
        today = datetime.now().date()
        checkouts_df = db.get_all_checkouts()
        users_df = db.get_all_users()
        books_df = db.get_all_books()

        for _, row in checkouts_df.iterrows():
            if pd.isna(row['return_date']):
                due = pd.to_datetime(row['due_date']).date()
                diff = (due - today).days
                # example logic for 3 days prior, same day, 3 days after
                if diff in (3,0,-3):
                    user = users_df[users_df['user_id'] == row['user_id']]
                    if not user.empty:
                        user_email = user.iloc[0]['email']
                        user_name = user.iloc[0]['name']
                        book_record = books_df[books_df['copy_ids'].str.contains(row['copy_id'], na=False)]
                        if not book_record.empty:
                            btitle = book_record.iloc[0]['title']
                            if diff == 3:
                                subject = "Library Reminder: Book due in 3 days"
                                body = f"Hello {user_name},\n\nYour book '{btitle}' is due in 3 days.\nRegards,\nLibrary"
                            elif diff == 0:
                                subject = "Library Reminder: Book due today"
                                body = f"Hello {user_name},\n\nYour book '{btitle}' is due today!\nRegards,\nLibrary"
                            else:
                                subject = "Library Overdue Notice"
                                body = f"Hello {user_name},\n\nYour book '{btitle}' is overdue by 3 days.\nRegards,\nLibrary"

                            print(f"DEBUG [check_reminders]: emailing '{user_email}' about diff={diff}")
                            ok = self.send_email(user_email, subject, body)
                            if not ok:
                                print(f"DEBUG [check_reminders]: email to {user_email} failed")

    def send_debug_email(self, test_email):
        print(f"DEBUG [send_debug_email]: sending to '{test_email}'")
        sub = "Library Debug Email"
        bod = "This is a test email from the library management system."
        return self.send_email(test_email, sub, bod)
