import sqlite3
import os

# Path to the database
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'chatbot.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Running migration on {DB_PATH}...")

    # Add knowledge_base column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE businesses ADD COLUMN knowledge_base TEXT")
        print("Added knowledge_base column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("knowledge_base column already exists.")
        else:
            print(f"Error adding knowledge_base: {e}")

    # Add last_trained_at column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE businesses ADD COLUMN last_trained_at DATETIME")
        print("Added last_trained_at column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("last_trained_at column already exists.")
        else:
            print(f"Error adding last_trained_at: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
