from flask import Flask, render_template, request
import pymysql
import json
import os

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



if __name__ == '__main__':
    # Tạo debug log kiểm tra thư mục
    if not os.path.exists(JSON_FILES_DIRECTORY):
        print(f"ERROR: Thư mục {JSON_FILES_DIRECTORY} không tồn tại.")
    else:
        print(f"DEBUG: Thư mục {JSON_FILES_DIRECTORY} tồn tại.")

    app.run(debug=True)
