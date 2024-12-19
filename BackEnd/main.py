from flask import Flask, render_template
import pymysql

app = Flask(__name__)

# Hàm kết nối cơ sở dữ liệu
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',  # Thay bằng mật khẩu MySQL của bạn
        database='dangnhap',  # Tên cơ sở dữ liệu của bạn
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# Route hiển thị danh sách bài viết
@app.route('/')
def index():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Lấy danh sách bài viết, sắp xếp theo ngày đăng
            cursor.execute("SELECT id, title, content, image_url FROM posts ORDER BY post_date DESC")
            posts = cursor.fetchall()
    finally:
        connection.close()

    return render_template('mainpage.html', posts=posts)

if __name__ == '__main__':
    app.run(debug=True)
