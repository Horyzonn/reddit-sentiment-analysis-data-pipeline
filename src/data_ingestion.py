import os
import json
from datetime import datetime
from src.db.mongo_client import save_raw_data
from src.reddit_client import reddit

#Lưu tạm vào file JSON
TEMP_FILE = "/opt/airflow/src/tmp/temp_ingest_data.json"

def convert_reddit_timestamp(timestamp):
    """Chuyển đổi Reddit timestamp (UTC) sang ISO format"""
    return datetime.utcfromtimestamp(timestamp).isoformat() if timestamp else None


def fetch_subreddit_data(subreddit_name, num_posts=50, num_comments=50):
    """
    Thu thập dữ liệu từ subreddit

    Args:
        subreddit_name (str): Tên subreddit cần thu thập
        num_posts (int): Số lượng bài viết cần lấy
        num_comments (int): Số lượng bình luận tối đa mỗi bài viết

    Returns:
        list: Danh sách các dictionary chứa dữ liệu
    """
    subreddit = reddit.subreddit(subreddit_name)
    collected_data = []
    current_time = datetime.utcnow().isoformat()

    try:
        for post in subreddit.hot(limit=num_posts):
            # Thu thập thông tin bài viết
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

            # Thu thập bình luận cho bài viết
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

    except Exception as e:
        print(f"[ERROR] Lỗi khi thu thập dữ liệu từ r/{subreddit_name}: {str(e)}")

    return collected_data

#Lưu vào MongoDB
def ingest_reddit_data():
    """Thu thập dữ liệu và trả về dict {subreddit_name: data}"""
    subreddits = ["Vietnam", "technology", "worldnews", "science"]
    all_data = {}
    for sub in subreddits:
        print(f"[INFO] Đang thu thập dữ liệu từ r/{sub}")
        data = fetch_subreddit_data(sub)
        all_data[sub] = data
        # 🔹 Đảm bảo thư mục tmp tồn tại
    os.makedirs(os.path.dirname(TEMP_FILE), exist_ok=True)

    # Ghi dữ liệu ra file JSON
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Dữ liệu đã được lưu tạm vào {TEMP_FILE}")

    # Chỉ return path để dùng trong DAG (tránh XCom quá tải)
    return TEMP_FILE


if __name__ == "__main__":
    ingest_reddit_data()