from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, flash
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Length, URL
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, FloatField, FieldList
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor, CKEditorField
import csv
import datetime
import requests
import smtplib
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import random
from datetime import date
from time import strftime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import os

now = datetime.datetime.now()
year = now.year

MY_EMAIL = "nathanj0601@gmail.com"
MY_PASSWORD = os.environ['MY_PASSWORD']

app = Flask(__name__)
ckeditor = CKEditor(app)
Bootstrap(app)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.password = "abcde13579"
app.config['SQLALCHEMY_BINDS'] = {
    'movies': 'sqlite:///movies.db',
    'book_collection': 'sqlite:///new-books-collection.db',
    'cafes': 'sqlite:///cafes.db',
    'posts': 'sqlite:///posts.db',
    'user': 'sqlite:///users.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app=app)


def check_admin():
    if current_user.id == 1:
        return True
    else:
        return False


# CONFIGURE TABLE
class BlogPost(db.Model):
    __bind_key__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = []


db.create_all(bind="posts")
db.session.commit()


class Comment(db.Model):
    __bind_key__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)


db.create_all(bind="user")


# WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    author = StringField("Your Name", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class CommentForm(FlaskForm):
    comment_text = StringField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")


@app.route('/')
def home():
    return render_template("index.html", year=year)


@app.route('/blog/post/<int:post_id>', methods=["GET", "POST"])
@login_required
def post_detail(post_id):
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        new_comment = Comment(text=comment_form.comment_text.data)
        for post in db.session.query(BlogPost):
            if post.id == post_id:
                post.comments.append(new_comment)
        db.session.add(new_comment)
        db.create_all(bind="user")
        db.session.commit()
    for post in db.session.query(BlogPost).all():
        if post.id == post_id:
            return render_template("post.html", post=post, year=year, form=comment_form, is_admin=check_admin())
    return render_template("blog.html", is_admin=check_admin())


@app.route('/blog')
@login_required
def blog_home():
    posts = db.session.query(BlogPost).all()
    return render_template("blog.html", all_posts=posts, is_admin=check_admin())


@app.route("/blog/new-post", methods=["GET", "POST"])
@login_required
def new_post():
    if current_user.id != 1:
        return redirect(f"/blog")
    else:
        form = CreatePostForm()
        if form.validate_on_submit():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=form.author.data,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("blog_home"))
        return render_template("make-post.html", form=form, is_edit=False)


@app.route("/blog/edit-post/<post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    if current_user.id != 1:
        return redirect(f"/blog/post/{post_id}")
    else:
        post = BlogPost.query.get(post_id)
        try:
            edit_form = CreatePostForm(
                subtitle=post.subtitle,
                img_url=post.img_url,
                author=post.author,
                body=post.body
            )
        except AttributeError:
            edit_form = CreatePostForm()
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = edit_form.author.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("blog_home", post_id=post.id, is_admin=check_admin()))
        return render_template("make-post.html", form=edit_form, is_edit=True, is_admin=check_admin())


@app.route('/about')
def about():
    return render_template("about.html", year=year)


@app.route('/contact', methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        return render_template("contact.html", year=year, msg_sent=False)
    else:
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]
        with smtplib.SMTP("smtp.gmail.com") as connection:
            connection.starttls()
            connection.login(MY_EMAIL, MY_PASSWORD)
            connection.sendmail(from_addr=email,
                                to_addrs=MY_EMAIL,
                                msg=f"Subject:Blog Message!\n\nName: {name}\nPhone Number: {phone}\nMessage: {message}\nEmail: {email}")

        return render_template("contact.html", year=year, msg_sent=True)


@app.route("/secrets")
def secrets():
    return render_template("secrets.html")


