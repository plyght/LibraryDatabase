import streamlit as st
import pandas as pd
import os
import requests
import uuid
import cv2
import datetime

from utils.barcode_scanner import BarcodeScanner
from utils.database import Database
from utils.notifications import NotificationSystem

print("DEBUG [top-level]: main.py is loading...")

db = Database()
scanner = BarcodeScanner()
notify = NotificationSystem()  # global instance

def check_admin_auth():
    return st.session_state.get('admin_authenticated', False)

def admin_login():
    print("DEBUG [admin_login]: start")
    st.header("admin login")
    with st.form("admin_login"):
        username = st.text_input("username")
        password = st.text_input("password", type="password")
        submitted = st.form_submit_button("login")
        if submitted:
            if username == "admin" and password == "admin":
                st.session_state.admin_authenticated = True
                st.success("login successful!")
                print("DEBUG [admin_login]: success")
            else:
                st.error("invalid credentials")
                print("DEBUG [admin_login]: invalid credentials")

def fetch_book_info_from_isbn(isbn):
    if not isbn or not isbn.strip().isdigit():
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
    except Exception as e:
        print(f"DEBUG [fetch_book_info_from_isbn]: error => {e}")
        return "", ""

def main():
    print("DEBUG [main()]: start in console")
    st.title("library management system")

    menu = st.sidebar.selectbox("menu", ["home (checkout)", "search books", "admin panel"])
    if menu == "home (checkout)":
        show_home_checkout()
    elif menu == "search books":
        show_search()
    elif menu == "admin panel":
        if not check_admin_auth():
            admin_login()
        else:
            show_admin()

    print("DEBUG [main()]: end in console")

