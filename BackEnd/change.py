from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import rarfile
import json
import pymysql

app = Flask(__name__)

# Cấu hình thư mục
DATASET = "uploads"
EXTRACT_FOLDER = "extracted"
RESULT_FOLDER = "test"
os.makedirs(DATASET, exist_ok=True)
os.makedirs(EXTRACT_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Cấu hình đường dẫn đến unrar.exe (của WinRAR)
rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\unrar.exe"

# Kết nối với MySQL bằng pymysql
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="dangnhap",
        cursorclass=pymysql.cursors.DictCursor  # Sử dụng DictCursor để trả về kết quả dưới dạng từ điển
    )

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

if __name__ == "__main__":
    app.run(debug=True)
