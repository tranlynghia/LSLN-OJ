from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Để sử dụng flash message

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

# Route thêm bài toán
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

if __name__ == '__main__':
    app.run(debug=True)
