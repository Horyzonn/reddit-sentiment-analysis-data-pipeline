from src.db.postgre_client import init_db

if __name__ == "__main__":
    init_db()
    print("Tables created successfully!")
