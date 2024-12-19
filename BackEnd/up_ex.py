from flask import Flask, request, jsonify, render_template, redirect, url_for
import pymysql

app = Flask(__name__)

# Cấu hình MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Thay bằng mật khẩu MySQL của bạn
    "database": "dangnhap",  # Thay bằng tên cơ sở dữ liệu của bạn
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# Hàm kết nối cơ sở dữ liệu
def get_db_connection():
    try:
        return pymysql.connect(**db_config)
    except Exception as e:
        print(f"Không thể kết nối cơ sở dữ liệu: {e}")
        raise

# Trang hiển thị form để thêm bài toán
@app.route('/add-problem-form', methods=['GET'])
def add_problem_form():
    return render_template('admin/form_ex.html')  # File HTML trong `templates/admin/form_ex.html`

# API xử lý thêm bài toán
@app.route('/add-problem', methods=['POST'])
def add_problem():
    data = {}
    
    # Lấy dữ liệu từ form HTML hoặc JSON
    if request.form:
        data = {
            "title": request.form.get("title"),
            "points": request.form.get("points"),
            "time_limit": request.form.get("time_limit"),
            "memory_limit": request.form.get("memory_limit"),
            "description": request.form.get("description"),
            "input_format": request.form.get("input_format"),
            "output_format": request.form.get("output_format"),
            "scoring": request.form.get("scoring"),
            "examples": request.form.get("examples"),
            "notifications": request.form.get("notifications", None)
        }
    elif request.json:
        data = request.json

    # Kiểm tra tính hợp lệ của dữ liệu
    required_fields = ["title", "points", "time_limit", "memory_limit", "description",
                       "input_format", "output_format", "scoring", "examples"]
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({"message": f"Thiếu các trường: {', '.join(missing_fields)}"}), 400

    try:
        # Kết nối cơ sở dữ liệu
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Câu lệnh SQL thêm bài toán
            sql = """
                INSERT INTO problems (title, points, time_limit, memory_limit, description, 
                                      input_format, output_format, scoring, examples, notifications)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['title'],
                data['points'],
                data['time_limit'],
                data['memory_limit'],
                data['description'],
                data['input_format'],
                data['output_format'],
                str(data['scoring']),  # Chuyển JSON sang chuỗi
                str(data['examples']),  # Chuyển JSON sang chuỗi
                data.get('notifications')
            ))
            connection.commit()

        if request.form:  # Nếu từ form HTML
            return redirect(url_for('add_problem_form'))
        return jsonify({"message": "Bài toán đã được thêm thành công!"}), 201
    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({"message": f"Lỗi MySQL: {str(e)}"}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Đã xảy ra lỗi trong quá trình thêm bài toán."}), 500
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    app.run(debug=True)
