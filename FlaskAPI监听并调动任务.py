from flask import Flask, request, jsonify
import re
import redis
import os


app = Flask(__name__)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

print("Current working directory:", os.getcwd())

def sanitize_filename(name):
    """清理文件名，移除不合法字符"""
    return re.sub(r'[\\/*?:"<>|]', '', name)


@app.route('/add_books', methods=['POST'])
def add_books():
    data = request.json
    books = data.get('books', [])

    for book_name in books:
        redis_client.lpush('task_queue', book_name)  # 使用 lpush 添加任务到 Redis
        app.logger.info(f"Task added to Redis: {book_name}")  # 记录日志

    return jsonify({"message": f"{len(books)} books added to the queue."})

import os

@app.route('/get_book_text', methods=['POST'])
def get_book_text():
    print("Flask current working directory:", os.getcwd())
    data = request.json
    book_name = data.get('book_name')
    if not book_name:
        return jsonify({"error": "Book name is required"}), 400

    safe_book_name = sanitize_filename(book_name)
    txt_file_name = f"{safe_book_name}.txt"

    print(f"Trying to open file: {txt_file_name}")  # 打印要打开的文件名

    try:
        with open(txt_file_name, 'r', encoding='utf-8') as file:
            content = file.read()
        return jsonify({"book_name": book_name, "content": content})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/test', methods=['GET'])
def test_route():
    return "Test route is working"


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