class LoginForm(FlaskForm):
    email = StringField(label="Email: ", validators=[DataRequired(), Email(message='This is not a valid email.')])
    password = PasswordField(label="Password: ", validators=[DataRequired(), Length(min=8, message="This password is less than 8 characters.")])
    submit = SubmitField(label="Log In")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.email.data == MY_EMAIL and form.password.data == app.password:
            return render_template("success.html")
        else:
            return render_template("denied.html")
    else:
        return render_template("login.html", form=form)


app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'


class CafeForm(FlaskForm):
    cafe = StringField("Cafe Name", validators=[DataRequired()])
    location = StringField("Cafe Location On Google Maps", validators=[DataRequired(), URL()])
    opening = StringField("Opening Time e.g. 9AM", validators=[DataRequired()])
    closing = StringField("Closing Time e.g. 5PM", validators=[DataRequired()])
    coffee_rating = SelectField("Food Rating", choices=["✘", "☕", "☕☕", "☕☕☕", "☕☕☕☕", "☕☕☕☕☕"], validators=[DataRequired()])
    wifi_rating = SelectField("Wifi Strength Rating", choices=["✘", "💪", "💪💪", "💪💪💪", "💪💪💪💪", "💪💪💪💪💪"], validators=[DataRequired()])
    power_outlet_rating = SelectField("Power Socket Availability", choices=["✘", "🔌", "🔌🔌", "🔌🔌🔌", "🔌🔌🔌🔌", "🔌🔌🔌🔌🔌"], validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route("/cafe")
def cafe_home():
    return render_template("cafe_main_page.html")


@app.route('/cafe/add', methods=["POST", "GET"])
def add_cafe():
    form = CafeForm()
    if form.validate_on_submit():
        with open("cafe-data.csv", mode="a") as csv_file:
            csv_file.write(f"\n{request.form['cafe']},{request.form['location']},{request.form['opening']},{request.form['closing']},{request.form['coffee_rating']},{request.form['wifi_rating']},{request.form['power_outlet_rating']}")
    return render_template('add_cafe.html', form=form)


@app.route('/cafe/cafes')
def cafes():
    with open('cafe-data.csv', newline='') as csv_file:
        csv_data = csv.reader(csv_file, delimiter=',')
        list_of_rows = []
        for row in csv_data:
            list_of_rows.append(row)
    return render_template('cafes.html', cafes=list_of_rows)


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/book_ratings')
def book_ratings_home():
    books = db.session.query(BookReview).all()
    return render_template('book_rating_homepage.html', ratings=books)


class AddBook(FlaskForm):
    book_name = StringField(label="Book Name", validators=[DataRequired()])
    author = StringField(label="Book Author", validators=[DataRequired()])
    rating = IntegerField("Rating", validators=[DataRequired()])
    submit = SubmitField('Add Book')


class BookReview(db.Model):
    __bind_key__ = 'book_collection'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    rating = db.Column(db.Float, nullable=False)


db.create_all(bind='book_collection')
db.session.commit()


@app.route("/book_ratings/add", methods=["GET", "POST"])
def add_book_rating():
    form = AddBook()
    if form.validate_on_submit():
        book = BookReview(title=request.form['book_name'], author=request.form['author'], rating=request.form['rating'])
        db.session.add()
        db.session.add(book)
        db.session.commit()

        books = db.session.query(BookReview).all()
        return render_template('book_rating_homepage.html', ratings=books)
    return render_template('add_book.html', form=form)


@app.route("/movies")
def movies():
    list_of_movies = db.session.query(MovieList).all()
    return render_template("movie_homepage.html", movies=list_of_movies)


class MovieList(db.Model):
    __bind_key__ = 'movies'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), unique=True, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    ranking = db.Column(db.Integer, unique=True, nullable=False)
    review = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(1000), unique=True, nullable=False)


