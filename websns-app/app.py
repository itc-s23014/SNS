from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def init_db():
    with sqlite3.connect("messages.db") as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)')

@app.route('/')
def index():
    with sqlite3.connect("messages.db") as conn:
        messages = conn.execute('SELECT * FROM messages').fetchall()
    return render_template('index.html', messages=messages)

@app.route('/post', methods=['POST'])
def post():
    content = request.form['content']
    with sqlite3.connect("messages.db") as conn:
        conn.execute('INSERT INTO messages (content) VALUES (?)', (content,))
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
