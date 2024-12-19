from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Bộ nhớ tạm cho danh sách đề bài
problems = []

@app.route('/')
def index():
    return render_template('index.html', problems=problems)

@app.route('/add-problem', methods=['GET', 'POST'])
def add_problem():
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        title = request.form['title']
        points = request.form['points']
        time_limit = request.form['time_limit']
        memory_limit = request.form['memory_limit']
        description = request.form['description']
        input_format = request.form['input_format']
        output_format = request.form['output_format']
        examples = request.form['examples']
        notifications = request.form['notifications']

        # Thêm đề bài vào danh sách
        problems.append({
            'title': title,
            'points': points,
            'time_limit': time_limit,
            'memory_limit': memory_limit,
            'description': description,
            'input_format': input_format,
            'output_format': output_format,
            'examples': examples,
            'notifications': notifications
        })

        return redirect(url_for('index'))

    return render_template('add_problem.html')

@app.route('/problem/<int:problem_id>')
def problem(problem_id):
    # Hiển thị đề bài chi tiết
    problem = problems[problem_id]
    return render_template('problem.html', problem=problem)

if __name__ == '__main__':
    app.run(debug=True)
