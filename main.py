import os

from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy.orm.exc import UnmappedInstanceError
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
Bootstrap5(app)

##CREATE DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI")
db = SQLAlchemy()
db.init_app(app)


##CREATE TABLE
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(700), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    ranking = db.Column(db.Integer, nullable=True)
    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(400), nullable=False)


# with app.app_context():
#     db.create_all()

## After adding the new_movie the code needs to be commented out/deleted.
## So you are not trying to add the same movie twice. The db will reject non-unique movie titles.

# new_movie = Movie(
#     title="Phone Booth",
#     year=2002,
#     description="Publicist Stuart Shepard finds himself trapped in a phone booth, pinned down by an extortionist's sniper rifle. Unable to leave or receive outside help, Stuart's negotiation with the caller leads to a jaw-dropping climax.",
#     rating=7.3,
#     ranking=10,
#     review="My favourite character was the caller.",
#     img_url="https://image.tmdb.org/t/p/w500/tjrX2oWRCM3Tvarz38zlZM7Uc10.jpg"
# )
# second_movie = Movie(
#     title="Avatar The Way of Water",
#     year=2022,
#     description="Set more than a decade after the events of the first film, learn the story of the Sully family (Jake, Neytiri, and their kids), the trouble that follows them, the lengths they go to keep each other safe, the battles they fight to stay alive, and the tragedies they endure.",
#     rating=7.3,
#     ranking=9,
#     review="I liked the water.",
#     img_url="https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg"
# )
# with app.app_context():
#     db.session.add(new_movie)
#     db.session.add(second_movie)
#     db.session.commit()


class RateMovieForm(FlaskForm):
    rating = StringField('Your rating out of 10', validators=[DataRequired()])
    review = StringField('Your review', validators=[DataRequired()])
    submit = SubmitField('Done')


class AddMovieForm(FlaskForm):
    title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie')


@app.route("/")
def home():
    if request.args.get('del_id_num'):
        with app.app_context():
            movie_id = request.args.get('del_id_num')
            movie_to_delete = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
            try:
                db.session.delete(movie_to_delete)
                db.session.commit()
            except UnmappedInstanceError:
                pass
    with app.app_context():
        result = db.session.execute(db.select(Movie).order_by(Movie.rating))
        movies = result.scalars()
        all_movies = [movie for movie in movies]
        for movie in all_movies:
            movie.ranking = len(all_movies) - (all_movies.index(movie))
            db.session.commit()
        return render_template("index.html", all_movies=all_movies)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    movie_id = request.args.get('id_num')
    movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
    db.session.commit()
    title = movie_to_update.title
    form = RateMovieForm()
    if form.validate_on_submit():
        if request.method == "POST":
            movie_id = request.args.get('id_num')
            movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
            movie_to_update.rating = request.form["rating"]
            movie_to_update.review = request.form["review"]
            db.session.commit()
            return redirect(url_for("home"))
    return render_template("edit.html", form=form, title=title)


@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddMovieForm()
    if request.method == "POST":
        if form.validate_on_submit():
            url = "https://api.themoviedb.org/3/search/movie?include_adult=false&language=en-US&page=1"

            headers = {
                "accept": "application/json",
                "Authorization": os.environ["API Read Access Token"]
            }
            parameters = {
                "query": request.form["title"]
            }

            response = requests.get(url, headers=headers, params=parameters)
            data = response.json()["results"]
            return render_template("select.html", data=data)
    return render_template("add.html", form=form)


@app.route("/select", methods=["GET", "POST"])
def select():
    if request.args.get("film_id"):
        film_id = request.args.get("film_id")
        url = f"https://api.themoviedb.org/3/movie/{film_id}?language=en-US"

        headers = {
            "accept": "application/json",
            "Authorization": os.environ["API Read Access Token"]
        }

        response = requests.get(url, headers=headers)
        data = response.json()
        print(data)
        new_movie = Movie(
            title=data["original_title"],
            year=data["release_date"].split("-")[0],
            description=data["overview"],
            img_url=f"https://image.tmdb.org/t/p/w500/{data['poster_path']}"
        )
        with app.app_context():
            db.session.add(new_movie)
            db.session.commit()
            movie = db.session.execute(db.select(Movie).where(Movie.title == data["original_title"])).scalar()
        return redirect(url_for("edit", id_num=movie.id))
    return render_template("index.html")


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
