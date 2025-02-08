import pandas as pd
import uuid
import os

class Database:
    def __init__(self):
        self.books_file = "data/books.csv"
        self.users_file = "data/users.csv"
        self.checkouts_file = "data/checkouts.csv"

        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)

        # Initialize CSV files if they don't exist
        self._initialize_files()

    def _initialize_files(self):
        """Initialize CSV files with proper columns if they don't exist"""
        if not os.path.exists(self.books_file):
            pd.DataFrame(columns=[
                'barcode', 'title', 'author', 'total_copies',
                'available_copies', 'copy_ids'
            ]).to_csv(self.books_file, index=False)

        if not os.path.exists(self.users_file):
            pd.DataFrame(columns=[
                'user_id', 'name', 'email'  # Added email field
            ]).to_csv(self.users_file, index=False)

        if not os.path.exists(self.checkouts_file):
            pd.DataFrame(columns=[
                'checkout_id', 'user_id', 'copy_id', 'checkout_date',
                'due_date', 'return_date'
            ]).to_csv(self.checkouts_file, index=False)

    def add_book(self, barcode, title, author, copies):
        """Add a new book to the database"""
        books_df = pd.read_csv(self.books_file)
        
        # Generate unique copy IDs
        copy_ids = [str(uuid.uuid4()) for _ in range(copies)]
        
        new_book = pd.DataFrame([{
            'barcode': barcode,
            'title': title,
            'author': author,
            'total_copies': copies,
            'available_copies': copies,
            'copy_ids': ','.join(copy_ids)
        }])
        
        books_df = pd.concat([books_df, new_book], ignore_index=True)
        books_df.to_csv(self.books_file, index=False)

    def get_book(self, barcode):
        """Get book information by barcode"""
        books_df = pd.read_csv(self.books_file)
        # Convert barcode column to string and ensure proper comparison
        books_df['barcode'] = books_df['barcode'].astype(str)
        book = books_df[books_df['barcode'] == str(barcode)]

        if book.empty:
            print(f"Debug: Book not found for barcode {barcode}")
            print(f"Debug: Available barcodes: {books_df['barcode'].tolist()}")
            return None

        return book.to_dict('records')[0]

    def search_books(self, term):
        """Search books by title or author"""
        books_df = pd.read_csv(self.books_file)
        return books_df[
            books_df['title'].str.contains(term, case=False, na=False) |
            books_df['author'].str.contains(term, case=False, na=False)
        ]

    def add_user(self, name, email):
        """Add a new user and generate ID"""
        users_df = pd.read_csv(self.users_file)
        user_id = str(uuid.uuid4())[:8]

        new_user = pd.DataFrame([{
            'user_id': user_id,
            'name': name,
            'email': email  # Added email field
        }])

        users_df = pd.concat([users_df, new_user], ignore_index=True)
        users_df.to_csv(self.users_file, index=False)
        return user_id

    def get_all_books(self):
        """Get all books"""
        return pd.read_csv(self.books_file)

    def get_all_users(self):
        """Get all users"""
        return pd.read_csv(self.users_file)

    def get_all_checkouts(self):
        """Get all checkouts"""
        return pd.read_csv(self.checkouts_file)