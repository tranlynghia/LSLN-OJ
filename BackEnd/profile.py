from flask import Flask, render_template
import pymysql
from datetime import datetime

app = Flask(__name__)

# Kết nối cơ sở dữ liệu
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',  # Mật khẩu MySQL
        database='dangnhap',  # Tên cơ sở dữ liệu
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# Hàm tính số bài nộp trong năm qua
def get_submission_summary(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT submission_date
                FROM submissions
                WHERE user_id = %s
                  AND YEAR(submission_date) = YEAR(CURDATE())
            """
            cursor.execute(query, (user_id,))
            submissions = cursor.fetchall()
            return submissions
    finally:
        connection.close()

# Hàm lấy thông tin người dùng
def get_user_profile(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT username, rating, total_exercises, total_points, rank_points
                FROM users
                WHERE id = %s
            """
            cursor.execute(query, (user_id,))
            user_profile = cursor.fetchone()
            return user_profile
    finally:
        connection.close()
@app.route('/')
def index():
    return render_template('index.html')


# Route trang profile
@app.route('/profile/<int:user_id>')
def profile(user_id):
    # Lấy thông tin người dùng
    user = get_user_profile(user_id)

    # Nếu không tìm thấy người dùng
    if not user:
        return render_template("error.html", error_message="Không tìm thấy người dùng.")

    # Lấy danh sách nộp bài
    submissions = get_submission_summary(user_id)

    # Xử lý dữ liệu để tạo lịch bài nộp
    submission_calendar = {}
    for submission in submissions:
        date_str = submission['submission_date'].strftime("%Y-%m-%d")
        submission_calendar[date_str] = submission_calendar.get(date_str, 0) + 1

    return render_template(
        "profile.html",
        user=user,
        submission_calendar=submission_calendar
    )

if __name__ == '__main__':
    app.run(debug=True)
