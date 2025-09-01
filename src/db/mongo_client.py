from pymongo import MongoClient, errors
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="/opt/airflow/src/.env")

def get_mongo_client():
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        return client
    except errors.ConnectionFailure as e:
        print(f"[ERROR] Could not connect to MongoDB: {e}")
        raise



def save_raw_data(collection_name, data):
    """
    Lưu danh sách dữ liệu vào MongoDB (Data Lake)
    - collection_name: tên subreddit (vd: 'Vietnam')
    - data: list các dictionary (dạng JSON)
    """
    if not data:
        print(f"[WARNING] No data to insert for {collection_name}")
        return

    try:
        client = get_mongo_client()
        db = client["reddit_raw"]  # DB lưu dữ liệu thô
        collection = db[collection_name]

        # Optional: tránh insert trùng lặp bằng cách đặt _id là post/comment id
        for item in data:
            item["_id"] = item["id"]

        result = collection.insert_many(data, ordered=False)
        print(f"[INFO] Inserted {len(result.inserted_ids)} records into '{collection_name}'")
    except errors.BulkWriteError as bwe:
        print(f"[WARNING] Some duplicate entries skipped in '{collection_name}': {bwe.details}")
    except Exception as e:
        print(f"[ERROR] Failed to insert data for '{collection_name}': {e}")
    finally:
        client.close()

