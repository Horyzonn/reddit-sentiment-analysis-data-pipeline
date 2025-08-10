import os
from dotenv import load_dotenv
import praw

load_dotenv()  # load biến môi trường từ .env

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    refresh_token=os.getenv("REDDIT_REFRESH_TOKEN"),
    user_agent="RedditSentimentApp/0.1 by u/YourUsername",
    redirect_uri="http://localhost:8080"
)