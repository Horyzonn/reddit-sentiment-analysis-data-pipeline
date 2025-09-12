from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_ingestion import fetch_and_save_subreddit
from src.sentiment_analysis import run_sentiment_analysis, create_sentiment_pipeline

CONFIG_FILE = "/opt/airflow/src/config/subreddits.json"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def read_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["subreddits"]

def analyze_all_subreddits(**context):
    sentiment_pipeline = create_sentiment_pipeline()
    # Lấy danh sách subreddit từ MongoDB hoặc config
    subreddits = read_config()
    for sub in subreddits:
        print(f"[INFO] Processing sentiment for r/{sub}")
        run_sentiment_analysis(sub, sentiment_pipeline)

with DAG(
    dag_id='reddit_data_pipeline',
    default_args=default_args,
    description='Thu thập dữ liệu Reddit và phân tích sentiment',
    schedule='0 */6 * * *',
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['reddit', 'mongodb', 'data_ingestion'],
) as dag:

    # Đọc config trong DAG context để tạo ingest task
    subreddits = read_config()
    ingest_tasks = []

    for sub in subreddits:
        task = PythonOperator(
            task_id=f"ingest_{sub}",
            python_callable=fetch_and_save_subreddit,
            op_args=[sub],  # truyền tên subreddit vào callable
        )
        ingest_tasks.append(task)

    finish_ingest = EmptyOperator(task_id="finish_ingest")
    for t in ingest_tasks:
        t >> finish_ingest

    sentiment_task = PythonOperator(
        task_id="sentiment_all_subreddits",
        python_callable=analyze_all_subreddits,
    )

    finish_ingest >> sentiment_task
