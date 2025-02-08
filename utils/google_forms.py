import streamlit as st
from datetime import datetime, timedelta
import uuid

class GoogleFormsHandler:
    def __init__(self):
        self.checkout_duration_days = 14  # Default checkout period

    def get_checkout_form(self):
        """Display an embedded checkout form"""
        st.subheader("Book Checkout Form")

        with st.form("checkout_form"):
            user_id = st.text_input("Your User ID")
            barcode = st.text_input("Book Barcode")

            submitted = st.form_submit_button("Checkout Book")

            if submitted:
                if not user_id or not barcode:
                    st.error("Please fill in all fields")
                    return None
                return self.process_checkout(user_id, barcode)

        return None

    def process_checkout(self, user_id, barcode):
        """Process the checkout request"""
        from utils.database import Database  # Import here to avoid circular imports

        db = Database()

        # Verify user exists with improved error handling
        users_df = db.get_all_users()
        user_exists = users_df['user_id'].astype(str).str.strip() == str(user_id).strip()

        if not user_exists.any():
            st.error(f"Invalid User ID: {user_id}. Please check your ID and try again.")
            return False

        # Verify book exists and is available
        book = db.get_book(barcode)
        if not book:
            st.error(f"Book with barcode {barcode} not found")
            return False

        # Get an available copy_id
        copy_ids = book['copy_ids'].split(',')

        # Read current checkouts to find available copy
        checkouts_df = db.get_all_checkouts()
        checked_out_copies = checkouts_df[
            (checkouts_df['return_date'].isna()) & 
            (checkouts_df['copy_id'].isin(copy_ids))
        ]['copy_id'].tolist()

        available_copies = [cid for cid in copy_ids if cid not in checked_out_copies]
        if not available_copies:
            st.error(f"No copies of '{book['title']}' are currently available. All copies are checked out.")
            return False

        # Process checkout
        checkout_date = datetime.now()
        due_date = checkout_date + timedelta(days=self.checkout_duration_days)

        # Add checkout record
        checkout_data = {
            'checkout_id': str(uuid.uuid4())[:8],
            'user_id': user_id,
            'copy_id': available_copies[0],
            'checkout_date': checkout_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'return_date': None
        }

        # Append to checkouts.csv
        import pandas as pd
        checkouts_df = pd.concat([
            checkouts_df, 
            pd.DataFrame([checkout_data])
        ], ignore_index=True)
        checkouts_df.to_csv('data/checkouts.csv', index=False)

        st.success(f"""
        Checkout successful!
        Book: {book['title']}
        Due date: {due_date.strftime('%Y-%m-%d')}
        Please return the book by the due date to avoid late fees.
        """)
        return True

    def get_checkout_form_link(self):
        """Get checkout form instructions"""
        return """
        ### Book Checkout
        To check out a book:
        1. Enter your User ID
        2. Enter the book's barcode
        3. Submit the form

        Your checkout will be processed immediately.
        """