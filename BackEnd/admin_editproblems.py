import os
import json
from flask import Flask, render_template, request, redirect, url_for
import pymysql

app = Flask(__name__)

# Đường dẫn tới thư mục chứa file JSON và các file tải lên
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Hàm kết nối cơ sở dữ liệu
def get_db_connection():
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "",  # Thay bằng mật khẩu MySQL của bạn
        "database": "dangnhap",  # Tên database của bạn
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor
    }
    return pymysql.connect(**db_config)

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

# Chạy ứng dụng Flask
if __name__ == '__main__':
    app.run(debug=True)
