from src.db.mongo_client import save_raw_data

import json
from src.db.mongo_client import save_raw_data

# Đường dẫn file tạm chứa dữ liệu ingest
TEMP_FILE = "/opt/airflow/src/tmp/temp_ingest_data.json"

def save_mongo():
    """
    Đọc dữ liệu từ file tạm JSON và lưu vào MongoDB.
    """
    try:
        # Đọc dữ liệu từ file tạm
        with open(TEMP_FILE, "r", encoding="utf-8") as f:
            data_dict = json.load(f)

        # Lưu vào MongoDB
        for sub, data in data_dict.items():
            if data:
                save_raw_data(collection_name=sub, data=data)
            else:
                print(f"[WARNING] Không có dữ liệu từ r/{sub}")

    except FileNotFoundError:
        print(f"[ERROR] Không tìm thấy file tạm tại {TEMP_FILE}")
    except json.JSONDecodeError:
        print(f"[ERROR] File {TEMP_FILE} không phải JSON hợp lệ")
    except Exception as e:
        print(f"[ERROR] Lỗi khi lưu dữ liệu vào MongoDB: {e}")