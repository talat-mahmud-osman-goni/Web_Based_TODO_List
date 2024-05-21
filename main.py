from flask_bootstrap import Bootstrap
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from werkzeug.security import generate_password_hash, check_password_hash

from form import TodoForm, LoginForm, RegisterForm
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEYS')
Bootstrap(app)


# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI', 'sqlite:///posts.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Todo(db.Model):
    __tablename__ = "todo"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    todo_list: Mapped[str] = mapped_column(String(250), nullable=True)


# Create a User table for all your registered users
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))


with app.app_context():
    db.create_all()


todo_list = []


# Register new users into the User database
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        # Check if user email is already present in the database.
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        # This line will authenticate the user with Flask-Login
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/", methods=["GET", "POST"])
def home():
    todo_form = TodoForm()
    if todo_form.validate_on_submit():
        todo_list.append(todo_form.todo_input.data)
        todo_form.todo_input.data = ""

    if request.method == 'POST':
        checked_items = request.form.getlist('todo_item')
        if checked_items:
            for item in checked_items:
                todo_list.remove(item)
                if current_user.is_authenticated:
                    list_to_delete = db.session.execute(db.select(Todo).where(Todo.user_id == current_user.id,
                                                                              Todo.todo_list == item)).scalars().first()
                    if list_to_delete:
                        db.session.delete(list_to_delete)
                        db.session.commit()

    return render_template('index.html', todo_form=todo_form, todo_list=todo_list, current_user=current_user)


@app.route("/new_list")
def new_list():
    if todo_list:
        todo_list.clear()
    return redirect(url_for('home'))


@app.route("/save_list", methods=["GET", "POST"])
def save_list():
    if todo_list:
        for item in todo_list:
            new_todo = Todo(
                user_id=current_user.id,  # Access the id attribute of current_user
                todo_list=item
            )
            db.session.add(new_todo)
            db.session.commit()
        return redirect(url_for("home"))
    return redirect(url_for("home"))


@app.route("/my_list/<int:user_id>", methods=["GET", "POST"])
def my_list(user_id):
    if current_user.id == user_id:
        user_todos = db.session.execute(db.select(Todo.todo_list).where(Todo.user_id == user_id)).scalars().all()
        todo_list.clear()
        for item in user_todos:
            todo_list.append(item)
        print(user_todos)
        return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
