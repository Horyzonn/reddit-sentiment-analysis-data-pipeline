import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from sqlalchemy import create_engine
import praw
import os
from dotenv import load_dotenv

# ==========================
# Kết nối PostgreSQL
# ==========================
POSTGRES_URL = "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"
engine = create_engine(POSTGRES_URL)

st.set_page_config(page_title="Reddit Sentiment Dashboard", layout="wide")

# ==========================
# Helper functions
# ==========================
def get_subreddits():
    query = "SELECT DISTINCT subreddit FROM posts ORDER BY subreddit;"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df["subreddit"].tolist()

def get_posts(subreddit):
    query = """
        SELECT post_id, title, author, created_utc, score, upvote_ratio, num_comments,
               sentiment_label, sentiment_score
        FROM posts
        WHERE subreddit = %s
        ORDER BY created_utc DESC;
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=(subreddit,))
    return df

def get_comments(subreddit):
    query = """
        SELECT comment_id, parent_post_id, author, created_utc, score,
               sentiment_label, sentiment_score, body
        FROM comments
        WHERE parent_post_id IN (
            SELECT post_id FROM posts WHERE subreddit = %s
        )
        ORDER BY created_utc DESC;
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=(subreddit,))
    return df

# ==========================
# CSS tùy chỉnh cho Card
# ==========================
card_css = """
<style>
.card {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
    text-align: center;
    margin-bottom: 5px;
}
.metric {
    font-size: 28px;
    font-weight: bold;
    color: #2E86C1;
}
.label {
    font-size: 14px;
    color: #7f8c8d;
}
</style>
"""
st.markdown(card_css, unsafe_allow_html=True)

# ==========================
# Tabs
# ==========================
tab1, tab2 = st.tabs(["System Dashboard", "User Dashboard"])

