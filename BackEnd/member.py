from flask import Flask, render_template, request, redirect, url_for, session
import pymysql

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Khóa bí mật cho session

# Kết nối MySQL
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',  # Thay bằng mật khẩu MySQL của bạn
        database='dangnhap',  # Tên cơ sở dữ liệu
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
# Route Bảng xếp hạng
@app.route('/users', methods=['GET'])
def users():
    username = request.args.get('username', '')
    page = int(request.args.get('page', 1))  # Trang hiện tại (mặc định là trang 1)
    limit = 10  # Số lượng người dùng trên mỗi trang
    offset = (page - 1) * limit

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Tìm kiếm theo username
            if username:
                query = """
                    SELECT SQL_CALC_FOUND_ROWS * 
                    FROM users 
                    WHERE username LIKE %s 
                    ORDER BY rating DESC 
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, ('%' + username + '%', limit, offset))
            else:
                query = """
                    SELECT SQL_CALC_FOUND_ROWS * 
                    FROM users 
                    ORDER BY rating DESC 
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, (limit, offset))

            rankings = cursor.fetchall()

            # Tính tổng số bản ghi
            cursor.execute("SELECT FOUND_ROWS()")
            total_users = cursor.fetchone()['FOUND_ROWS()']
    finally:
        connection.close()

    total_pages = (total_users + limit - 1) // limit
    return render_template(
        'member.html', 
        rankings=rankings, 
        current_page=page, 
        total_pages=total_pages, 
        username=username
    )
if __name__ == "__main__":
    app.run(debug=True)
