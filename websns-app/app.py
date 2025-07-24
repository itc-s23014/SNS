from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector
import os
from dotenv import load_dotenv
app = Flask(__name__)
app.secret_key = 'secret_key'

load_dotenv()
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
@app.route('/')
def index():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, content,id FROM Posts')

    posts = cursor.fetchall()

    like_post_ids = []
    if 'user_id' in session:
        user_id = session['user_id']
        cursor.execute('SELECT post_id FROM Likes WHERE user_id = %s', (user_id,))
        like_post_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('index.html', posts=posts,like_post_ids=like_post_ids)

@app.route('/like', methods=['POST'])
def like_post():
    if 'user_id' not in session:
        return redirect('/login')

    post_id = request.form['post_id']
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM Likes WHERE post_id = %s AND user_id = %s', (post_id, user_id))

    if cursor.fetchone():
    
        cursor.execute('DELETE FROM Likes WHERE post_id = %s AND user_id = %s', (post_id, user_id))
        conn.commit()
        flash("Like removed.", "info")
    else:
      
        cursor.execute('INSERT INTO Likes (post_id, user_id) VALUES (%s, %s)', (post_id, user_id))
        conn.commit()
        flash("Post liked successfully!", "success")

    cursor.close()
    
    conn.close()
    return redirect('/')


@app.route('/post', methods=['POST'])
def post():
    if 'user_id' not in session:
        return redirect('/login')
    
    content = request.form['content']
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    username = user[0] if user else '名無し'
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Posts (content,username) VALUES (%s,%s)', (content,username))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/',methods=['postpagebtn'])
def page_post_transition():
    return redirect('/post')

@app.route('/', methods=['mypagebtn'])
def page_mypage_transition():
    return redirect('/mypage')


@app.route('/mypage', methods=['GET'])
def mypage():
    return render_template('mypage.html')

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
        session['user_id'] = user[0]
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
    app.run(host='0.0.0.0', port=5000, debug=True)  