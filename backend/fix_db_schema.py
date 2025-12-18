import sqlite3

def fix_database():
    db_path = "sql_app.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists in documents
        cursor.execute("PRAGMA table_info(documents)")
        columns = [info[1] for info in cursor.fetchall()]
        if "session_id" not in columns:
            print("Adding session_id column to documents table...")
            cursor.execute("ALTER TABLE documents ADD COLUMN session_id TEXT DEFAULT 'default'")
        else:
            print("session_id column already exists in documents table.")

        # Check if column exists in search_logs
        cursor.execute("PRAGMA table_info(search_logs)")
        columns = [info[1] for info in cursor.fetchall()]
        if "session_id" not in columns:
            print("Adding session_id column to search_logs table...")
            cursor.execute("ALTER TABLE search_logs ADD COLUMN session_id TEXT DEFAULT 'default'")
        else:
            print("session_id column already exists in search_logs table.")

        conn.commit()
        print("Database schema update completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()
