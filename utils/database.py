import pandas as pd
import uuid
import os
import datetime

class Database:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.books_file = os.path.join(base_dir, "..", "data", "books.csv")
        self.users_file = os.path.join(base_dir, "..", "data", "users.csv")
        self.checkouts_file = os.path.join(base_dir, "..", "data", "checkouts.csv")

        # ensure there's a data directory
        os.makedirs(os.path.join(base_dir, "..", "data"), exist_ok=True)
        self._initialize_files()

    def _initialize_files(self):
        # create empty csvs if needed
        if not os.path.exists(self.books_file):
            pd.DataFrame(columns=[
                'barcode','title','author','total_copies','available_copies','copy_ids'
            ]).to_csv(self.books_file, index=False)

        if not os.path.exists(self.users_file):
            pd.DataFrame(columns=['user_id','name','email']).to_csv(self.users_file, index=False)

        if not os.path.exists(self.checkouts_file):
            pd.DataFrame(columns=[
                'checkout_id','user_id','copy_id','checkout_date','due_date','return_date'
            ]).to_csv(self.checkouts_file, index=False)

    def add_book(self, barcode, title, author, copies):
        """
        merges copies if the book already exists by barcode.
        increments total_copies + available_copies, merges copy_ids.
        otherwise adds a new row.
        """
        copies = int(copies)
        books_df = pd.read_csv(self.books_file)
        books_df['barcode'] = books_df['barcode'].astype(str)

        existing = books_df[books_df['barcode'] == str(barcode)]
        if not existing.empty:
            idx = existing.index[0]
            row = books_df.loc[idx]
            cur_total = int(row['total_copies'])
            cur_avail = int(row['available_copies'])

            cur_ids = []
            if isinstance(row['copy_ids'], str) and row['copy_ids'].strip():
                cur_ids = row['copy_ids'].split(',')

            new_ids = [str(uuid.uuid4()) for _ in range(copies)]

            # update
            books_df.at[idx,'title'] = title if title else row['title']
            books_df.at[idx,'author'] = author if author else row['author']
            books_df.at[idx,'total_copies'] = cur_total + copies
            books_df.at[idx,'available_copies'] = cur_avail + copies
            books_df.at[idx,'copy_ids'] = ','.join(cur_ids + new_ids)
        else:
            # brand-new row
            new_ids = [str(uuid.uuid4()) for _ in range(copies)]
            new_row = pd.DataFrame([{
                'barcode': str(barcode),
                'title': title,
                'author': author,
                'total_copies': copies,
                'available_copies': copies,
                'copy_ids': ','.join(new_ids)
            }])
            books_df = pd.concat([books_df, new_row], ignore_index=True)

        books_df.to_csv(self.books_file, index=False)

    def checkout_copy(self, barcode):
        """
        tries to find a book with the given barcode, and if there's at least 1 available copy,
        decrement the availability by 1, and return the chosen copy_id. else return None.
        """
        books_df = pd.read_csv(self.books_file)
        books_df['barcode'] = books_df['barcode'].astype(str)

        match = books_df[books_df['barcode'] == str(barcode)]
        if match.empty:
            return None
        idx = match.index[0]
        row = books_df.loc[idx]

        av = int(row['available_copies'])
        if av < 1:
            return None

        # parse copy_ids
        copy_ids = row['copy_ids'].split(',') if row['copy_ids'].strip() else []
        if not copy_ids:
            return None  # no copy ids left?

        chosen_id = copy_ids[0]  # naive approach: pick first
        # decrement available
        books_df.at[idx, 'available_copies'] = av - 1
        books_df.to_csv(self.books_file, index=False)
        return chosen_id

    def get_book(self, barcode):
        df = pd.read_csv(self.books_file)
        df['barcode'] = df['barcode'].astype(str)
        row = df[df['barcode'] == str(barcode)]
        if row.empty:
            return None
        return row.to_dict('records')[0]

    def search_books(self, term):
        df = pd.read_csv(self.books_file)
        return df[
            df['title'].str.contains(term, case=False, na=False) |
            df['author'].str.contains(term, case=False, na=False)
        ]

    def add_user(self, name, email):
        users_df = pd.read_csv(self.users_file)
        user_id = str(uuid.uuid4())[:8]
        new_row = pd.DataFrame([{
            'user_id': user_id,
            'name': name,
            'email': email
        }])
        users_df = pd.concat([users_df, new_row], ignore_index=True)
        users_df.to_csv(self.users_file, index=False)
        return user_id

    def get_all_books(self):
        return pd.read_csv(self.books_file)

    def get_all_users(self):
        return pd.read_csv(self.users_file)

    def get_all_checkouts(self):
        return pd.read_csv(self.checkouts_file)

    def record_checkout(self, checkout_id, user_id, copy_id, date_str, due_str):
        df = pd.read_csv(self.checkouts_file)
        new_entry = {
            'checkout_id': checkout_id,
            'user_id': user_id,
            'copy_id': copy_id,
            'checkout_date': date_str,
            'due_date': due_str,
            'return_date': None
        }
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(self.checkouts_file, index=False)

    def check_in_copy(self, copy_id):
        """
        find an open checkout for this copy_id => set return_date => increment available_copies
        returns True if success, False if not found or already returned
        """
        checkouts_df = pd.read_csv(self.checkouts_file)
        open_checkout = checkouts_df[
            (checkouts_df['copy_id'] == copy_id) & (checkouts_df['return_date'].isna())
        ]
        if open_checkout.empty:
            return False

        # mark it returned
        idx = open_checkout.index[0]
        checkouts_df.at[idx, 'return_date'] = datetime.datetime.now().strftime("%Y-%m-%d")
        checkouts_df.to_csv(self.checkouts_file, index=False)

        # increment availability
        books_df = pd.read_csv(self.books_file)
        rowmatch = books_df[books_df['copy_ids'].str.contains(copy_id, na=False)]
        if rowmatch.empty:
            return True  # no book found, can't do anything else
        row_idx = rowmatch.index[0]
        av = int(books_df.loc[row_idx, 'available_copies'])
        books_df.at[row_idx, 'available_copies'] = av + 1
        books_df.to_csv(self.books_file, index=False)
        return True

    def get_recent_events(self, n=10):
        """
        merges checkouts with user/book data so admin can see who checked out or in
        returns up to n events sorted by date desc
        """
        import datetime

        co = pd.read_csv(self.checkouts_file)
        users = pd.read_csv(self.users_file)
        books = pd.read_csv(self.books_file)

        # build a list of events
        events = []
        for _, row in co.iterrows():
            checkout_date = row['checkout_date']
            return_date = row['return_date']
            user_id = row['user_id']
            copy_id = row['copy_id']

            # find user
            urow = users[users['user_id'] == user_id]
            user_name = "unknown"
            if not urow.empty:
                user_name = urow.iloc[0]['name']

            # find book
            brow = books[books['copy_ids'].str.contains(copy_id, na=False)]
            book_title = "unknown"
            if not brow.empty:
                book_title = brow.iloc[0]['title']

            # figure out event_date + type
            if pd.isna(return_date):
                # checkout
                event_date = checkout_date
                event_type = "checkout"
            else:
                event_date = return_date
                event_type = "checkin"

            events.append({
                "user_name": user_name,
                "book_title": book_title,
                "copy_id": copy_id,
                "event_type": event_type,
                "event_date": event_date
            })

        edf = pd.DataFrame(events)
        # parse date
        def parse_d(s):
            try:
                return datetime.datetime.strptime(s, "%Y-%m-%d")
            except:
                return datetime.datetime.min
        edf['parsed'] = edf['event_date'].apply(parse_d)
        edf = edf.sort_values('parsed', ascending=False).head(n)
        edf.drop('parsed', axis=1, inplace=True)
        return edf

