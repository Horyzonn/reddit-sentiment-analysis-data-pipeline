from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Thêm src vào sys.path để có thể import module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_ingestion import ingest_reddit_data
from src.save_mongo import save_mongo

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def task_ingest(**context):
    ingest_reddit_data()

def task_save_mongo(**context):
    save_mongo()

with DAG(
    dag_id='reddit_data_pipeline',
    default_args=default_args,
    description='Thu thập dữ liệu Reddit',
    schedule='0 */6 * * *',  # Mỗi 6 giờ
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['reddit', 'mongodb', 'data_ingestion'],
) as dag:

    ingest_task = PythonOperator(
        task_id='ingest_reddit_data',
        python_callable=task_ingest,
    )

    save_mongo_task = PythonOperator(
        task_id='save_data_to_mongo',
        python_callable=task_save_mongo,
    )

ingest_task >> save_mongo_task