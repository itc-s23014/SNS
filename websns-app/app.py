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
def like_post_api():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'ログインが必要です'}), 401

    try:
        data = request.get_json()
        post_id = data.get('post_id')
        action = data.get('action')
        user_id = session['user_id']

        if not post_id or not action:
            return jsonify({'status': 'error', 'message': '不正なリクエストです'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        liked_status = False
        if action == 'like':
            cursor.execute('INSERT INTO Likes (post_id, user_id) VALUES (%s, %s)', (post_id, user_id))
            liked_status = True
        elif action == 'unlike':
            cursor.execute('DELETE FROM Likes WHERE post_id = %s AND user_id = %s', (post_id, user_id))
            liked_status = False
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'liked': liked_status
        })

    except Exception as e:
        print(f"Error in /like API: {e}")
        return jsonify({'status': 'error', 'message': 'サーバーエラーが発生しました'}), 500

@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    if 'user_id' not in session:
        return redirect('/login')

    content = request.form.get('content')
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
        return jsonify({'status': 'error', 'message': 'ログインが必要です。'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'データがありません。'}), 400
            
        followed_user_id = data.get('followed_user_id')
        action = data.get('action') 
        follower_id = session['user_id'] 

        if str(follower_id) == str(followed_user_id):
            return jsonify({'status': 'error', 'message': '自分自身をフォローすることはできません。'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        new_state = False
        if action == 'follow':
 
            cursor.execute('INSERT INTO Follows (follower_id, followed_id) VALUES (%s, %s)', (follower_id, followed_user_id))
            
            cursor.execute('UPDATE users SET follow_count = follow_count + 1 WHERE id = %s', (follower_id,))
        
            cursor.execute('UPDATE users SET follower_count = follower_count + 1 WHERE id = %s', (followed_user_id,))
            
            
            new_state = True

        elif action == 'unfollow':
            
            cursor.execute('DELETE FROM Follows WHERE follower_id = %s AND followed_id = %s', (follower_id, followed_user_id))

            cursor.execute('UPDATE users SET follow_count = GREATEST(0, follow_count - 1) WHERE id = %s', (follower_id,))
            
            cursor.execute('UPDATE users SET follower_count = GREATEST(0, follower_count - 1) WHERE id = %s', (followed_user_id,))
         

            new_state = False
        
        else:
            return jsonify({'status': 'error', 'message': '無効なアクションです。'}), 400

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'followed': new_state})

    except Exception as e:
        print(f"Error in /follow route: {e}") 
        return jsonify({'status': 'error', 'message': 'サーバーエラーが発生しました。'}), 500

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

    cursor.execute('SELECT username FROM users WHERE id = %s', (user_id,))
    username = cursor.fetchone()[0]

    cursor.execute('SELECT follow_count, follower_count FROM users WHERE id = %s', (user_id,))
    result = cursor.fetchone()
    if result is None:
        follow_data = [("フォロー", 0), ("フォロワー", 0)]
    else:
        follow_data = [("フォロー", result[0]), ("フォロワー", result[1])]

    cursor.execute('''
        SELECT Posts.id, Posts.content, Posts.username
        FROM Likes
        JOIN Posts ON Likes.post_id = Posts.id
        WHERE Likes.user_id = %s
    ''', (user_id,))
    liked_posts = cursor.fetchall()
    print("liked_posts:", liked_posts)  

    cursor.execute('''
    SELECT 
        messages.id,              
        messages.content,           
        messages.post_id,           
        Posts.content,              
        users.username              
    FROM messages
    JOIN Posts ON messages.post_id = Posts.id
    JOIN users ON Posts.user_id = users.id
    WHERE messages.sender_id = %s
''', (user_id,))
    my_comments = cursor.fetchall()
    print("my_comments:", my_comments)  

    cursor.execute('''
        SELECT id, content, username FROM Posts WHERE user_id = %s
    ''', (user_id,))
    my_posts = cursor.fetchall()


    posts_with_posts = []
    for post in my_posts:
        post_id, content, username = post
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT messages.content, users.username
        FROM messages
        JOIN users ON messages.sender_id = users.id
        WHERE messages.post_id = %s
    ''', (post_id,))
        comments = cursor.fetchall()
        posts_with_posts.append({
        'id': post_id,
        'content': content,
        'username': username,
        'comments': comments
    })
    cursor.close()
    conn.close()

    return render_template(
    'mypage.html',
    follow=follow_data,
    liked_posts=liked_posts,
    my_comments=my_comments,
    my_posts=my_posts,
    my_comment=my_comments,
    username=username,
    posts_with_posts=posts_with_posts
)

@app.route('/edit_username', methods=['POST'])
def edit_username():
    if 'user_id' not in session:
        return redirect('/login')
    new_username = request.form['new_username']
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET username = %s WHERE id = %s', (new_username, user_id))
    cursor.execute('UPDATE Posts SET username = %s WHERE user_id = %s', (new_username, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash("ユーザーネームを変更しました", "success")
    return redirect('/mypage')
        
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