def show_home_checkout():
    st.header("book checkout")
    if st.sidebar.button("change user id"):
        st.session_state.pop("current_user_id", None)
        st.sidebar.success("user id cleared.")
        return

    if "current_user_id" not in st.session_state:
        st.subheader("login / create account")
        action = st.radio(
            "select an action",
            ["sign in with user id", "create new account", "forgot user id?"]
        )

        if action == "sign in with user id":
            typed_id = st.text_input("existing user id")
            if st.button("sign in"):
                if typed_id.strip():
                    users_df = db.get_all_users()
                    match = users_df[users_df['user_id'].astype(str).str.strip() == typed_id.strip()]
                    if match.empty:
                        st.error("that user id doesn't exist. check or create new.")
                    else:
                        st.session_state["current_user_id"] = typed_id.strip()
                        st.success(f"welcome back, user {typed_id}!")
                else:
                    st.error("please type a user id")

        elif action == "create new account":
            new_name = st.text_input("your name")
            new_email = st.text_input("your email")
            if st.button("create account"):
                if new_name and new_email:
                    allu = db.get_all_users()
                    dup = allu[allu['email'].str.lower().str.strip() == new_email.lower().strip()]
                    if not dup.empty:
                        st.error("an account with that email already exists!")
                        if st.button("email me my user id"):
                            user_id = dup.iloc[0]['user_id']
                            subject = "Your Library User ID"
                            body = f"Hello,\n\nYour user id is: {user_id}\n\nRegards,\nLibrary"
                            print(f"DEBUG [email_user_id]: sending user id {user_id} to {new_email.strip()}")
                            ok = notify.send_email(new_email.strip(), subject, body)
                            if ok:
                                st.success(f"emailed your user id to {new_email.strip()}")
                                print("DEBUG [email_user_id]: success => email sent")
                            else:
                                st.error("failed to send email. check logs or smtp config.")
                                print("DEBUG [email_user_id]: fail => see logs.")
                    else:
                        new_id = db.add_user(new_name.strip(), new_email.strip())
                        st.session_state["current_user_id"] = new_id
                        st.success(f"new account created => user id: {new_id}")
                else:
                    st.error("please enter name & email")

        else:  # forgot user id
            forgot_email = st.text_input("enter your email to retrieve user id")
            if st.button("send user id to my email"):
                if forgot_email.strip():
                    users_df = db.get_all_users()
                    match = users_df[users_df['email'].str.lower().str.strip() == forgot_email.lower().strip()]
                    if match.empty:
                        st.error("no user found with that email.")
                    else:
                        user_id = match.iloc[0]['user_id']
                        subject = "Your Library User ID"
                        body = f"Hello,\n\nYour user id is: {user_id}\n\nRegards,\nLibrary"
                        print(f"DEBUG [forgot_user_id]: sending user id {user_id} to {forgot_email.strip()}")
                        success = notify.send_email(forgot_email.strip(), subject, body)
                        if success:
                            st.success(f"emailed your user id to {forgot_email.strip()}")
                            print("DEBUG [forgot_user_id]: success => email sent")
                        else:
                            st.error("failed to send email. see logs.")
                            print("DEBUG [forgot_user_id]: fail => see logs.")
                else:
                    st.error("please enter an email")

        if "current_user_id" not in st.session_state:
            st.warning("you must be signed in to proceed with checkout.")
            return
    else:
        st.info(f"you are currently user id => {st.session_state['current_user_id']}")

    st.subheader("checkout a book")

    if st.button("scan barcode now"):
        scanned = scanner.scan_barcode()
        if scanned:
            st.session_state["checkout_barcode"] = scanned
            st.success(f"scanned => {scanned}")

    typed_barcode = st.text_input("book barcode (isbn)", value=st.session_state.get("checkout_barcode",""))
    if st.button("fetch open library data"):
        t,a = fetch_book_info_from_isbn(typed_barcode)
        if t or a:
            st.write(f"**title**: {t}, **author**: {a}")
        else:
            st.warning("not found in open library or invalid isbn")

    if st.button("checkout book"):
        user_id = st.session_state["current_user_id"]
        book = db.get_book(typed_barcode)
        if not book:
            st.error("that book isn't in the db. ask an admin to add it.")
            return

        copy_id = db.checkout_copy(typed_barcode)
        if not copy_id:
            st.error("no copies available or invalid. cannot checkout.")
            return

        now = datetime.datetime.now()
        due_date = now + datetime.timedelta(days=14)
        co_id = str(uuid.uuid4())[:8]
        db.record_checkout(
            checkout_id=co_id,
            user_id=user_id,
            copy_id=copy_id,
            date_str=now.strftime("%Y-%m-%d"),
            due_str=due_date.strftime("%Y-%m-%d")
        )
        st.success(f"checked out '{book['title']}' by {book['author']} — due {due_date.strftime('%Y-%m-%d')}")

    st.write("books in db (simplified):")
    all_books = db.get_all_books()
    if all_books.empty:
        st.info("no books yet.")
    else:
        user_view = all_books[['title','author','total_copies','available_copies']]
        st.dataframe(user_view)

def show_search():
    st.header("search books")
    term = st.text_input("search by title or author")
    if term:
        results = db.search_books(term)
        if results.empty:
            st.info("no books found for that search.")
        else:
            st.dataframe(results[['title','author','total_copies','available_copies']])