@app.route("/movies/add", methods=["POST", "GET"])
def add_movie():
    form = AddMovie()
    if form.validate_on_submit():
        movie = MovieList(title=f"{request.form.get('movie_name')}",
                          year=f"{request.form.get('year')}",
                          description=f"{request.form.get('description')}",
                          rating=float(f"{request.form.get('rating')}"),
                          ranking=int(f"{request.form.get('ranking')}"),
                          review=f"{request.form.get('review')}",
                          img_url=f"{request.form.get('url')}")
        db.session.add(movie)
        db.session.commit()
        return redirect(url_for('movies'))
    return render_template("add_movie.html", form=form)


class AddMovie(FlaskForm):

    movie_name = StringField(label="Movie Name", validators=[DataRequired()])
    year = IntegerField(label="Release Year", validators=[DataRequired()])
    description = StringField(label="Movie Description", validators=[DataRequired()])
    rating = FloatField(label="Movie Rating", validators=[DataRequired()])
    ranking = IntegerField(label="Movie Ranking", validators=[DataRequired()])
    review = StringField(label="Movie Review", validators=[DataRequired()])
    url = StringField(label="Movie Image URL", validators=[DataRequired(), URL()])
    submit = SubmitField('Add Movie')


db.create_all(bind="movies")
db.session.commit()


class Cafe(db.Model):
    __bind_key__ = 'cafes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=True)


db.create_all(bind='cafes')


@app.route("/cafeapi")
def cafe_api_home():
    return render_template("cafe_api_index.html")


# HTTP GET - Read Record

@app.route("/cafeapi/random", methods=["GET"])
def random_cafe():
    cafe = random.choice(db.session.query(Cafe).all())
    return jsonify(
        id=cafe.id,
        name=cafe.name,
        map_url=cafe.map_url,
        img_url=cafe.img_url,
        location=cafe.location,
        seats=cafe.seats,
        has_toilet=cafe.has_toilet,
        has_wifi=cafe.has_wifi,
        has_sockets=cafe.has_sockets,
        can_take_calls=cafe.can_take_calls,
        coffee_price=cafe.coffee_price,
    )


@app.route("/cafeapi/all", methods=["GET"])
def all_cafe():
    all_cafes = db.session.query(Cafe).all()
    list_of_cafe_details = []

    for cafe in all_cafes:
        list_of_cafe_details.append(
            {
                "id": cafe.id,
                "name": cafe.name,
                "map_url": cafe.map_url,
                "img_url": cafe.img_url,
                "location": cafe.location,
                "seats": cafe.seats,
                "has_toilet": cafe.has_toilet,
                "has_wifi": cafe.has_wifi,
                "has_sockets": cafe.has_sockets,
                "can_take_calls": cafe.can_take_calls,
                "coffee_price": cafe.coffee_price
            }
        )

    return jsonify(cafes=[cafe_details for cafe_details in list_of_cafe_details])\



@app.route("/cafeapi/search", methods=["GET"])
def find_cafe():
    location = request.args.get("city_name")
    all_cafes = db.session.query(Cafe).all()
    cafe_in_location = False

    for cafe in all_cafes:
        if location.lower() == cafe.location.lower():
            cafe_in_location = True

    if cafe_in_location:
        return jsonify(
            id=cafe.id,
            name=cafe.name,
            map_url=cafe.map_url,
            img_url=cafe.img_url,
            location=cafe.location,
            seats=cafe.seats,
            has_toilet=cafe.has_toilet,
            has_wifi=cafe.has_wifi,
            has_sockets=cafe.has_sockets,
            can_take_calls=cafe.can_take_calls,
            coffee_price=cafe.coffee_price,
        )
    else:
        return jsonify(error={"Not Found": "Sorry, we don't have a cafe at that location."})


# HTTP POST - Create Record


