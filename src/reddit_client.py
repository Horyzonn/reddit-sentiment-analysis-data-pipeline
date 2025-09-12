import os
from dotenv import load_dotenv
import praw

load_dotenv(dotenv_path="/opt/airflow/src/.env")  # load biến môi trường từ .env



reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    refresh_token=os.getenv("REDDIT_REFRESH_TOKEN"),
    user_agent="rdDataSentiment/0.1 by u/Horyzonix",
    requestor_kwargs={"timeout": 60}
)



# def test_connection():
#     me = reddit.user.me()
#     print("Đăng nhập thành công với user:", me)
#
# test_connection()