def show_admin():
    st.header("admin panel")

    tab1, tab2, tab3, tab4 = st.tabs(["books", "users", "checkouts", "notifications"])

    # -- books --
    with tab1:
        st.subheader("book management")
        if st.button("scan new book"):
            scanned = scanner.scan_barcode()
            if scanned:
                st.session_state["admin_isbn"] = scanned
                st.success(f"scanned => {scanned}")
                t,a = fetch_book_info_from_isbn(scanned)
                st.session_state["admin_title"] = t
                st.session_state["admin_author"] = a

        typed_isbn = st.text_input("barcode (isbn)", value=st.session_state.get("admin_isbn",""))
        if st.button("fetch from open library"):
            t,a = fetch_book_info_from_isbn(typed_isbn)
            st.session_state["admin_isbn"] = typed_isbn
            st.session_state["admin_title"] = t
            st.session_state["admin_author"] = a
            if not t and not a:
                st.warning("not found in open library. fill in manually below")

        with st.form("admin_add_book"):
            def_t = st.session_state.get("admin_title","")
            def_a = st.session_state.get("admin_author","")
            fin_t = st.text_input("book title", value=def_t)
            fin_a = st.text_input("author", value=def_a)
            fin_c = st.number_input("number of copies to add", min_value=1, value=1)
            ssub = st.form_submit_button("add/update book")
            if ssub:
                db.add_book(typed_isbn.strip(), fin_t.strip(), fin_a.strip(), fin_c)
                st.success("book added or updated in db")

        st.write("full books in db (admin view):")
        st.dataframe(db.get_all_books())

    # -- users --
    with tab2:
        st.subheader("user management")
        st.write(db.get_all_users())
        with st.form("add_user"):
            nm = st.text_input("name")
            em = st.text_input("email")
            sb = st.form_submit_button("create user")
            if sb:
                if nm and em:
                    allu = db.get_all_users()
                    existing = allu[allu['email'].str.lower().str.strip() == em.lower().strip()]
                    if not existing.empty:
                        ex_uid = existing.iloc[0]['user_id']
                        st.warning(f"that email is already in use. user id => {ex_uid}")
                        st.info("if you want, you can send them an email with their user id:")
                        if st.button("email them their user id", key="email_existing_user"):
                            subject = "Your Library User ID"
                            body = f"Hello,\n\nYour user id is: {ex_uid}\n\nRegards,\nLibrary"
                            print(f"DEBUG [admin_email_user_id]: about to email user id {ex_uid} to {em.strip()}")
                            ok = notify.send_email(em.strip(), subject, body)
                            if ok:
                                st.success(f"we emailed the user id to {em.strip()}")
                                print("DEBUG [admin_email_user_id]: success => email sent")
                            else:
                                st.error("failed to send email. see logs.")
                                print("DEBUG [admin_email_user_id]: failed => see logs.")
                    else:
                        new_id = db.add_user(nm.strip(), em.strip())
                        st.success(f"user created => {new_id}")
                else:
                    st.error("fill name & email")

    # -- checkouts --
    with tab3:
        st.subheader("checkouts + checkins")
        st.write("recent events (checkin/checkout):")
        recents = db.get_recent_events(10)
        st.dataframe(recents)

        st.write("all checkout records:")
        st.dataframe(db.get_all_checkouts())

        st.write("check in a book copy (by copy_id):")
        copy_id_input = st.text_input("copy id")
        if st.button("check in copy"):
            ok = db.check_in_copy(copy_id_input.strip())
            if ok:
                st.success("checked in successfully!")
            else:
                st.error("check-in failed. maybe invalid copy id or already returned.")

            st.write("updated events:")
            st.dataframe(db.get_recent_events(10))
            st.write("updated checkouts:")
            st.dataframe(db.get_all_checkouts())
            st.write("updated books:")
            st.dataframe(db.get_all_books())

    # -- notifications & email settings --
    with tab4:
        st.subheader("notifications & email settings")
        st.write("send reminders for 3 days before due, due day, 3 days overdue.")
        if st.button("send reminder/overdue emails"):
            notify.check_reminders(db)
            st.success("reminders triggered. check console logs for details")

        st.write("---")
        st.write("**set or update smtp credentials** (gmail account & password)**")
        with st.form("smtp_creds"):
            default_email = notify.sender_email or ""
            default_pass = notify.sender_password or ""
            new_email = st.text_input("library email account", value=default_email)
            new_pass = st.text_input("library email password", type="password", value=default_pass)
            sbc = st.form_submit_button("save email credentials")
            if sbc:
                print(f"DEBUG [smtp_creds]: admin typed email '{new_email}' pass len = {len(new_pass)}")
                notify.update_credentials(new_email.strip(), new_pass.strip())
                st.success("updated smtp credentials in memory. try sending test email below.")

        st.write("---\n**debug email test**:")
        debug_email = st.text_input("email for test message")
        if st.button("send debug email"):
            if debug_email.strip():
                print(f"DEBUG [admin debug email]: about to call send_debug_email for {debug_email.strip()}")
                ok = notify.send_debug_email(debug_email.strip())
                if ok:
                    st.success("debug email sent!")
                    print("DEBUG [admin debug email]: success => email was sent (returned True)")
                else:
                    st.error("failed to send debug email. see console logs.")
                    print("DEBUG [admin debug email]: returned False => check logs")
            else:
                st.error("please enter a valid email address")

if __name__ == "__main__":
    print("DEBUG [__main__]: about to call main()")
    main()
    print("DEBUG [__main__]: main() returned")
