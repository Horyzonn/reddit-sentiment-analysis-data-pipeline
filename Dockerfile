FROM apache/airflow:3.0.3
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
RUN pip install torch==2.6.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu