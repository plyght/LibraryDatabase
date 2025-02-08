import streamlit as st
import pandas as pd
from utils.barcode_scanner import BarcodeScanner
from utils.database import Database
from utils.google_forms import GoogleFormsHandler
import cv2
import os

# Initialize components
db = Database()
scanner = BarcodeScanner()
forms_handler = GoogleFormsHandler()

def check_admin_auth():
    """Check if admin is authenticated"""
    return st.session_state.get('admin_authenticated', False)

def admin_login():
    """Handle admin login"""
    st.header("Admin Login")

    with st.form("admin_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if (username == os.environ.get('ADMIN_USERNAME') and 
                password == os.environ.get('ADMIN_PASSWORD')):
                st.session_state.admin_authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

def main():
    st.title("Library Management System")

    # Sidebar for navigation
    menu = st.sidebar.selectbox(
        "Menu",
        ["Home", "Scan Books", "Search Books", "Admin Panel"]
    )

    if menu == "Home":
        show_home()
    elif menu == "Scan Books":
        show_scanner()
    elif menu == "Search Books":
        show_search()
    elif menu == "Admin Panel":
        if not check_admin_auth():
            admin_login()
        else:
            show_admin()
            if st.sidebar.button("Logout"):
                st.session_state.admin_authenticated = False
                st.rerun()

def show_home():
    st.header("Welcome to the Library Management System")
    st.write("""
    - Use the scanner to add new books
    - Search for available books
    - Check out books using your ID
    - Admin panel for management
    """)

    # Display embedded checkout form instead of external link
    forms_handler.get_checkout_form()

def show_scanner():
    st.header("Barcode Scanner")

    if st.button("Start Scanner"):
        result = scanner.scan_barcode()
        if result:
            st.success(f"Barcode detected: {result}")
            book_info = db.get_book(result)
            if book_info is not None:
                st.write("Book Information:")
                st.write(book_info)
            else:
                st.warning("Book not found in database")

                # Add new book form
                if check_admin_auth():  # Only show add book form to admin
                    with st.form("new_book"):
                        title = st.text_input("Book Title")
                        author = st.text_input("Author")
                        copies = st.number_input("Number of Copies", min_value=1, value=1)

                        if st.form_submit_button("Add Book"):
                            db.add_book(result, title, author, copies)
                            st.success("Book added successfully!")
                else:
                    st.info("Please contact an administrator to add this book to the system.")

def show_search():
    st.header("Search Books")

    search_term = st.text_input("Search by title or author")
    if search_term:
        results = db.search_books(search_term)
        if not results.empty:
            st.write(results)
        else:
            st.info("No books found")

def show_admin():
    st.header("Admin Panel")

    tab1, tab2, tab3, tab4 = st.tabs(["Books", "Users", "Checkouts", "Notifications"])

    with tab1:
        st.subheader("Book Management")
        st.write("Scan a book's barcode to add it to the database:")
        if st.button("Start Barcode Scanner"):
            result = scanner.scan_barcode()
            if result:
                st.success(f"Barcode detected: {result}")
                book_info = db.get_book(result)
                if book_info is not None:
                    st.write("Book already in database:")
                    st.write(book_info)
                else:
                    with st.form("new_book_admin"):
                        title = st.text_input("Book Title")
                        author = st.text_input("Author")
                        copies = st.number_input("Number of Copies", min_value=1, value=1)

                        if st.form_submit_button("Add Book"):
                            db.add_book(result, title, author, copies)
                            st.success("Book added successfully!")

        st.divider()
        books = db.get_all_books()
        st.write(books)

    with tab2:
        st.subheader("User Management")
        users = db.get_all_users()
        st.write(users)

        with st.form("new_user"):
            name = st.text_input("User Name")
            email = st.text_input("User Email")
            if st.form_submit_button("Generate User ID"):
                if name and email:
                    user_id = db.add_user(name, email)
                    st.success(f"User ID generated: {user_id}")
                else:
                    st.error("Please fill in both name and email")

    with tab3:
        st.subheader("Checkout Management")
        checkouts = db.get_all_checkouts()
        st.write(checkouts)

    with tab4:
        st.subheader("Overdue Notifications")
        if st.button("Send Overdue Notifications"):
            from utils.notifications import NotificationSystem
            notification_system = NotificationSystem()
            notification_system.check_overdue_books(db)
            st.success("Overdue notifications sent!")

if __name__ == "__main__":
    main()