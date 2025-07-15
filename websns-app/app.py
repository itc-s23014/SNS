from flask import Flask, render_template, request, redirect, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'secret_key'

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='flaskuser',         
        password='yourpassword',   
        database='flaskapp'
    )

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            content TEXT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def init_usersdb():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(50) NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def index():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages')
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', messages=messages)

@app.route('/post', methods=['POST'])
def post():
    content = request.form['content']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (content) VALUES (%s)', (content,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/post', methods=['GET'])
def post_form():
    return render_template('post.html')

@app.route('/login', methods=['GET'])
def login_form():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return redirect('/')
    else:
        flash("adress or password is incorret","error")
        cursor.close()
        conn.close()
        return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            return 'Username and password are required', 400
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, password))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/login')
    return render_template('register.html')


if __name__ == '__main__':
    init_db()
    init_usersdb()
    app.run(host='0.0.0.0', port=5000)
