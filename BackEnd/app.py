from flask import Flask, render_template, request, redirect, send_from_directory, url_for, session,jsonify
import pymysql
from datetime import datetime, timedelta
import pymysql.cursors
import json
import os
import subprocess
import tempfile
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Khóa bí mật cho session
IMAGE_FOLDER = os.path.join(os.getcwd(), "BackEnd", "img", "uploads")
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
@app.route('/img/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory('uploads', filename)
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
                SELECT username, rating, total_exercises, rank_points
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
    if not file_name:  # Nếu file_name là None hoặc chuỗi rỗng
        print("ERROR: Tên file JSON không hợp lệ.")
        return default_value

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
            # Lấy tên file từ cơ sở dữ liệu
            scoring_file = problem.get('scoring_file')  # Tên file JSON chứa điểm
            examples_file = problem.get('examples_file')  # Tên file JSON chứa ví dụ

            # Nếu không có file, gán giá trị mặc định là danh sách rỗng
            if scoring_file:
                problem['scoring'] = read_json_file(scoring_file, [])
            else:
                problem['scoring'] = []

            if examples_file:
                problem['examples'] = read_json_file(examples_file, [])
            else:
                problem['examples'] = []

            # Trả kết quả về template, vẫn hiển thị bài toán mặc dù thiếu file
            return render_template('question_info.html', problem=problem)
        else:
            # Trường hợp không tìm thấy bài toán
            return "Bài toán không tồn tại.", 404

    except pymysql.MySQLError as e:
        # Xử lý lỗi cơ sở dữ liệu
        return f"Lỗi cơ sở dữ liệu: {str(e)}", 500

    finally:
        if connection:
            connection.close()

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
def grade_submission(filepath, language, problem_id):
    # Đường dẫn file đáp án
    answer_file = os.path.join(TEST_FOLDER, f"scoring_{problem_id}.json")

    if not os.path.exists(answer_file):
        return {"error": f"Không tìm thấy file đáp án cho bài {problem_id}"}

    # Đọc file JSON chứa các test case
    with open(answer_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    correct = 0
    details = []

    # Duyệt qua các test case và chấm điểm
    for i, case in enumerate(test_cases):
        input_data = case.get("input", "")
        expected_output = case.get("output", "").strip()

        try:
            # Xây dựng và thực thi lệnh chạy code
            command = get_execution_command(filepath, language)
            result = subprocess.run(
                command, input=input_data, text=True, capture_output=True, timeout=5
            )
            actual_output = result.stdout.strip()

            # So sánh kết quả thực tế với kết quả mong đợi
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

    # Tính điểm tổng và trả kết quả
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

@app.route('/submit', methods=['GET'])
def submit_problem():
    problem_id = request.args.get('problem_id')  # Lấy giá trị 'problem_id' từ URL
    if not problem_id:
        return "Thiếu tham số problem_id", 400  # Trả về lỗi nếu thiếu problem_id

    # Truy vấn bài toán từ cơ sở dữ liệu
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM problems WHERE id = %s", (problem_id,))
            problem = cursor.fetchone()

        if not problem:
            return "Không tìm thấy bài toán.", 404

        return render_template('submit.html', problem=problem)  # Truyền bài toán vào template
    finally:
        connection.close()


@app.route('/api/submit', methods=['POST'])
def submit_code():
    try:
        # Lấy dữ liệu từ form
        code = request.form['code']
        language = request.form['language']
        problem_id = request.form['problem_title']  # Đây là ID bài toán

        if not code or not language or not problem_id:
            return jsonify({"message": "Thiếu tham số cần thiết: code, language, hoặc problem_id"}), 400

        # Tạo file tạm để lưu code
        with tempfile.NamedTemporaryFile(suffix=get_file_extension(language), delete=False) as temp_file:
            temp_file.write(code.encode())
            temp_filepath = temp_file.name

        # Gọi hàm chấm bài
        result = grade_submission(temp_filepath, language, problem_id)
        os.unlink(temp_filepath)  # Xóa file tạm sau khi xử lý

        if "error" in result:
            return jsonify({"message": result["error"]}), 404

        # Lưu kết quả bài nộp vào cơ sở dữ liệu
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO submissions (user_id, task_name, correct_tests, total_tests, score, submission_date, status)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                """
                cursor.execute(
                    query,
                    (
                        session['user_id'],          # ID người dùng đang đăng nhập
                        f"Problem {problem_id}",    # Tên bài toán
                        result['correct'],          # Số test đúng
                        result['total'],            # Tổng số test
                        result['total_score'],      # Tổng điểm
                        "Accepted" if result['correct'] == result['total'] else "Rejected"
                    ),
                )
                connection.commit()
        finally:
            connection.close()

        # Trả về kết quả chấm bài
        return jsonify(result)

    except Exception as e:
        return jsonify({"message": f"Đã xảy ra lỗi: {str(e)}"}), 500

    
    
#Hiển thị submission
# Route lấy kết quả bài nộp của người dùng
@app.route('/submission_results')
def submission_results():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Yêu cầu đăng nhập

    user_id = session['user_id']

    # Lấy danh sách bài nộp của người dùng từ cơ sở dữ liệu
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT task_name, correct_tests, total_tests, score, submission_date, status
                FROM submissions
                WHERE user_id = %s
                ORDER BY submission_date DESC
            """
            cursor.execute(query, (user_id,))
            submissions = cursor.fetchall()
    finally:
        connection.close()

    return render_template('Submission.html', submissions=submissions)

# Route hiển thị danh sách kỳ thi
@app.route('/exams', methods=['GET'])
def exams():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Lấy danh sách kỳ thi
            query = """
                SELECT exams.id, exams.name, exams.start_time, exams.end_time,
                       (CASE WHEN NOW() BETWEEN exams.start_time AND exams.end_time THEN 1 ELSE 0 END) AS is_active,
                       COUNT(exam_problems.problem_id) AS problem_count
                FROM exams
                LEFT JOIN exam_problems ON exams.id = exam_problems.exam_id
                GROUP BY exams.id
                ORDER BY exams.start_time DESC;
            """
            cursor.execute(query)
            exams = cursor.fetchall()
    finally:
        connection.close()

    return render_template('contest.html', exams=exams)
#Routes đến giới thiệu
@app.route('/about')  # Thêm dấu "/" trước 'about'
def about():
    return render_template('about.html')

if __name__ == "__main__":
    app.run(debug=True)
