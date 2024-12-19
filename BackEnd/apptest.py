from flask import Flask, render_template, request, redirect, url_for, session,jsonify
import pymysql
from datetime import datetime, timedelta
import pymysql.cursors
import json
import os
import subprocess
import tempfile
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
# Route Trang chủ
@app.route('/')
def index():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM posts ORDER BY post_date DESC")
            posts = cursor.fetchall()
    finally:
        connection.close()

    return render_template('mainpage.html', posts=posts)
# Route Đăng Nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_error = None
    next_url = request.args.get('next')  # Lấy tham số 'next' từ URL
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
                        
                        # Nếu có tham số 'next', chuyển hướng về URL đó, nếu không thì về trang chủ
                    return redirect(next_url or url_for('index'))  # Chuyển hướng về trang chính (mainpage)
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
# Route Bảng xếp hạng
@app.route('/users', methods=["GET"])
def users():
    """Hiển thị bảng xếp hạng của người dùng"""
    if 'user_id' not in session:
        # Nếu chưa đăng nhập, lưu lại URL của trang hiện tại để chuyển về sau khi đăng nhập
        return redirect(url_for('login', next=request.url))

    search_query = request.args.get("username", "")  # Lấy query tìm kiếm
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if search_query:
                cursor.execute(
                    "SELECT * FROM standing WHERE name_id LIKE %s ORDER BY score DESC LIMIT 50",
                    (f"%{search_query}%",),
                )
            else:
                cursor.execute("SELECT * FROM standing ORDER BY score DESC LIMIT 50")
            standing = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template("member.html", standing=standing)
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
    submission_calendar=submission_calendar,
    datetime=datetime,
    timedelta=timedelta  # Truyền timedelta vào template
     )
# Config kết nối MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'dangnhap',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_exercises(search_query=None, score_filter=None):
    """Truy vấn dữ liệu từ bảng `problems` với các bộ lọc tìm kiếm."""
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            query = "SELECT id, title, points FROM problems WHERE 1"
            params = []

            if search_query:
                query += " AND title LIKE %s"
                params.append(f"%{search_query}%")

            if score_filter:
                query += " AND points <= %s"
                params.append(score_filter)

            cursor.execute(query, params)
            exercises = cursor.fetchall()
    finally:
        connection.close()
    return exercises

@app.route("/exercise", methods=["GET"])
def exercise_list():
    """Trang chính hiển thị danh sách bài tập với chức năng tìm kiếm và lọc theo điểm."""
    search_query = request.args.get('search_query', '')

    exercises = get_exercises(search_query=search_query)

    return render_template("question.html", exercises=exercises, search_query=search_query)
# Cấu hình MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Thay bằng mật khẩu MySQL của bạn
    "database": "dangnhap",  # Tên database của bạn
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# Thư mục chứa các file JSON
JSON_FILES_DIRECTORY = "data"

# Hàm kết nối cơ sở dữ liệu
def get_db_connection():
    return pymysql.connect(**db_config)

# Hàm đọc file JSON
def read_json_file(file_name, default_value=None):
    # Xây dựng đường dẫn đầy đủ tới file JSON
    file_path = os.path.join(JSON_FILES_DIRECTORY, file_name)
    
    # Debug log kiểm tra đường dẫn
    print(f"DEBUG: Đang đọc file từ đường dẫn: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File không tìm thấy tại {file_path}")
        return default_value
    except json.JSONDecodeError as e:
        print(f"ERROR: Lỗi đọc JSON từ file {file_path}: {e}")
        return default_value

