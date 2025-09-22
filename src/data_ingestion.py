import os
import json
from datetime import datetime
from src.db.mongo_client import save_raw_data
from src.reddit_client import reddit
import time
from prawcore.exceptions import RequestException, ResponseException, ServerError

#Lưu tạm vào file JSON
TEMP_FILE = "/opt/airflow/src/tmp/temp_ingest_data.json"

CONFIG_FILE = "/opt/airflow/src/config/subreddits.json"

def convert_reddit_timestamp(timestamp):
    """Chuyển đổi Reddit timestamp (UTC) sang ISO format"""
    return datetime.utcfromtimestamp(timestamp).isoformat() if timestamp else None


def fetch_and_save_subreddit(subreddit_name, num_posts=50, num_comments=50, max_retries=3):
    """Thu thập dữ liệu Reddit với retry/backoff"""
    attempt = 0
    collected_data = []
    current_time = datetime.utcnow().isoformat()

    while attempt < max_retries:
        try:
            subreddit = reddit.subreddit(subreddit_name)

            # Lấy posts
            for post in subreddit.hot(limit=num_posts):
                post_data = {
                    "type": "post",
                    "id": post.id,
                    "title": post.title,
                    "selftext": post.selftext,
                    "author": str(post.author) if post.author else None,
                    "created_utc": convert_reddit_timestamp(post.created_utc),
                    "subreddit": subreddit_name,
                    "score": post.score,
                    "upvote_ratio": post.upvote_ratio,
                    "num_comments": post.num_comments,
                    "url": post.url,
                    "permalink": post.permalink,
                    "collected_at": current_time
                }
                collected_data.append(post_data)

                # Lấy comments
                post.comments.replace_more(limit=0)
                for comment in post.comments.list()[:num_comments]:
                    comment_data = {
                        "type": "comment",
                        "id": comment.id,
                        "body": comment.body,
                        "author": str(comment.author) if comment.author else None,
                        "created_utc": convert_reddit_timestamp(comment.created_utc),
                        "score": comment.score,
                        "parent_id": comment.parent_id,
                        "link_id": comment.link_id,
                        "permalink": comment.permalink,
                        "is_submitter": comment.is_submitter,
                        "depth": comment.depth,
                        "controversiality": comment.controversiality,
                        "edited": convert_reddit_timestamp(comment.edited) if comment.edited else False,
                        "stickied": comment.stickied,
                        "parent_post_id": post.id,
                        "subreddit": subreddit_name,
                        "collected_at": current_time
                    }
                    collected_data.append(comment_data)

            # Lưu vào MongoDB nếu có dữ liệu
            if collected_data:
                save_raw_data(subreddit_name, collected_data)

            print(f"[INFO] Đã lưu {len(collected_data)} records từ r/{subreddit_name} vào MongoDB")
            return  # thành công, thoát vòng lặp

        except Exception as e:
            attempt += 1
            wait_time = 5 * attempt  # backoff tuyến tính
            print(f"[WARN] Attempt {attempt} thất bại với r/{subreddit_name}: {e}. Đang retry sau {wait_time}s...")
            time.sleep(wait_time)

    print(f"[ERROR] Không thể thu thập dữ liệu từ r/{subreddit_name} sau {max_retries} attempts")
