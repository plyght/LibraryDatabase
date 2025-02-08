import pandas as pd
import uuid
import os

class Database:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.books_file = os.path.join(base_dir, "..", "data", "books.csv")
        self.users_file = os.path.join(base_dir, "..", "data", "users.csv")
        self.checkouts_file = os.path.join(base_dir, "..", "data", "checkouts.csv")

        # ensure data directory
        os.makedirs(os.path.join(base_dir, "..", "data"), exist_ok=True)
        self._initialize_files()

    def _initialize_files(self):
        """create empty csvs if not present"""
        if not os.path.exists(self.books_file):
            pd.DataFrame(columns=[
                'barcode', 'title', 'author', 'total_copies',
                'available_copies', 'copy_ids'
            ]).to_csv(self.books_file, index=False)

        if not os.path.exists(self.users_file):
            pd.DataFrame(columns=['user_id','name','email']).to_csv(self.users_file, index=False)

        if not os.path.exists(self.checkouts_file):
            pd.DataFrame(columns=['checkout_id','user_id','copy_id','checkout_date','due_date','return_date']).to_csv(self.checkouts_file, index=False)

    def add_book(self, barcode, title, author, copies):
        """
        if this barcode already exists, we treat it as the same book,
        increment total_copies & available_copies, and merge copy_ids.
        if the user gave a new title/author that's non-empty, we update them.
        """
        print(f"DEBUG add_book => barcode:{barcode}, title:{title}, author:{author}, copies:{copies}")

        # make sure copies is an int
        copies = int(copies)

        books_df = pd.read_csv(self.books_file)
        # ensure barcode is string
        books_df['barcode'] = books_df['barcode'].astype(str)

        # see if there's a row for this barcode
        existing = books_df[books_df['barcode'] == str(barcode)]
        if not existing.empty:
            # we found an existing entry => merge
            idx = existing.index[0]
            row = books_df.loc[idx]
            current_total = int(row['total_copies'])
            current_available = int(row['available_copies'])

            # parse existing copy_ids
            current_ids = []
            if isinstance(row['copy_ids'], str) and row['copy_ids'].strip():
                current_ids = row['copy_ids'].split(',')

            # generate new copy IDs
            new_ids = [str(uuid.uuid4()) for _ in range(copies)]
            merged_ids = current_ids + new_ids

            # update
            books_df.at[idx, 'title'] = title if title else row['title']
            books_df.at[idx, 'author'] = author if author else row['author']
            books_df.at[idx, 'total_copies'] = current_total + copies
            books_df.at[idx, 'available_copies'] = current_available + copies
            books_df.at[idx, 'copy_ids'] = ','.join(merged_ids)

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

        # save
        books_df.to_csv(self.books_file, index=False)
        print("DEBUG: wrote to csv. verifying read-back.")
        updated = pd.read_csv(self.books_file)
        print(updated.tail())

    def get_book(self, barcode):
        books_df = pd.read_csv(self.books_file)
        books_df['barcode'] = books_df['barcode'].astype(str)
        found = books_df[books_df['barcode'] == str(barcode)]
        if found.empty:
            print(f"DEBUG get_book => no match for {barcode}")
            return None
        return found.to_dict('records')[0]

    def search_books(self, term):
        books_df = pd.read_csv(self.books_file)
        # simple partial search
        return books_df[
            books_df['title'].str.contains(term, case=False, na=False) |
            books_df['author'].str.contains(term, case=False, na=False)
        ]

    def add_user(self, name, email):
        users_df = pd.read_csv(self.users_file)
        user_id = str(uuid.uuid4())[:8]
        new_user = pd.DataFrame([{
            'user_id': user_id,
            'name': name,
            'email': email
        }])
        users_df = pd.concat([users_df, new_user], ignore_index=True)
        users_df.to_csv(self.users_file, index=False)
        return user_id

    def get_all_books(self):
        return pd.read_csv(self.books_file)

    def get_all_users(self):
        return pd.read_csv(self.users_file)

    def get_all_checkouts(self):
        return pd.read_csv(self.checkouts_file)
