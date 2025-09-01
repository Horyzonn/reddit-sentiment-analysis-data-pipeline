from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Boolean, TIMESTAMP
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="/opt/airflow/src/.env")  # load biến môi trường từ .env

DATABASE_URL = os.getenv("POSTGRES_URL")

# Tạo engine kết nối đến PostgreSQL
engine = create_engine(DATABASE_URL)
# Khởi tạo metadata để quản lý các bảng
metadata = MetaData()

# Định nghĩa bảng posts
posts = Table("posts", metadata,
    Column("post_id", String, primary_key=True),
    Column("title", String),
    Column("selftext", String),
    Column("author", String),
    Column("created_utc", TIMESTAMP),
    Column("subreddit", String),
    Column("score", Integer),
    Column("upvote_ratio", Float),
    Column("num_comments", Integer),
    Column("url", String),
    Column("permalink", String),
    Column("sentiment_label", String),
    Column("sentiment_score", Float),
    Column("collected_at", TIMESTAMP)
)

# Định nghĩa bảng comments
comments_table = Table("comments", metadata,
    Column("comment_id", String, primary_key=True),
    Column("parent_post_id", String),
    Column("parent_id", String),
    Column("body", String),
    Column("author", String),
    Column("created_utc", TIMESTAMP),
    Column("score", Integer),
    Column("depth", Integer),
    Column("is_submitter", Boolean),
    Column("controversiality", Integer),
    Column("edited", TIMESTAMP),
    Column("stickied", Boolean),
    Column("sentiment_label", String),
    Column("sentiment_score", Float),
    Column("collected_at", TIMESTAMP)
)

# Hàm tiện ích tạo bảng (gọi 1 lần)
def init_db():
    metadata.create_all(engine)