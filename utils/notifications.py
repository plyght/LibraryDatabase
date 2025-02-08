import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pandas as pd

class NotificationSystem:
    def __init__(self):
        # get from environment or you can hardcode
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.environ.get('LIBRARY_EMAIL')
        self.sender_password = os.environ.get('LIBRARY_EMAIL_PASSWORD')

    def send_email(self, recipient_email, subject, body):
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"failed to send email: {str(e)}")
            return False

    def check_reminders(self, db):
        """
        for each checkout row that is not returned, check how many days until or after due_date:
          * if days_to_due = 3 -> 3 days left
          * if days_to_due = 0 -> due today
          * if days_to_due = -3 -> 3 days overdue
        send the appropriate email if the user has an email
        """
        today = datetime.now().date()
        checkouts_df = pd.read_csv(db.checkouts_file)
        users_df = pd.read_csv(db.users_file)
        books_df = pd.read_csv(db.books_file)

        # filter only unreturned
        unreturned = checkouts_df[checkouts_df['return_date'].isna()]

        for _, row in unreturned.iterrows():
            try:
                due_str = row['due_date']
                due_dt = datetime.strptime(due_str, "%Y-%m-%d").date()
                days_to_due = (due_dt - today).days

                # only respond if days_to_due in [3, 0, -3]
                if days_to_due not in [3, 0, -3]:
                    continue

                user_id = row['user_id']
                # fetch user
                user_df = users_df[users_df['user_id'] == user_id]
                if user_df.empty:
                    continue
                user = user_df.iloc[0]
                email = user['email']
                if not email:
                    continue

                # find the book
                copy_id = row['copy_id']
                # we find the row in books where copy_ids has that copy
                match = books_df[books_df['copy_ids'].str.contains(copy_id, na=False)]
                if match.empty:
                    continue
                book = match.iloc[0]
                subject = "Library Book Reminder"
                name = user['name']
                body = ""

                if days_to_due == 3:
                    body = f"dear {name},\n\nthis is a reminder that your borrowed book:\n '{book['title']}' by {book['author']}\n is due in 3 days. please return on time."
                elif days_to_due == 0:
                    body = f"dear {name},\n\nthis is a reminder that your borrowed book:\n '{book['title']}' by {book['author']}'\n is due today. please return it promptly."
                else:  # days_to_due == -3
                    body = f"dear {name},\n\nyour borrowed book:\n '{book['title']}' by {book['author']}\n is 3 days overdue. please return it asap."

                self.send_email(email, subject, body)
            except Exception as e:
                print("reminder error =>", e)

    def send_debug_email(self, to_address):
        """
        let admin test emailing a custom email not in db
        """
        subject = "Test Email from the Library System"
        body = "hello,\n\nthis is a debug/test email from the library management system."
        ok = self.send_email(to_address, subject, body)
        return ok
