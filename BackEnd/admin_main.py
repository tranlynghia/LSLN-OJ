from flask import Flask, render_template, request, redirect, url_for,flash,send_from_directory,session
import pymysql
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import rarfile
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Thay bằng một khóa bí mật thực tế

# Cấu hình đường dẫn lưu ảnh
app.config['UPLOAD_FOLDER'] = 'BackEnd/uploads/'
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
@app.route('/img/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory('uploads', filename)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Mật khẩu không khớp.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Kiểm tra tài khoản đã tồn tại
                cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
                if cursor.fetchone():
                    flash('Tên tài khoản đã tồn tại.', 'danger')
                    return redirect(url_for('register'))
                
                # Thêm tài khoản mới
                query = "INSERT INTO admins (username, password) VALUES (%s, %s)"
                cursor.execute(query, (username, hashed_password))
                connection.commit()
                flash('Đăng ký thành công!', 'success')
                return redirect(url_for('login'))
        finally:
            connection.close()

    return render_template('admin/register.html')

# Route Đăng nhập Admin
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
                admin = cursor.fetchone()
                if admin and check_password_hash(admin['password'], password):
                    session['admin_id'] = admin['id']
                    session['admin_username'] = admin['username']
                    flash('Đăng nhập thành công!', 'success')
                    return redirect(url_for('task_selection'))
                else:
                    flash('Tên tài khoản hoặc mật khẩu không đúng.', 'danger')
        finally:
            connection.close()

    return render_template('admin/login.html')

# Route Dashboard cho Admin (chỉ truy cập khi đã đăng nhập)
@app.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        flash('Vui lòng đăng nhập.', 'danger')
        return redirect(url_for('login'))

    return render_template('admin/dashboard.html', admin_username=session['admin_username'])
@app.route('/admin/delete_post/<int:post_id>', methods=['GET', 'POST'])
def delete_post(post_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Kiểm tra bài viết có tồn tại hay không
            cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
            post = cursor.fetchone()

            if not post:
                return "Bài viết không tồn tại", 404

            # Xóa bài viết
            cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
            connection.commit()

            flash("Bài viết đã được xóa thành công.", "success")

    except pymysql.MySQLError as e:
        flash(f"Lỗi cơ sở dữ liệu: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))

    finally:
        connection.close()

    return redirect(url_for('admin_dashboard'))

# Route Đăng xuất Admin
@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất.', 'success')
    return redirect(url_for('login'))


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
            # Lưu file ảnh vào thư mục UPLOAD_FOLDER
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Lưu tên file ảnh thay vì đường dẫn
            image_name = filename
            
            # Lưu thông tin bài viết vào cơ sở dữ liệu
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    query = """
                        INSERT INTO posts (title, content, post_date, image_url)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (title, content, post_date, image_name))
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
            # Lấy dữ liệu bài viết từ cơ sở dữ liệu
            cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
            post = cursor.fetchone()
            if not post:
                return "Bài viết không tồn tại", 404

            # Nếu là yêu cầu POST (Lưu thay đổi)
            if request.method == 'POST':
                title = request.form['title']
                content = request.form['content']
                post_date = request.form['post_date']
                image = request.files['image']

                # Xử lý ảnh nếu có
                if image and image.filename != '' and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path)  # Lưu ảnh vào thư mục

                    # Cập nhật bài viết với ảnh mới
                    update_query = """
                        UPDATE posts
                        SET title = %s, content = %s, post_date = %s, image_url = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (title, content, post_date, filename, post_id))
                else:
                    # Cập nhật bài viết mà không thay đổi ảnh
                    update_query = """
                        UPDATE posts
                        SET title = %s, content = %s, post_date = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (title, content, post_date, post_id))

                connection.commit()
                return redirect(url_for('admin_dashboard'))

        # Nếu là yêu cầu GET, hiển thị form chỉnh sửa
        return render_template('admin/edit_post.html', post=post)

    finally:
        connection.close()

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
@app.route('/add-problem', methods=['GET', 'POST'])
def add_problem():
    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ form
            title = request.form['title']
            points = request.form['points']
            time_limit = request.form['time_limit']
            memory_limit = request.form['memory_limit']
            description = request.form['description']
            input_format = request.form['input_format']
            output_format = request.form['output_format']
            scoring = request.form['scoring']
            examples = request.form['examples']
            notifications = request.form['notifications']

            # Kiểm tra JSON hợp lệ cho các trường "scoring" và "examples"
            try:
                scoring_json = json.loads(scoring)
                examples_json = json.loads(examples)
            except json.JSONDecodeError:
                flash('Scoring hoặc Examples không phải định dạng JSON hợp lệ.', 'danger')
                return redirect(url_for('add_problem'))

            # Lưu thông tin bài toán vào cơ sở dữ liệu
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    query = """
                        INSERT INTO problems (
                            title, points, time_limit, memory_limit, description,
                            input_format, output_format, scoring_file, examples_file, notifications
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        query,
                        (
                            title, points, time_limit, memory_limit, description,
                            input_format, output_format, json.dumps(scoring_json), json.dumps(examples_json), notifications
                        )
                    )
                    connection.commit()
                flash('Bài toán đã được thêm thành công!', 'success')
            finally:
                connection.close()

            return redirect(url_for('add_problem'))

        except Exception as e:
            flash(f'Đã xảy ra lỗi: {str(e)}', 'danger')
            return redirect(url_for('add_problem'))

    return render_template('admin/form_ex.html')
# Đường dẫn tới thư mục chứa file JSON và các file tải lên
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Trang chỉnh sửa bài toán (GET)
@app.route('/edit_problem/<int:problem_id>', methods=['GET', 'POST'])
def edit_problem(problem_id):
    if request.method == 'GET':
        # Xử lý GET request để hiển thị form chỉnh sửa
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM problems WHERE id = %s", (problem_id,))
                problem = cursor.fetchone()

            if problem:
                # Nếu có file scoring_file và examples_file, đọc chúng
                scoring_file = problem.get('scoring_file')
                examples_file = problem.get('examples_file')

                problem['scoring'] = read_json_file(scoring_file) if scoring_file else []
                problem['examples'] = read_json_file(examples_file) if examples_file else []

                return render_template('admin/edit_problems.html', problem=problem)
            else:
                return "Bài toán không tồn tại.", 404

        except pymysql.MySQLError as e:
            return f"Lỗi cơ sở dữ liệu: {str(e)}", 500
        finally:
            if connection:
                connection.close()

    elif request.method == 'POST':
        # Xử lý POST request khi người dùng gửi form chỉnh sửa
        connection = None
        try:
            title = request.form['title']
            points = request.form['points']
            time_limit = request.form['time_limit']
            memory_limit = request.form['memory_limit']
            description = request.form['description']
            input_format = request.form['input_format']
            output_format = request.form['output_format']
            notifications = request.form.get('notifications', '')

            # Kiểm tra và lưu các file JSON (scoring_file, examples_file)
            scoring_file = request.files.get('scoring_file')
            examples_file = request.files.get('examples_file')

            if scoring_file and scoring_file.filename.endswith('.json'):
                scoring_filename = os.path.join(app.config['UPLOAD_FOLDER'], scoring_file.filename)
                scoring_file.save(scoring_filename)
            else:
                scoring_filename = None

            if examples_file and examples_file.filename.endswith('.json'):
                examples_filename = os.path.join(app.config['UPLOAD_FOLDER'], examples_file.filename)
                examples_file.save(examples_filename)
            else:
                examples_filename = None

            # Cập nhật cơ sở dữ liệu
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute(""" 
                    UPDATE problems 
                    SET title = %s, points = %s, time_limit = %s, memory_limit = %s, 
                        description = %s, input_format = %s, output_format = %s, 
                        scoring_file = %s, examples_file = %s, notifications = %s
                    WHERE id = %s
                """, (
                    title, points, time_limit, memory_limit, description,
                    input_format, output_format, scoring_filename, examples_filename,
                    notifications, problem_id
                ))

                connection.commit()

            return redirect(url_for('edit_problem', problem_id=problem_id))

        except pymysql.MySQLError as e:
            return f"Lỗi cơ sở dữ liệu: {str(e)}", 500
        except Exception as e:
            return f"Lỗi khi xử lý: {str(e)}", 400
        finally:
            if connection:
                connection.close()

# Hàm đọc tệp JSON từ thư mục 'data'
def read_json_file(file_name):
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        return None
# Cấu hình thư mục
DATASET = "uploads"
EXTRACT_FOLDER = "extracted"
RESULT_FOLDER = "test"
os.makedirs(DATASET, exist_ok=True)
os.makedirs(EXTRACT_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Cấu hình đường dẫn đến unrar.exe (của WinRAR)
rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\unrar.exe"

# Lấy danh sách bài kiểm tra từ cơ sở dữ liệu
def get_problems():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM problems")
            problems = cursor.fetchall()
    finally:
        conn.close()
    return problems

@app.route("/change", methods=["GET", "POST"])
def upload_and_process_rar():
    result_file = None
    error = None
    problems = get_problems()  # Lấy danh sách bài kiểm tra

    if request.method == "POST":
        if "file" not in request.files:
            error = "Không có file nào được tải lên!"
        else:
            uploaded_file = request.files["file"]
            if uploaded_file.filename.endswith(".rar"):
                try:
                    # Lưu file .rar
                    rar_path = os.path.join(DATASET, uploaded_file.filename)
                    uploaded_file.save(rar_path)

                    # Giải nén file .rar
                    with rarfile.RarFile(rar_path) as rf:
                        rf.extractall(EXTRACT_FOLDER)

                    # Lấy tên thư mục con sau khi giải nén
                    extract_subfolder = os.path.splitext(uploaded_file.filename)[0]
                    extract_subfolder_path = os.path.join(EXTRACT_FOLDER, extract_subfolder)

                    # Kiểm tra nếu thư mục con tồn tại
                    if not os.path.isdir(extract_subfolder_path):
                        error = "Không tìm thấy thư mục con chứa các file cần thiết!"
                        return render_template(
                            "admin/change.html", result_file=result_file, error=error, extract_folder=EXTRACT_FOLDER, problems=problems
                        )

               # Kiểm tra nếu người dùng đã chọn bài kiểm tra
                    problem_id = request.form.get("problem_id")
                    custom_name = None

                    if problem_id:
                        # Đặt tên file dựa trên problem_id
                        custom_name = f"scoring_{problem_id}.json"
                    else:
                        error = "Không chọn bài kiểm tra."

                    if custom_name:
                        # Xử lý file .inp và .out
                        result_file = process_extracted_files(extract_subfolder_path, custom_name)

                except Exception as e:
                    error = f"Lỗi xử lý file .rar: {str(e)}"
            else:
                error = "Vui lòng tải lên file .rar hợp lệ!"

    return render_template(
        "admin/change.html", result_file=result_file, error=error, extract_folder=EXTRACT_FOLDER, problems=problems
    )


def process_extracted_files(EXTRACT_FOLDER, output_filename):
    data = []
    files = sorted(os.listdir(EXTRACT_FOLDER))

    print(f"Files in {EXTRACT_FOLDER}: {files}")  # In ra các file trong thư mục giải nén

    # Ghép cặp file .inp và .out
    file_pairs = {}
    for filename in files:
        if filename.endswith(".inp"):
            base_name = os.path.splitext(filename)[0]
            file_pairs[base_name] = {"inp": filename}
        elif filename.endswith(".out"):
            base_name = os.path.splitext(filename)[0]
            if base_name in file_pairs:
                file_pairs[base_name]["out"] = filename

    print(f"File pairs: {file_pairs}")  # In ra các cặp file đã ghép

    # Đọc nội dung và tạo JSON từ thư mục giải nén
    for base_name, pair in file_pairs.items():
        if "inp" in pair and "out" in pair:
            inp_path = os.path.join(EXTRACT_FOLDER, pair["inp"])  # Đọc từ thư mục giải nén
            out_path = os.path.join(EXTRACT_FOLDER, pair["out"])  # Đọc từ thư mục giải nén

            with open(inp_path, "r", encoding="utf-8") as inp_file:
                input_content = inp_file.read().strip()
                print(f"Input file {inp_path} content: {input_content}")
            with open(out_path, "r", encoding="utf-8") as out_file:
                output_content = out_file.read().strip()
                print(f"Output file {out_path} content: {output_content}")

            data.append({"input": input_content, "output": output_content})

    # Kiểm tra dữ liệu trước khi ghi vào JSON
    print(f"Data to write: {data}")

    # Lưu kết quả JSON vào thư mục result
    if not os.path.exists(RESULT_FOLDER):
        os.makedirs(RESULT_FOLDER)

    result_file = os.path.join(RESULT_FOLDER, output_filename)
    print(f"Saving JSON to: {result_file}")
    with open(result_file, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

    return output_filename

@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(RESULT_FOLDER, filename, as_attachment=True)

@app.route('/admin/add_exam', methods=['GET', 'POST'])
def add_exam():
    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ form
            exam_name = request.form['exam_name']
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            problems = request.form.getlist('problems')  # Lấy danh sách bài toán (list)

            # Lưu kỳ thi vào cơ sở dữ liệu
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    # Thêm thông tin kỳ thi
                    query_exam = """
                        INSERT INTO exams (name, start_time, end_time)
                        VALUES (%s, %s, %s)
                    """
                    cursor.execute(query_exam, (exam_name, start_time, end_time))
                    exam_id = cursor.lastrowid  # Lấy ID kỳ thi vừa thêm

                    # Thêm các bài toán vào kỳ thi
                    query_exam_problems = """
                        INSERT INTO exam_problems (exam_id, problem_id)
                        VALUES (%s, %s)
                    """
                    for problem_id in problems:
                        cursor.execute(query_exam_problems, (exam_id, problem_id))

                    connection.commit()
                    flash('Kỳ thi đã được thêm thành công!', 'success')
            finally:
                connection.close()
            
            return redirect(url_for('add_exam'))
        except Exception as e:
            flash(f'Lỗi: {str(e)}', 'danger')
            return redirect(url_for('add_exam'))
    else:
        # Lấy danh sách bài toán từ cơ sở dữ liệu
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, title FROM problems")
                problems = cursor.fetchall()
        finally:
            connection.close()

        # Hiển thị form tạo kỳ thi
        return render_template('admin/add_exam.html', problems=problems)
# Route cho trang chủ (hiển thị bài viết)
@app.route('/')
def task_selection():
    return render_template('admin/menu.html')

if __name__ == '__main__':
    app.run(debug=True)
