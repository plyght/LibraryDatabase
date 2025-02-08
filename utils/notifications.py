import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pandas as pd

class NotificationSystem:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.environ.get('LIBRARY_EMAIL')
        self.sender_password = os.environ.get('LIBRARY_EMAIL_PASSWORD')
        
    def send_email(self, recipient_email, subject, body):
        """Send an email using SMTP"""
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "plain"))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            return True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False
            
    def check_overdue_books(self, db):
        """Check for overdue books and send notifications"""
        today = datetime.now().date()
        checkouts_df = pd.read_csv(db.checkouts_file)
        users_df = pd.read_csv(db.users_file)
        books_df = pd.read_csv(db.books_file)
        
        # Filter for overdue and unreturned books
        overdue_checkouts = checkouts_df[
            (pd.to_datetime(checkouts_df['due_date']).dt.date < today) & 
            (checkouts_df['return_date'].isna())
        ]
        
        for _, checkout in overdue_checkouts.iterrows():
            user = users_df[users_df['user_id'] == checkout['user_id']].iloc[0]
            book = books_df[books_df['copy_ids'].str.contains(checkout['copy_id'])].iloc[0]
            
            if user['email']:  # Only send if email exists
                subject = "Library Book Overdue Notice"
                body = f"""
                Dear {user['name']},
                
                The following book is overdue:
                
                Title: {book['title']}
                Author: {book['author']}
                Due Date: {checkout['due_date']}
                
                Please return the book as soon as possible to avoid any late fees.
                
                Best regards,
                Library Management System
                """
                
                self.send_email(user['email'], subject, body)
