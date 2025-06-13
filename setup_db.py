"""
Database setup script.

This script creates and populates an example SQLite database for testing.
"""
import os
import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def setup_database(db_path: str = "example.db") -> None:
    """
    Set up the example database.
    
    Args:
        db_path: Path to the database file
    """
    try:
        logger.info(f"Setting up example database at {db_path}")
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT,
            in_stock BOOLEAN DEFAULT 1
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (order_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
        """)
        
        # Insert sample data
        # Users
        users = [
            ("jsmith", "john.smith@example.com", "John", "Smith"),
            ("ajones", "alice.jones@example.com", "Alice", "Jones"),
            ("mgarcia", "maria.garcia@example.com", "Maria", "Garcia"),
            ("rwilson", "robert.wilson@example.com", "Robert", "Wilson"),
            ("slee", "sarah.lee@example.com", "Sarah", "Lee")
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO users (username, email, first_name, last_name) VALUES (?, ?, ?, ?)",
            users
        )
        
        # Products
        products = [
            ("Laptop", "High-performance laptop", 1299.99, "Electronics"),
            ("Smartphone", "Latest model smartphone", 799.99, "Electronics"),
            ("Headphones", "Noise-cancelling headphones", 199.99, "Audio"),
            ("Coffee Maker", "Automatic coffee maker", 89.99, "Kitchen"),
            ("Desk Chair", "Ergonomic office chair", 249.99, "Furniture"),
            ("Fitness Tracker", "Water-resistant fitness tracker", 129.99, "Wearables"),
            ("Blender", "High-speed blender", 79.99, "Kitchen"),
            ("Wireless Mouse", "Bluetooth wireless mouse", 49.99, "Accessories"),
            ("Tablet", "10-inch tablet", 399.99, "Electronics"),
            ("Backpack", "Water-resistant backpack", 59.99, "Accessories")
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO products (name, description, price, category) VALUES (?, ?, ?, ?)",
            products
        )
        
        # Orders
        orders = [
            (1, "2023-01-15", 1299.99, "completed"),
            (1, "2023-03-20", 249.99, "completed"),
            (2, "2023-02-10", 989.98, "completed"),
            (3, "2023-04-05", 279.98, "shipped"),
            (4, "2023-03-30", 399.99, "pending"),
            (5, "2023-04-10", 129.99, "processing")
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO orders (user_id, order_date, total_amount, status) VALUES (?, ?, ?, ?)",
            orders
        )
        
        # Order Items
        order_items = [
            (1, 1, 1, 1299.99),
            (2, 5, 1, 249.99),
            (3, 2, 1, 799.99),
            (3, 3, 1, 199.99),
            (4, 4, 1, 89.99),
            (4, 7, 1, 79.99),
            (4, 8, 2, 49.99),
            (5, 9, 1, 399.99),
            (6, 6, 1, 129.99)
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
            order_items
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        logger.info("Database setup complete")
        
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise


if __name__ == "__main__":
    setup_database() 