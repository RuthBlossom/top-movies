# Import necessary modules from Flask, Flask extensions, SQLAlchemy, and other libraries
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

# Constants for The Movie Database (TMDB) API
MOVIE_DB_API_KEY = "USE_YOUR_OWN_CODE"  # API key for authenticating with TMDB
MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"  # URL for searching movies
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"  # URL for getting movie details
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"  # Base URL for movie poster images

# Initialize the Flask application
app = Flask(__name__)
# Secret key for securely signing the session cookie and can be used for any other security-related needs by extensions or your application
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
# Initialize Bootstrap5 for styling the application
Bootstrap5(app)

# Define the base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Set the database URI to use SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
# Initialize SQLAlchemy with the custom base class
db = SQLAlchemy(model_class=Base)
# Attach the Flask app to the SQLAlchemy instance
db.init_app(app)

# Define the Movie model which will correspond to a table in the database
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Primary key column
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)  # Title column, must be unique and not null
    year: Mapped[int] = mapped_column(Integer, nullable=False)  # Year column, not null
    description: Mapped[str] = mapped_column(String(500), nullable=False)  # Description column, not null
    rating: Mapped[float] = mapped_column(Float, nullable=True)  # Rating column, can be null
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)  # Ranking column, can be null
    review: Mapped[str] = mapped_column(String(250), nullable=True)  # Review column, can be null
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)  # Image URL column, not null

# Create all the tables in the database (only necessary once)
with app.app_context():
    db.create_all()

# Define a WTForm for finding movies
class FindMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])  # Input field for movie title, required
    submit = SubmitField("Add Movie")  # Submit button

# Define a WTForm for rating and reviewing movies
class RateMovieForm(FlaskForm):
    rating = StringField("Your Rating Out of 10 e.g. 7.5")  # Input field for rating
    review = StringField("Your Review")  # Input field for review
    submit = SubmitField("Done")  # Submit button

# Route for the home page
@app.route("/")
def home():
    # Query all movies ordered by rating
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    all_movies = result.scalars().all()  # Convert result to a list of movies

    # Assign ranking to each movie based on its position in the sorted list
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()  # Commit changes to the database

    # Render the index.html template, passing the list of movies
    return render_template("index.html", movies=all_movies)

# Route for adding a new movie
@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = FindMovieForm()  # Create an instance of the FindMovieForm
    if form.validate_on_submit():  # Check if the form is submitted and valid
        movie_title = form.title.data  # Get the movie title from the form
        # Make a request to the TMDB search API to find movies matching the title
        response = requests.get(MOVIE_DB_SEARCH_URL, params={
            "api_key": MOVIE_DB_API_KEY, "query": movie_title})
        data = response.json()["results"]  # Extract the results from the response
        # Render the select.html template, passing the search results
        return render_template("select.html", options=data)
    # Render the add.html template, passing the form
    return render_template("add.html", form=form)

# Route for finding movie details and adding the movie to the database
@app.route("/find")
def find_movie():
    movie_api_id = request.args.get("id")  # Get the movie ID from the query string
    if movie_api_id:
        movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_api_id}"  # Construct the API URL for the movie
        # Make a request to the TMDB API to get movie details
        response = requests.get(movie_api_url, params={
            "api_key": MOVIE_DB_API_KEY, "language": "en-US"})
        data = response.json()  # Extract the data from the response
        # Create a new movie instance with the data from the API
        new_movie = Movie(
            title=data["title"],
            year=data["release_date"].split("-")[0],
            img_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
            description=data["overview"]
        )
        db.session.add(new_movie)  # Add the new movie to the session
        db.session.commit()  # Commit the session to save the movie to the database
        # Redirect to the route for rating the new movie
        return redirect(url_for("rate_movie", id=new_movie.id))

# Route for editing (rating and reviewing) a movie
@app.route("/edit", methods=["GET", "POST"])
def rate_movie():
    form = RateMovieForm()  # Create an instance of the RateMovieForm
    movie_id = request.args.get("id")  # Get the movie ID from the query string
    movie = db.get_or_404(Movie, movie_id)  # Get the movie from the database or return a 404 error
    if form.validate_on_submit():  # Check if the form is submitted and valid
        movie.rating = float(form.rating.data)  # Update the movie's rating
        movie.review = form.review.data  # Update the movie's review
        db.session.commit()  # Commit the session to save the changes
        # Redirect to the home page
        return redirect(url_for('home'))
    # Render the edit.html template, passing the movie and form
    return render_template("edit.html", movie=movie, form=form)

# Route for deleting a movie
@app.route("/delete")
def delete_movie():
    movie_id = request.args.get("id")  # Get the movie ID from the query string
    movie = db.get_or_404(Movie, movie_id)  # Get the movie from the database or return a 404 error
    db.session.delete(movie)  # Delete the movie from the session
    db.session.commit()  # Commit the session to remove the movie from the database
    # Redirect to the home page
    return redirect(url_for("home"))

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)  # Start the app in debug mode for detailed error messages

