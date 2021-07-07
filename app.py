from flask import Flask, render_template, session, request, redirect, url_for, send_from_directory
from werkzeug.datastructures import ImmutableDict
from werkzeug.utils import secure_filename
from wtforms import Form, TextAreaField, validators
from datetime import datetime, date, timedelta
from vectorizer import vect
from update import update_model
import pickle
import sqlite3
import os
import numpy as np

class FlaskWithHamlish(Flask):
    jinja_options = ImmutableDict(
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_', 'hamlish_jinja.HamlishExtension']
    )

app = FlaskWithHamlish(__name__)
app.config['SECRET_KEY'] = 'The secret key which ciphers the cookie'
app.jinja_env.hamlish_mode = 'indented'
app.jinja_env.hamlish_enable_div_shortcut = True

# 分類機の準備
cur_dir = os.path.dirname(__file__)
clf = pickle.load(open(os.path.join(cur_dir, 'pkl_objects', 'classifier.pkl'),
                       'rb'))
db = os.path.join(cur_dir, 'reviews.sqlite')

def classify(document):
    label = {0: 'negative', 1: 'positive'}
    X = vect.transform([document])
    y = clf.predict(X)[0]
    proba = clf.predict_proba(X).max()
    return label[y], proba

def train(document, y):
    X = vect.transform([document])
    clf.partial_fit(X, [y])

def sqlite_entry(path, document, y):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("INSERT INTO review_db (review, sentiment, date)"\
              " VALUES (?, ?, DATETIME('now'))", (document, y))
    conn.commit()
    conn.close()

# Flask
class ReviewForm(Form):
    moviereview = TextAreaField('',
                                [validators.DataRequired(),
                                 validators.length(min=15)])

# @app.before_request
# def before_request():
#     if session.get('username') is not None:
#         return
#     if request.path == '/login':
#         return
#     return redirect('/login')

# @app.before_request
# def load_logged_in_user():
#     user_id = session.get('user_id')

#     if user_id is None:
#         g.user = None
#     else:
#         db = get_db()
#         g.user = db.execute(
#             'SELECT * FROM user WHERE id = ?',(user_id,)
#         ).fetchone()

@app.route('/create_user', methods=['GET','POST'])
def create_user():
    if request.method == 'GET':
        return render_template('auth/create_user.haml', title='ユーザー登録', year=datetime.now().year)
    
    username = request.form['username']
    password = request.form['password']

    db = get_db()

    error_message = None

    if not username:
        error_message = 'ユーザー名の入力は必須です'
    elif not password:
        error_message = 'パスワードの入力は必須です'
    elif db.execute('SELECT id FROM user WHERE username=?', (username,)).fetchone()is not None:
        error_message = 'ユーザー名{}はすでに使用されています'.format(username)

    if error_message is not None:
        flash(error_message, category='alert alert-danger')
        return redirect(url_for('create_user'))

    db.execute(
        'INSERT INTO user (username, password) VALUES(?,?)',
        (username, generate_password_hash(password))
    )
    db.commit()

    flash('ユーザーログインが完了しました。登録した内容でログインしてください', category='alert alert-info')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.haml',
                                title='ログイン',
                                year=datetime.now().year)
    
    username = request.form['username']
    password = request.form['password']

    db = get_db()

    error_message = None

    user = db.execute(
        'SELECT * FROM user WHERE username = ?',(username,)
    ).fetchone()

    if user is None:
        error_message = 'ユーザー名が正しくありません'
    elif not check_password_hash(user['password'],password):
        error_message = 'パスワードが正しくありません'

    if error_message is not None:
        flash(error_message,category='alert alert-danger')
        return reedirect(url_for('login'))
    
    session.clear()
    session['user_id'] = user['id']
    flash('{}さんとしてログインしました'.format(username),category='alert alert-info')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました',category='alert alert-info')
    return redirect(url_for('index'))



@app.route('/index')
def index():
    form = ReviewForm(request.form)
    return render_template('reviewform.haml', form=form)

# @app.route('/login', methods=['GET','POST'])
# def login():
#     if request.method == 'POST' and _is_account_valid():
#         session['username'] == request.form['username']
#         return redirect(url_for('index'))
#     return render_template("login.haml")

# def _is_account_valid():
#     if request.form.get('username') is None:
#         return False
#     return True

# @app.route('/logout', methods=['GET'])
# def logout():
#     session.pop('username', None)
#     return redirect(url_for('login'))

@app.route('/results', methods=['POST'])
def results():
    form = ReviewForm(request.form)
    if request.method == 'POST' and form.validate():
        review = request.form['moviereview']
        y, proba = classify(review)
        return render_template('results.haml',
                               content=review,
                               prediction=y,
                               probability=round(proba*100, 2))
    return render_template('reviewform.haml', form=form)

@app.route('/thanks', methods=['POST'])
def feedback():
    feedback = request.form['feedback_button']
    review = request.form['review']
    prediction = request.form['prediction']

    inv_label = {'negative': 0, 'positive': 1}
    y = inv_label[prediction]
    if feedback == 'Incorrect':
        y = int(not(y))
    train(review, y)
    sqlite_entry(db, review, y)
    return render_template('thanks.haml')

if __name__ == '__main__':
    app.run(debug=True)
    clf = update_model(db_path=db, model=clf, batch_size=10000)