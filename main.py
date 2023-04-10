import os
import sqlite3

from flask import Flask, render_template, redirect, request, make_response, session, abort, jsonify
from data import db_session
from data.users import User
import datetime
from forms.user import RegisterForm, LoginForm
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_restful import reqparse, abort, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, IMAGES, configure_uploads


from werkzeug.utils import secure_filename

app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/timursalem/PycharmProjects/NGame/db/NGames.db'
app.config['UPLOADED_AVATARS_DEST'] = 'static/images/avatars'
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

db = SQLAlchemy(app)
api = Api(app)

avatars = UploadSet('avatars', IMAGES)
configure_uploads(app, (avatars,))


class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    preview = db.Column(db.String(200))
    fullpreview = db.Column(db.String(200))
    price = db.Column(db.Integer)
    famous = db.Column(db.Integer)
    age_limit = db.Column(db.Integer)
    link = db.Column(db.String(50))
    description = db.Column(db.String(50))
    release_date = db.Column(db.String(50))
    platforms = db.Column(db.String(50))


def generate_single_game_html(game):
    return render_template("games_html/basic_game.html", game=game)


def generate_game_html():
    with app.app_context():
        games = Game.query.all()

        for game in games:
            html = generate_single_game_html(game)

            with open(f"templates/games_html/{game.name.lower().replace(' ', '_')}.html", "w") as f:
                f.write(html)


generate_game_html()

with app.app_context():
    games = Game.query.all()

    for game in games:
        exec(
            f'def game_{str(game.name).replace(" ", "_")}():\n    return render_template("games_html/{str(game.name).lower().replace(" ", "_")}.html", game=game)')
        app.route(f'/{str(game.name).lower().replace(" ", "_")}')(eval(f'game_{str(game.name).replace(" ", "_")}'))


@app.route('/')
def home():
    games = Game.query.all()

    return render_template("home.html", games=games)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/search', methods=['GET', 'POST'])
def search():
    query = request.args.get('q')
    print(query)
    conn = sqlite3.connect('NGames.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM games WHERE name LIKE ?", ('%' + query + '%',))
    games = [game for game in cursor.fetchall()]
    print(games)
    conn.close()
    query = f'По запросу {query} нашлось {len(games)} игр'
    return render_template('search_results.html', games=games, query=query)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    with app.app_context():
        form = RegisterForm()
        if form.validate_on_submit():
            filename = avatars.save(form.profile_image.data)

            if form.password.data != form.password_again.data:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пароли не совпадают")
            db_sess = db_session.create_session()
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")
            user = User(
                name=form.name.data,
                email=form.email.data,
                profile_image=f'/static/images/avatars/{filename}',

            )
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            return redirect('/login')
        return render_template('register.html', title='Регистрация', form=form)


if __name__ == '__main__':
    db_session.global_init("db/users.db")
    app.run(host='0.0.0.0', port=8888, debug=True)