with tab1:
    st.title("📊 DASHBOARD DỮ LIỆU HỆ THỐNG")

    # Dropdown chọn subreddit
    subreddits = get_subreddits()
    selected_sub = st.selectbox("Chọn 1 subreddit:", subreddits)

    if selected_sub:
        posts_df = get_posts(selected_sub)
        comments_df = get_comments(selected_sub)

        # ==========================
        # HÀNG 1: Metrics + Pie + Sentiment level
        # ==========================
        st.markdown("### 📊 Thống kê & Biểu đồ tổng quan")
        col1, col2, col3 = st.columns([2,2,2])

        with col1:
            st.markdown("### Số lượng")
            st.markdown(f"""
            <div class="card">
                <div class="label">Tổng số Posts</div>
                <div class="metric">{len(posts_df)}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
                    <div class="card">
                        <div class="label">Tổng số Comments</div>
                        <div class="metric">{len(comments_df)}</div>  
                    </div>
                    """, unsafe_allow_html=True)

        with col2:
            st.markdown('### Phân tích Comment')
            if not comments_df.empty:
                sentiment_counts = comments_df['sentiment_label'].value_counts()
                color_map = {"POSITIVE": "#2ecc71", "NEGATIVE": "#e74c3c", "NEUTRAL": "#f39c12"}
                labels = list(sentiment_counts.index)
                norm_labels = [str(l).upper() for l in labels]
                colors = [color_map.get(l, "#95a5a6") for l in norm_labels]

                fig1, ax1 = plt.subplots(figsize=(3,3))
                wedges, texts, autotexts = ax1.pie(
                    sentiment_counts.values,
                    labels=None,
                    autopct="%1.1f%%",
                    startangle=90,
                    colors=colors,
                    wedgeprops=dict(edgecolor="white")
                )
                ax1.axis("equal")
                for t in autotexts:
                    t.set_color("black")
                    t.set_fontsize(10)
                legend_labels = [f"{lab} ({cnt})" for lab, cnt in zip(labels, sentiment_counts.values)]
                ax1.legend(wedges, legend_labels, title="Sentiment Breakdown", loc="center left", bbox_to_anchor=(1,0,0.5,1))
                st.pyplot(fig1)
            else:
                st.info("Không có dữ liệu Comments để hiển thị sentiment.")

        with col3:
            st.markdown("### Điểm số phân tích tổng quan")
            if not comments_df.empty or not posts_df.empty:
                def label_to_score(label):
                    if str(label).lower() == "positive": return 1
                    elif str(label).lower() == "negative": return -1
                    else: return 0
                all_data = pd.concat([posts_df[["sentiment_label"]].copy(),
                                      comments_df[["sentiment_label"]].copy()])
                all_data["sentiment_numeric"] = all_data["sentiment_label"].apply(label_to_score)
                overall_score = all_data["sentiment_numeric"].mean()

                if overall_score > 0.2:
                    conclusion, color, icon = "Positive", "#2ecc71", "👍"
                elif overall_score < -0.2:
                    conclusion, color, icon = "Negative", "#e74c3c", "👎"
                else:
                    conclusion, color, icon = "Neutral", "#f39c12", "👌"

                st.markdown(
                    f"""
                    <div style="text-align:center; padding:15px; border-radius:10px; 
                                background-color: #f9f9f9; border:1px solid #ddd;">
                        <div style="font-size:32px; font-weight:bold; color:{color};">
                            {overall_score:.2f}
                        </div>
                        <div style="font-size:20px; color:{color};">
                            {icon} {conclusion}
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
            else:
                st.info("Không có dữ liệu để tính Overall Score.")

        # ==========================
        # HÀNG 2: Sentiment Timeline
        # ==========================
        if not comments_df.empty:
            st.markdown("### 📈 Biểu đồ theo thời gian")
            comments_df['created_utc'] = pd.to_datetime(comments_df['created_utc'])
            comments_df['date'] = comments_df['created_utc'].dt.normalize()
            comments_df['sentiment_label'] = comments_df['sentiment_label'].str.upper()
            count_timeline = comments_df.groupby(['date','sentiment_label']).size().reset_index(name='count')
            pivot_counts = count_timeline.pivot(index='date', columns='sentiment_label', values='count').fillna(0)
            for col in ["POSITIVE", "NEUTRAL", "NEGATIVE"]:
                if col not in pivot_counts.columns: pivot_counts[col] = 0

            if not pivot_counts.empty:
                fig, ax = plt.subplots(figsize=(12,5))
                ax.bar(pivot_counts.index, pivot_counts['POSITIVE'], label='POSITIVE', color="#2ecc71", alpha=0.8)
                ax.bar(pivot_counts.index, pivot_counts['NEUTRAL'], bottom=pivot_counts['POSITIVE'], label='NEUTRAL', color="#f39c12", alpha=0.8)
                ax.bar(pivot_counts.index, pivot_counts['NEGATIVE'], bottom=pivot_counts['POSITIVE'] + pivot_counts['NEUTRAL'], label='NEGATIVE', color="#e74c3c", alpha=0.8)
                ax.set_xlabel("Ngày")
                ax.set_ylabel("Số lượng Comments")
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
                fig.autofmt_xdate(rotation=45)
                plt.title("Sentiment Timeline (Comments)")
                ax.legend()
                st.pyplot(fig)
            else:
                st.info("Không có dữ liệu để hiển thị Sentiment Timeline.")
        else:
            st.info("Không có dữ liệu comments.")

        # ==========================
        # HÀNG 3: Bảng dữ liệu
        # ==========================
        st.markdown("### 📝 Bảng dữ liệu Posts")
        st.dataframe(posts_df)
        st.markdown("### 💬 Bảng dữ liệu Comments")
        st.dataframe(comments_df)

with tab2:
    st.title("📥 Lấy dữ liệu trực tiếp từ Reddit (PRAW)")

    st.markdown("Nhập tên subreddit để lấy dữ liệu gần đây:")

    subreddit_input = st.text_input("Tên subreddit (ví dụ: vietnam)")

    num_posts = st.slider("Số lượng bài viết tối đa:", min_value=10, max_value=50, value=50, step=10)

    if st.button("Lấy dữ liệu"):
        if subreddit_input.strip() == "":
            st.warning("Vui lòng nhập tên subreddit hợp lệ.")
        else:
            try:
                # ==========================
                # Cấu hình PRAW
                # ==========================
                load_dotenv()

                REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
                REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")

                reddit = praw.Reddit(
                    client_id=REDDIT_CLIENT_ID,
                    client_secret=REDDIT_CLIENT_SECRET,
                    user_agent="rdDataSentiment/0.1 by u/Horyzonix"
                )

                subreddit = reddit.subreddit(subreddit_input)

                posts_data = []
                comments_data = []

                # Lấy posts và comments
                for post in subreddit.new(limit=num_posts):
                    posts_data.append({
                        "post_id": post.id,
                        "title": post.title,
                        "author": str(post.author),
                        "created_utc": pd.to_datetime(post.created_utc, unit='s'),
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "url": post.url,
                        "selftext": post.selftext
                    })

                    post.comments.replace_more(limit=20)
                    for comment in post.comments.list():
                        comments_data.append({
                            "comment_id": comment.id,
                            "parent_post_id": post.id,
                            "author": str(comment.author),
                            "created_utc": pd.to_datetime(comment.created_utc, unit='s'),
                            "score": comment.score,
                            "body": comment.body
                        })

                if posts_data:
                    posts_df = pd.DataFrame(posts_data)
                    comments_df = pd.DataFrame(comments_data)

                    st.success(
                        f"Lấy được {len(posts_df)} bài viết và {len(comments_df)} comment từ r/{subreddit_input}")

                    # Hiển thị bảng trực tiếp như Tab 1
                    st.markdown("### 📝 Bài viết")
                    st.dataframe(posts_df)

                    st.markdown("### 💬 Comments")
                    st.dataframe(comments_df)
                else:
                    st.info("Không có dữ liệu để hiển thị.")
            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")
