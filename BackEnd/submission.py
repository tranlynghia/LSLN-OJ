from flask import Flask, render_template, session, redirect, url_for, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Thay thế bằng khóa bí mật của bạn

# Hàm kết nối cơ sở dữ liệu
def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',  # Cập nhật theo thông tin của bạn
        password='',  # Cập nhật theo thông tin của bạn
        database='dangnhap'  # Cập nhật tên cơ sở dữ liệu
    )
    return connection

# Route chính cho trang kết quả bài nộp
@app.route('/submission_results')
def submission_results():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Nếu người dùng chưa đăng nhập, chuyển hướng tới trang đăng nhập

    user_id = session['user_id']

    # Kết nối tới cơ sở dữ liệu và lấy kết quả bài nộp
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT task_name, correct_tests, total_tests, score, submission_date
                FROM submissions
                WHERE user_id = %s
                ORDER BY submission_date DESC
            """
            cursor.execute(query, (user_id,))
            submissions = cursor.fetchall()
    finally:
        connection.close()

    # Kiểm tra nếu không có kết quả nào
    if not submissions:
        return render_template('submission_results.html', submissions=None)

    # Trả về dữ liệu cho template
    return render_template('submission_results.html', submissions=submissions)

# # Route cho trang login
# @app.route('/login')
# def login():
#     return render_template('login.html')  # Tạo trang login.html của bạn

# # Route cho trang logout
# @app.route('/logout')
# def logout():
#     session.clear()  # Xóa session khi người dùng đăng xuất
#     return redirect(url_for('login'))

# # Hàm để kiểm tra xem người dùng đã đăng nhập chưa
def check_logged_in():
    return 'user_id' in session

if __name__ == '__main__':
    app.run(debug=True)
