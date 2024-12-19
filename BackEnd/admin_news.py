from flask import Flask, render_template, request, redirect, url_for
import pymysql
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Cấu hình đường dẫn lưu ảnh
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Kiểm tra định dạng ảnh
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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

# Route cho Admin - Đăng Bài
@app.route('/admin/create_post', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        title = request.form['title']
        content = request.form['content']
        post_date = request.form['post_date']
        
        # Kiểm tra ảnh tải lên
        if 'image' not in request.files:
            return "Không có ảnh tải lên"
        
        image = request.files['image']
        if image.filename == '':
            return "Chưa chọn ảnh"
        
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            
            # Kiểm tra nếu thư mục uploads chưa tồn tại thì tạo mới
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Lưu thông tin bài viết vào cơ sở dữ liệu
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    query = """
                        INSERT INTO posts (title, content, post_date, image_url)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (title, content, post_date, image_url))
                    connection.commit()
            finally:
                connection.close()
            
            return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/create_post.html')
@app.route('/admin/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Lấy thông tin bài viết cũ từ cơ sở dữ liệu
            cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
            post = cursor.fetchone()
            
            # Nếu bài viết không tồn tại
            if not post:
                return "Bài viết không tồn tại", 404
            
            if request.method == 'POST':
                # Lấy dữ liệu từ form
                title = request.form['title']
                content = request.form['content']
                post_date = request.form['post_date']
                
                # Kiểm tra ảnh tải lên (nếu có)
                if 'image' in request.files and request.files['image'].filename != '':
                    image = request.files['image']
                    if image and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        
                        # Kiểm tra nếu thư mục uploads chưa tồn tại thì tạo mới
                        if not os.path.exists(app.config['UPLOAD_FOLDER']):
                            os.makedirs(app.config['UPLOAD_FOLDER'])
                        
                        # Lưu ảnh mới
                        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        image_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    else:
                        image_url = post['image_url']  # Giữ ảnh cũ nếu không có ảnh mới
                else:
                    image_url = post['image_url']  # Giữ ảnh cũ nếu không có ảnh mới

                # Cập nhật bài viết vào cơ sở dữ liệu
                with connection.cursor() as cursor:
                    query = """
                        UPDATE posts
                        SET title = %s, content = %s, post_date = %s, image_url = %s
                        WHERE id = %s
                    """
                    cursor.execute(query, (title, content, post_date, image_url, post_id))
                    connection.commit()
                
                return redirect(url_for('admin_dashboard'))
            
    finally:
        connection.close()

    return render_template('admin/edit_post.html', post=post)


# Route cho Admin - Bảng điều khiển (hiển thị các bài đăng)
@app.route('/admin/dashboard')
def admin_dashboard():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM posts ORDER BY post_date DESC")
            posts = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin/dashboard.html', posts=posts)

if __name__ == '__main__':
    app.run(debug=True)
