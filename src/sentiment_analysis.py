# src/sentiment.py
import re
import string
import datetime
import os
import pandas as pd
import psycopg2
import psycopg2.extras
from sqlalchemy import create_engine
from src.db.mongo_client import get_mongo_client
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

# CONFIG
from src.db.postgre_client import engine

# Text preprocessing
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text

# Helper: bulk upsert into Postgres using psycopg2.execute_values
def _bulk_upsert_posts(records):
    """
    CHỈNH SỬA: dùng ON CONFLICT on post_id để tránh duplicate.
    records: list of dict matching posts table schema
    """
    if not records:
        return 0

    cols = [
        "post_id","title","selftext","author","created_utc","subreddit","score",
        "upvote_ratio","num_comments","url","permalink","sentiment_label",
        "sentiment_score","collected_at"
    ]

    # prepare list of tuples in column order
    values = [
        tuple(rec.get(c) for c in cols)
        for rec in records
    ]

    insert_sql = f"""
    INSERT INTO posts ({', '.join(cols)}) VALUES %s
    ON CONFLICT (post_id) DO UPDATE
    SET
      title = EXCLUDED.title,
      selftext = EXCLUDED.selftext,
      author = EXCLUDED.author,
      created_utc = EXCLUDED.created_utc,
      subreddit = EXCLUDED.subreddit,
      score = EXCLUDED.score,
      upvote_ratio = EXCLUDED.upvote_ratio,
      num_comments = EXCLUDED.num_comments,
      url = EXCLUDED.url,
      permalink = EXCLUDED.permalink,
      sentiment_label = EXCLUDED.sentiment_label,
      sentiment_score = EXCLUDED.sentiment_score,
      collected_at = EXCLUDED.collected_at;
    """

    conn = engine.raw_connection()
    cur = conn.cursor()
    try:
        psycopg2.extras.execute_values(cur, insert_sql, values, template=None, page_size=100)
        conn.commit()
        inserted = len(values)
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] bulk upsert posts failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def _bulk_upsert_comments(records):
    """
    CHỈNH SỬA: ON CONFLICT on comment_id (tránh duplicate).
    """
    if not records:
        return 0

    cols = [
        "comment_id","parent_post_id","parent_id","body","author","created_utc","score",
        "depth","is_submitter","controversiality","edited","stickied",
        "sentiment_label","sentiment_score","collected_at"
    ]

    values = [
        tuple(rec.get(c) for c in cols)
        for rec in records
    ]

    insert_sql = f"""
    INSERT INTO comments ({', '.join(cols)}) VALUES %s
    ON CONFLICT (comment_id) DO UPDATE
    SET
      parent_post_id = EXCLUDED.parent_post_id,
      parent_id = EXCLUDED.parent_id,
      body = EXCLUDED.body,
      author = EXCLUDED.author,
      created_utc = EXCLUDED.created_utc,
      score = EXCLUDED.score,
      depth = EXCLUDED.depth,
      is_submitter = EXCLUDED.is_submitter,
      controversiality = EXCLUDED.controversiality,
      edited = EXCLUDED.edited,
      stickied = EXCLUDED.stickied,
      sentiment_label = EXCLUDED.sentiment_label,
      sentiment_score = EXCLUDED.sentiment_score,
      collected_at = EXCLUDED.collected_at;
    """

    conn = engine.raw_connection()
    cur = conn.cursor()
    try:
        psycopg2.extras.execute_values(cur, insert_sql, values, template=None, page_size=100)
        conn.commit()
        inserted = len(values)
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] bulk upsert comments failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

# Tạo pipeline sentiment
def create_sentiment_pipeline():
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    model_id = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(model_id)
    return pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# Main: run sentiment and store (with processed flag)
def run_sentiment_analysis(subreddit, sentiment_pipeline: pipeline, only_unprocessed=True, cutoff_hours=6):
    """
    Phân tích cảm xúc và lưu vào PostgreSQL.
    Model/pipeline sẽ được tạo trong DAG và truyền vào.
    """
    client = get_mongo_client()
    db_raw = client["reddit_raw"]
    raw_col = db_raw[subreddit]

    if only_unprocessed:
        query = {"processed_at": {"$exists": False}}
    else:
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(hours=cutoff_hours)
        query = {"collected_at": {"$gte": cutoff_time.isoformat()}}

    docs = list(raw_col.find(query))
    if not docs:
        print(f"[INFO] No docs to process for r/{subreddit}")
        client.close()
        return

    posts_records, comments_records, processed_ids = [], [], []

    for doc in docs:
        processed_ids.append(doc["_id"])

        if doc.get("type") == "post":
            text = clean_text((doc.get("title") or "") + " " + (doc.get("selftext") or ""))
            if not text:
                continue
            analysis = sentiment_pipeline(text[:512])[0]
            posts_records.append({
                "post_id": doc.get("id"),
                "title": doc.get("title"),
                "selftext": doc.get("selftext"),
                "author": doc.get("author"),
                "created_utc": doc.get("created_utc"),
                "subreddit": doc.get("subreddit"),
                "score": doc.get("score"),
                "upvote_ratio": doc.get("upvote_ratio"),
                "num_comments": doc.get("num_comments"),
                "url": doc.get("url"),
                "permalink": doc.get("permalink"),
                "sentiment_label": analysis["label"],
                "sentiment_score": float(analysis["score"]),
                "collected_at": doc.get("collected_at"),
            })

        elif doc.get("type") == "comment":
            text = clean_text(doc.get("body", ""))
            if not text:
                continue
            analysis = sentiment_pipeline(text[:512])[0]
            comments_records.append({
                "comment_id": doc.get("id"),
                "parent_post_id": doc.get("parent_post_id"),
                "parent_id": doc.get("parent_id"),
                "body": doc.get("body"),
                "author": doc.get("author"),
                "created_utc": doc.get("created_utc"),
                "score": doc.get("score"),
                "depth": doc.get("depth"),
                "is_submitter": doc.get("is_submitter"),
                "controversiality": doc.get("controversiality"),
                "edited": doc.get("edited"),
                "stickied": doc.get("stickied"),
                "sentiment_label": analysis["label"],
                "sentiment_score": float(analysis["score"]),
                "collected_at": doc.get("collected_at"),
            })

    # Upsert to Postgres (idempotent)
    inserted_posts = 0
    inserted_comments = 0
    try:
        if posts_records:
            inserted_posts = _bulk_upsert_posts(posts_records)
            print(f"[INFO] Upserted {inserted_posts} post records into PostgreSQL (r/{subreddit})")
        if comments_records:
            inserted_comments = _bulk_upsert_comments(comments_records)
            print(f"[INFO] Upserted {inserted_comments} comment records into PostgreSQL (r/{subreddit})")
    except Exception as e:
        print(f"[ERROR] Upsert failed for r/{subreddit}: {e}")
        #  nếu upsert thất bại thì không mark processed; sẽ retry hoặc debug
        client.close()
        raise

    # =============================
    # Mark processed in MongoDB (chỉ khi upsert thành công)
    # =============================
    try:
        now_iso = datetime.datetime.utcnow().isoformat()
        raw_col.update_many({"_id": {"$in": processed_ids}}, {"$set": {"processed_at": now_iso}})
        print(f"[INFO] Marked {len(processed_ids)} docs as processed in reddit_raw.{subreddit}")
    except Exception as e:
        print(f"[WARNING] Failed to mark processed in MongoDB for r/{subreddit}: {e}")

    client.close()
    return {"posts": inserted_posts, "comments": inserted_comments, "processed_docs": len(processed_ids)}
