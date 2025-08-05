from flask import Flask, render_template, request, redirect, flash, session
from werkzeug.utils import secure_filename

import mysql.connector
import os
from dotenv import load_dotenv
app = Flask(__name__)
app.secret_key = 'secret_key'


UPLOAD_FOLDER = 'static/profile_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    cursor.execute('SELECT username, content, id, user_id FROM Posts')
    posts = cursor.fetchall()

    comments_by_post = {}
    cursor.execute('''
        SELECT post_id, username, content 
        FROM messages 
        JOIN users ON messages.sender_id = users.id
    ''')
    comments = cursor.fetchall()
    for comment in comments:
        post_id = comment[0]
        if post_id not in comments_by_post:
            comments_by_post[post_id] = []
        comments_by_post[post_id].append({'username': comment[1], 'content': comment[2]})

    like_post_ids = []
    followed_user_ids = []

    if 'user_id' in session:
        user_id = session['user_id']


        cursor.execute('SELECT post_id FROM Likes WHERE user_id = %s', (user_id,))
        like_post_ids = [row[0] for row in cursor.fetchall()]

   
        cursor.execute('SELECT followed_id FROM Follows WHERE follower_id = %s', (user_id,))
        followed_user_ids = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template(
        'index.html',
        posts=posts,
        like_post_ids=like_post_ids,
        comments_by_post=comments_by_post,
        followed_user_ids=followed_user_ids 
    )
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
@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    if 'user_id' not in session:
        return redirect('/login')

    content = request.form.get('content')
    print(f"Received post_id: {post_id}, content: {content}") 

    if not content:
        return "コメントが空です", 400

    user_id = session['user_id']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (content, sender_id, post_id) VALUES (%s, %s, %s)', (content, user_id, post_id))
    conn.commit()
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
    cursor.execute('INSERT INTO Posts (content,username,user_id) VALUES (%s,%s,%s)', (content,username,user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/follow', methods=['POST'])
def follow():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    followed_user_id = request.form['followed_user_id']

    if str(user_id) == str(followed_user_id):
        flash("自分をフォローすることはできません", "warning")
        return redirect('/')

    conn = get_connection()
    cursor = conn.cursor()

    
    cursor.execute('SELECT * FROM Follows WHERE follower_id = %s AND followed_id = %s', (user_id, followed_user_id))
    follow_record = cursor.fetchone()

    if follow_record:

        cursor.execute('DELETE FROM Follows WHERE follower_id = %s AND followed_id = %s', (user_id, followed_user_id))

        cursor.execute('UPDATE users SET follow_count = follow_count - 1 WHERE id = %s', (user_id,))
        cursor.execute('UPDATE users SET follower_count = follower_count - 1 WHERE id = %s', (followed_user_id,))
        flash("フォローを解除しました", "info")
    else:
      
        cursor.execute('INSERT INTO Follows (follower_id, followed_id) VALUES (%s, %s)', (user_id, followed_user_id))

        
        cursor.execute('UPDATE users SET follow_count = follow_count + 1 WHERE id = %s', (user_id,))
        cursor.execute('UPDATE users SET follower_count = follower_count + 1 WHERE id = %s', (followed_user_id,))
        flash("フォローしました", "success")

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
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT follow_count, follower_count FROM users WHERE id = %s', (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result is None:
        follow_data = [("フォロー", 0), ("フォロワー", 0)]
    else:
        follow_data = [("フォロー", result[0]), ("フォロワー", result[1])]

    return render_template('mypage.html', follow=follow_data)


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
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        profile_image = request.files.get('profile_image')

        print("profile_image:",profile_image)
        print("profile",profile_image.filename if profile_image else "No file uploaded")
        if not username or not password:
            return 'Username and password are required', 400

        profile_image_path = None
        if profile_image and allowed_file(profile_image.filename):
            filename = secure_filename(profile_image.filename)
            profile_image_path = f"{username}_{filename}"
            profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_image_path))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, password, profile_image_path) VALUES (%s, %s, %s)',
            (username, password, profile_image_path)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  