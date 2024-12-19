import os
import subprocess
import tempfile
import json
import pymysql
from flask import Flask, render_template, request

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

# Đọc dữ liệu từ file JSON
def read_json_file(filename, default_value):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
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
    # Đường dẫn file đáp án (dựa trên problem_id)
    answer_file = os.path.join(TEST_FOLDER, f"scoring_{problem_id}.json")

    if not os.path.exists(answer_file):
        return {"error": "File chấm điểm không tồn tại"}

    # Đọc file chấm điểm
    scoring_data = read_json_file(answer_file, {})
    
    if not scoring_data:
        return {"error": "Dữ liệu chấm điểm không hợp lệ"}

    # Chạy mã code của người dùng (giả sử đã có mã code cần chấm)
    try:
        command = get_execution_command(filepath, language)
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = result.stdout

        # So sánh kết quả đầu ra với kết quả chấm điểm
        # (Giả sử scoring_data có một trường "expected_output" để so sánh)
        expected_output = scoring_data.get("expected_output", "")
        if output.strip() == expected_output.strip():
            return {"result": "Đúng", "score": scoring_data.get("score", 0)}
        else:
            return {"result": "Sai", "score": 0}

    except subprocess.CalledProcessError as e:
        return {"error": f"Lỗi khi chạy mã: {e}"}

if __name__ == '__main__':
    app.run(debug=True)
