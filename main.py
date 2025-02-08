import streamlit as st
import pandas as pd
import os
import requests
import cv2

from utils.barcode_scanner import BarcodeScanner
from utils.database import Database
from utils.google_forms import GoogleFormsHandler

db = Database()
scanner = BarcodeScanner()
forms_handler = GoogleFormsHandler()

def check_admin_auth():
    return st.session_state.get('admin_authenticated', False)

def admin_login():
    st.header("admin login")
    with st.form("admin_login"):
        username = st.text_input("username")
        password = st.text_input("password", type="password")
        submitted = st.form_submit_button("login")
        if submitted:
            if username == "admin" and password == "admin":
                st.session_state.admin_authenticated = True
                st.success("login successful!")
                st.rerun()
            else:
                st.error("invalid credentials")

def fetch_book_info_from_isbn(isbn):
    # quick check if this is numeric or not
    if not isbn or not isbn.isdigit():
        return "", ""
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=data&format=json"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        key = f"ISBN:{isbn}"
        if key in data:
            record = data[key]
            authors = record.get("authors", [])
            author_name = authors[0]["name"] if authors else "unknown"
            return record.get("title", ""), author_name
        else:
            return "", ""
    except:
        return "", ""

def main():
    st.title("library management system")

    menu = st.sidebar.selectbox("menu", ["home", "scan books", "search books", "admin panel"])
    if menu == "home":
        show_home()
    elif menu == "scan books":
        show_scanner()
    elif menu == "search books":
        show_search()
    elif menu == "admin panel":
        if not check_admin_auth():
            admin_login()
        else:
            show_admin()
            if st.sidebar.button("logout"):
                st.session_state.admin_authenticated = False
                st.rerun()

def show_home():
    st.header("welcome to the library management system")
    st.write("""
    - use the scanner to add new books
    - search for available books
    - check out books using your id
    - admin panel for management
    """)
    forms_handler.get_checkout_form()

def show_scanner():
    """
    user can scan. if it finds a book in db, show it.
    if not, attempt to fetch from open library + let them add it.
    only one final table shown after the add
    """
    st.header("barcode scanner")
    if st.button("start scanner"):
        result = scanner.scan_barcode()
        if result:
            st.success(f"barcode detected: {result}")

            # attempt open library fetch
            fetched_title, fetched_author = fetch_book_info_from_isbn(result)
            if not fetched_title and not fetched_author:
                st.warning("open library could not find a title/author; fill them in manually")

            # see if it already exists
            book_info = db.get_book(result)
            if book_info:
                # we can still allow user to add more copies if they want
                st.info("this barcode is already in the db, but you can add more copies or update info below.")
                prefill_title = book_info['title']
                prefill_author = book_info['author']

                if fetched_title:  # if we found better data
                    prefill_title = fetched_title
                if fetched_author:
                    prefill_author = fetched_author

                if check_admin_auth():
                    with st.form("update_scanner_form"):
                        new_title = st.text_input("book title", value=prefill_title)
                        new_author = st.text_input("author", value=prefill_author)
                        copies = st.number_input("copies to add", min_value=1, value=1)
                        addit = st.form_submit_button("update / add more copies")
                        if addit:
                            try:
                                db.add_book(result, new_title, new_author, copies)
                                st.success("updated/added copies successfully!")
                            except Exception as e:
                                st.error(f"error: {str(e)}")
                else:
                    st.info("login as admin to add more copies.")
            else:
                # new isbn
                st.warning("book not found in db. let's add it now.")
                if check_admin_auth():
                    with st.form("new_scanner_form"):
                        default_title = fetched_title
                        default_author = fetched_author
                        newtitle = st.text_input("book title", value=default_title)
                        newauthor = st.text_input("author", value=default_author)
                        copies = st.number_input("number of copies", min_value=1, value=1)
                        submitted = st.form_submit_button("add book")
                        if submitted:
                            try:
                                db.add_book(result, newtitle, newauthor, copies)
                                st.success("book added!")
                            except Exception as e:
                                st.error(f"error => {str(e)}")
                else:
                    st.info("please contact admin to add this book.")

        # after scanning or adding, show the final db
        st.write("books in db:")
        st.write(db.get_all_books())

def show_search():
    st.header("search books")
    term = st.text_input("search by title or author")
    if term:
        results = db.search_books(term)
        if not results.empty:
            st.write(results)
        else:
            st.info("no books found")

def show_admin():
    st.header("admin panel")
    tab1, tab2, tab3, tab4 = st.tabs(["books", "users", "checkouts", "notifications"])

    with tab1:
        st.subheader("book management")

        # scan with webcam
        if st.button("scan barcode (webcam)"):
            scanned = scanner.scan_barcode()
            if scanned:
                st.session_state["admin_isbn"] = scanned
                st.success(f"scanned => {scanned}")
                t, a = fetch_book_info_from_isbn(scanned)
                if not t and not a:
                    st.warning("couldn't find data on open library; fill in below")
                st.session_state["admin_prefill_title"] = t
                st.session_state["admin_prefill_author"] = a

        st.write("or type isbn below, then fetch metadata if you want.")
        typed_isbn = st.text_input("barcode (isbn)", value=st.session_state.get("admin_isbn", ""))

        if st.button("fetch from open library"):
            t, a = fetch_book_info_from_isbn(typed_isbn)
            st.session_state["admin_isbn"] = typed_isbn
            st.session_state["admin_prefill_title"] = t
            st.session_state["admin_prefill_author"] = a
            if not t and not a:
                st.warning("not found in open library; fill in manually below")
            else:
                st.success(f"fetched => title:'{t}', author:'{a}'")

        with st.form("admin_add_book_form"):
            def_t = st.session_state.get("admin_prefill_title", "")
            def_a = st.session_state.get("admin_prefill_author", "")
            final_t = st.text_input("book title", value=def_t)
            final_a = st.text_input("author", value=def_a)
            final_c = st.number_input("copies to add", min_value=1, value=1)
            sub_btn = st.form_submit_button("add/update book in db")

            if sub_btn:
                try:
                    db.add_book(typed_isbn, final_t, final_a, final_c)
                    st.success("book added or updated. see below")
                except Exception as e:
                    st.error(f"error => {str(e)}")

        st.write("books in db:")
        st.write(db.get_all_books())

    with tab2:
        st.subheader("user management")
        st.write(db.get_all_users())

        with st.form("new_user"):
            name = st.text_input("user name")
            email = st.text_input("user email")
            if st.form_submit_button("generate user id"):
                if name and email:
                    user_id = db.add_user(name, email)
                    st.success(f"user id => {user_id}")
                else:
                    st.error("please fill in name and email")

    with tab3:
        st.subheader("checkout management")
        st.write(db.get_all_checkouts())

    with tab4:
        st.subheader("overdue notifications")
        if st.button("send overdue notifications"):
            from utils.notifications import NotificationSystem
            ns = NotificationSystem()
            ns.check_overdue_books(db)
            st.success("overdue notifications sent!")

if __name__ == "__main__":
    main()