# Trang chi tiết bài toán
@app.route('/problem/<int:problem_id>')
def problem_detail(problem_id):
    connection = None
    try:
        # Kết nối cơ sở dữ liệu
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Truy xuất bài toán dựa trên ID
            cursor.execute("SELECT * FROM problems WHERE id = %s", (problem_id,))
            problem = cursor.fetchone()

        if problem:
            # Lấy tên file và ví dụ từ cơ sở dữ liệu
            scoring_file = problem.get('scoring_file')
            examples_file = problem.get('examples_file')

            # Đọc nội dung từ file JSON (nếu cần)
            problem['scoring'] = read_json_file(scoring_file, [])
            problem['examples'] = read_json_file(examples_file, [])

            # Trả về template với thông tin problem
            return render_template(
                'submit.html',  # Thay bằng file template đúng ('submit.html')
                problem=problem,
                problem_id=problem_id
            )
        else:
            # Trường hợp không tìm thấy bài toán
            return "Bài toán không tồn tại.", 404

    except pymysql.MySQLError as e:
        return f"Lỗi cơ sở dữ liệu: {str(e)}", 500
    finally:
        if connection:
            connection.close()
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Đường dẫn đến folder chứa file chấm
TEST_FOLDER = os.path.join(os.getcwd(), "test")

# Lấy phần mở rộng file theo ngôn ngữ
def get_file_extension(language):
    extensions = {
        'python': '.py',
        'cpp': '.cpp',
        'java': '.java',
        'javascript': '.js',
    }
    return extensions.get(language, '.txt')

# Xây dựng command để chạy file code
def get_execution_command(filepath, language):
    if language == 'python':
        return ['python3', filepath]
    elif language == 'cpp':
        executable = filepath.replace('.cpp', '.out')
        subprocess.run(['g++', filepath, '-o', executable], check=True)
        return [executable]
    elif language == 'java':
        subprocess.run(['javac', filepath], check=True)
        return ['java', filepath.replace('.java', '')]
    elif language == 'javascript':
        return ['node', filepath]
    else:
        raise ValueError("Unsupported language")

# Chấm bài từ file code
def grade_submission(filepath, language, problem_title):
    # Đường dẫn file đáp án
    answer_file = os.path.join(TEST_FOLDER, f"scoring_{problem_title}.json")

    if not os.path.exists(answer_file):
        return {"error": f"Không tìm thấy file đáp án cho bài {problem_title}"}

    with open(answer_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    correct = 0
    details = []

    for i, case in enumerate(test_cases):
        input_data = case.get("input", "")
        expected_output = case.get("output", "").strip()

        try:
            command = get_execution_command(filepath, language)
            result = subprocess.run(
                command, input=input_data, text=True, capture_output=True, timeout=5
            )
            actual_output = result.stdout.strip()

            if actual_output == expected_output:
                correct += 1
                details.append({
                    "test_case": f"Test {i + 1}",
                    "status": "Accepted",
                    "time": "0.1s",
                    "score": 10,
                })
            else:
                details.append({
                    "test_case": f"Test {i + 1}",
                    "status": "Rejected",
                    "time": "0.1s",
                    "score": 0,
                })
        except Exception as e:
            details.append({
                "test_case": f"Test {i + 1}",
                "status": f"Error: {str(e)}",
                "time": "N/A",
                "score": 0,
            })

    total_tests = len(test_cases)
    total_score = correct * (100 // total_tests)
    grade = round(correct / total_tests * 5, 2)

    return {
        "total": total_tests,
        "correct": correct,
        "details": details,
        "total_score": total_score,
        "grade": grade,
    }

@app.route('/submit/<string:problem_title>')
def submit(problem_title):
    return render_template('submit.html', problem={"name": problem_title})

@app.route('/api/submit', methods=['POST'])
def submit_code():
    try:
        code = request.form['code']
        language = request.form['language']
        problem_title = request.form['problem_title']

        if not code:
            return jsonify({"message": "Code không được để trống"}), 400

        with tempfile.NamedTemporaryFile(suffix=get_file_extension(language), delete=False) as temp_file:
            temp_file.write(code.encode())
            temp_filepath = temp_file.name

        result = grade_submission(temp_filepath, language, problem_title)
        os.unlink(temp_filepath)  # Xóa file tạm sau khi xử lý

        if "error" in result:
            return jsonify({"message": result["error"]}), 404

        return jsonify(result)
    except Exception as e:
        return jsonify({"message": f"Đã xảy ra lỗi: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
