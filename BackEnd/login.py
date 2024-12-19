from flask import Flask, request, render_template, redirect, url_for, session
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

# Route Đăng Nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = "SELECT * FROM dang_nhap WHERE username = %s AND pass = %s"
                cursor.execute(query, (username, password))
                user_login = cursor.fetchone()
                
                if user_login:
                    # Lấy thêm thông tin từ bảng users
                    user_query = "SELECT * FROM users WHERE username = %s"
                    cursor.execute(user_query, (username,))
                    user = cursor.fetchone()
                    
                    if user:
                        session['user_id'] = user['id']
                        session['username'] = user['username']
                        session['rating'] = user['rating']
                        return redirect(url_for('index'))
                else:
                    login_error = "Sai tài khoản hoặc mật khẩu!"
        finally:
            connection.close()
    return render_template('login.html', login_error=login_error)

# Route Đăng Ký
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    signup_error = None
    if request.method == 'POST':
        username = request.form.get('username-l')
        password = request.form.get('password-l')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email')

        if password != password_confirm:
            signup_error = "Mật khẩu không khớp!"
        else:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    # Kiểm tra tài khoản đã tồn tại
                    check_query = "SELECT * FROM dang_nhap WHERE username = %s"
                    cursor.execute(check_query, (username,))
                    if cursor.fetchone():
                        signup_error = "Tên tài khoản đã tồn tại!"
                    else:
                        # Thêm vào bảng dang_ky và dang_nhap
                        insert_query_ky = "INSERT INTO dang_ky (username, pass, email) VALUES (%s, %s, %s)"
                        cursor.execute(insert_query_ky, (username, password, email))
                        insert_query_nhap = "INSERT INTO dang_nhap (username, pass) VALUES (%s, %s)"
                        cursor.execute(insert_query_nhap, (username, password))
                        
                        # Thêm vào bảng users với mặc định rating = 0
                        insert_user_query = """
                            INSERT INTO users (username, rating, total_exercises, total_points, rank_points)
                            VALUES (%s, 0, 0, 0, 0)
                        """
                        cursor.execute(insert_user_query, (username,))
                        
                        # Lấy ID của user vừa thêm
                        user_id = cursor.lastrowid
                        
                        # Thêm vào bảng standing
                        insert_standing_query = """
                            INSERT INTO standing (rank, name_id, score, practic, note)
                            VALUES (%s, %s, 0, 0, '')
                        """
                        cursor.execute(insert_standing_query, (user_id, username))
                        
                        connection.commit()
                        return "Đăng ký thành công! Vui lòng đăng nhập."
            finally:
                connection.close()
    return render_template('login.html', signup_error=signup_error)
# Route Đăng xuất
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Route Trang chủ
@app.route('/')
def index():
    return render_template('mainpage.html')