@app.route("/cafeapi/add", methods=["POST"])
def post_new_cafe():
    try:
        new_cafe = Cafe(
            name=request.form.get("name"),
            map_url=request.form.get("map_url"),
            img_url=request.form.get("img_url"),
            location=request.form.get("location"),
            has_sockets=bool(request.form.get("sockets")),
            has_toilet=bool(request.form.get("toilet")),
            has_wifi=bool(request.form.get("wifi")),
            can_take_calls=bool(request.form.get("calls")),
            seats=request.form.get("seats"),
            coffee_price=request.form.get("coffee_price"),
        )
        db.session.add(new_cafe)
        db.session.commit()
        return jsonify(response={"success": "Successfully added the new cafe."})
    except:
        return jsonify(response={"error": "Another cafe in the database already has that name. Please change it to another name. If it is a chain cafe like Starbucks, type a number after it or list it's full name."})


# HTTP PUT/PATCH - Update Record


@app.route("/cafeapi/update-price/<int:cafe_id>", methods=["PATCH"])
def update_price(cafe_id):
    new_price = request.args.get("new_price")
    cafe_found = db.session.query(Cafe).get(cafe_id)
    if cafe_found:
        cafe_found.coffee_price = new_price
        db.session.commit()
        return jsonify(response={"Success": "Successfully updated price in database."})
    else:
        return jsonify(error={"Nor Found": "A cafe with that id wasn't found in the database."}), 404


# HTTP DELETE - Delete Record


@app.route("/cafeapi/report-closed/<int:cafe_id>", methods=["DELETE"])
def delete_record(cafe_id):
    api_key = request.args.get("api_key")
    if api_key == "TopSecretAPIKey":
        cafe = db.session.query(Cafe).get(cafe_id)
        if cafe:
            db.session.delete(cafe)
            db.session.commit()
            return jsonify(response={"success": "Successfully deleted the cafe from the database."}), 200
        else:
            return jsonify(error={"Not Found": "Sorry, a cafe with that id wasn't found in the database."}), 404
    else:
        return jsonify(error={"Forbidden": "Sorry, that's not allowed. Make sure you have the correct API key."}), 403


class User(UserMixin, db.Model):
    __bind_key__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(500), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)


db.create_all(bind="user")
db.session.commit()


@app.route('/login_home')
def login_home():
    return render_template("login_index.html", logged_in=current_user.is_authenticated)


@app.route('/login_home/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(email=request.form.get('email')).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login_to_login', logged_in=current_user.is_authenticated))

        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)

        new_user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=hashed_password
        )

        db.session.add(new_user)
        db.create_all()
        try:
            db.session.commit()
        except:
            return redirect(url_for("login_to_login", logged_in=current_user.is_authenticated))
        login_user(new_user)

        return redirect(url_for("login_secrets", name=new_user.name, logged_in=current_user.is_authenticated))

    return render_template("register.html", logged_in=current_user.is_authenticated)


@app.route('/login_home/login', methods=["POST", "GET"])
def login_to_login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        try:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('login_secrets', name=user.name, logged_in=current_user.is_authenticated))
            else:
                flash("That password is incorrect.")
                return redirect(url_for("login_to_login", logged_in=current_user.is_authenticated))
        except AttributeError:
            flash('An Account With That Email Address Does Not Exist.')
            return redirect(url_for("login_to_login", logged_in=current_user.is_authenticated))

    return render_template("login_loginscreen.html", logged_in=current_user.is_authenticated)


@app.route('/login_home/secrets')
@login_required
def login_secrets():
    print(db.session.query(User).all())
    for n in db.session.query(User).all():
        print(n.password)
    print(current_user.name)
    return render_template("login_secrets.html", name=current_user.name, logged_in=current_user.is_authenticated)


@app.route('/login_home/logout')
def logout():
    logout_user()
    return redirect(url_for("login_home"))


@app.route('/download')
@login_required
def download():
    return send_from_directory('static', filename="files/cheat_sheet.pdf", logged_in=current_user.is_authenticated)


@login_manager.user_loader
def load_login_user(user_id):
    return User.query.get(int(user_id))


@app.errorhandler(404)
def page_not_found():
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
