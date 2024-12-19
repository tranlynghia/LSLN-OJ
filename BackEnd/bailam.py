import os
import json
from flask import Flask, request, render_template, jsonify
import subprocess
import tempfile
import pymysql

app = Flask(__name__)

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
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['TEST_FOLDER'] = 'test'  # Thư mục chứa các file test

# Hàm kết nối cơ sở dữ liệu
def get_db_connection():
    return pymysql.connect(**db_config)

# Hàm đọc file JSON
def read_json_file(file_name, default_value=None):
    file_path = os.path.join(JSON_FILES_DIRECTORY, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default_value
    except json.JSONDecodeError as e:
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
            scoring_file = problem.get('scoring_file')
            examples_file = problem.get('examples_file')

            # Đọc nội dung từ file JSON
            problem['scoring'] = read_json_file(scoring_file, [])
            problem['examples'] = read_json_file(examples_file, [])

            # Trả kết quả về template
            return render_template('question_info.html', problem=problem)
        else:
            return "Bài toán không tồn tại.", 404

    except pymysql.MySQLError as e:
        return f"Lỗi cơ sở dữ liệu: {str(e)}", 500

    finally:
        if connection:
            connection.close()

# Hàm chấm bài
def grade_submission(filepath, language, test_file_name):
    correct = 0
    details = []
    test_folder = app.config['TEST_FOLDER']
    
    test_path = os.path.join(test_folder, test_file_name)
    
    if os.path.isfile(test_path):
        with open(test_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        input_data = test_data.get('input', '')
        expected_output = test_data.get('output', '')
        
        try:
            command = get_execution_command(filepath, language)
            result = subprocess.run(command, input=input_data, text=True, capture_output=True, timeout=5)
            
            if result.stdout.strip() == expected_output.strip():
                correct += 1
                details.append({"test_case": test_file_name, "score": 50, "time": "0.1s", "status": "Accepted"})
            else:
                details.append({"test_case": test_file_name, "score": 0, "time": "0.1s", "status": "Rejected"})
        except Exception as e:
            details.append({"test_case": test_file_name, "score": 0, "time": "N/A", "status": f"Error: {str(e)}"})
    
    total_tests = 1
    return {"total": total_tests, "correct": correct, "details": details, "total_score": correct * 50, "grade": round(correct / total_tests * 5, 2)}

# Hàm lấy lệnh thực thi cho từng ngôn ngữ
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

# Trang nộp bài
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        try:
            if 'file' in request.files and request.files['file'].filename:
                uploaded_file = request.files['file']
                temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
                uploaded_file.save(temp_filepath)
            else:
                code = request.form['code']
                language = request.form['language']
                with tempfile.NamedTemporaryFile(suffix=get_file_extension(language), delete=False) as temp_file:
                    temp_file.write(code.encode())
                    temp_filepath = temp_file.name

            test_file_name = request.form['test_file']
            language = request.form['language']
            result = grade_submission(temp_filepath, language, test_file_name)
            os.unlink(temp_filepath)  # Xóa file sau khi chấm
            return jsonify(result)
        except Exception as e:
            return jsonify({"message": str(e)}), 500
    return render_template('submit.html')

# Trang chủ
@app.route('/')
def index():
    return render_template('question_info.html')

if __name__ == '__main__':
    app.run(debug=True)
