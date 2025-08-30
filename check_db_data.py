import sqlite3
import os

DB_PATH = os.path.join('data', 'database.sqlite')

def check_data():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("--- Checking Device ID: 3 ---")
        cursor.execute("SELECT * FROM devices WHERE id = ?", (3,))
        device = cursor.fetchone()
        if device:
            # Print with column names for clarity
            cols = [description[0] for description in cursor.description]
            print(dict(zip(cols, device)))
        else:
            print("Device with ID 3 not found.")

        print("\n--- Checking Connection ID: 4 ---")
        cursor.execute("SELECT * FROM connections WHERE id = ?", (4,))
        connection = cursor.fetchone()
        if connection:
            cols = [description[0] for description in cursor.description]
            print(dict(zip(cols, connection)))
        else:
            print("Connection with ID 4 not found.")

        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    check_data()
