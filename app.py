
import os
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from data_models import db, Author, Book


app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'data/library.sqlite')}"
)

# Nur für die lokale Entwicklung
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "development-only-secret"
)

db.init_app(app)


# ----------------------------------
# Startseite
# ----------------------------------


@app.route("/")
def home():
    sort_by = request.args.get("sort", "title")
    search_term = request.args.get("search", "").strip()

    stmt = select(Book).options(selectinload(Book.author))

    # Stichwortsuche
    if search_term:
        stmt = stmt.where(Book.title.ilike(f"%{search_term}%"))

    # Sortierung
    if sort_by == "author":
        stmt = stmt.join(Book.author).order_by(
            Author.name, Book.title
        )
    else:
        sort_by = "title"
        stmt = stmt.order_by(Book.title)

    books = db.session.scalars(stmt).all()

    return render_template(
        "home.html",
        books=books,
        sort_by=sort_by,
        search_term=search_term
    )



# ----------------------------------
# Autoren hinzufügen
# ----------------------------------

@app.route("/add_author", methods=["GET", "POST"])
def add_author():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        birth_date_str = request.form.get("birthdate", "")
        death_date_str = request.form.get("date_of_death", "")

        try:
            birth_date = date.fromisoformat(birth_date_str)

            date_of_death = (
                date.fromisoformat(death_date_str)
                if death_date_str else None
            )

        except ValueError:
            flash("Bitte gültige Datumswerte eingeben.", "error")

        else:
            if not name:
                flash("Der Name darf nicht leer sein.", "error")

            elif date_of_death and date_of_death < birth_date:
                flash("Das Todesdatum ist ungültig.", "error")

            else:
                author = Author(
                    name=name,
                    birth_date=birth_date,
                    date_of_death=date_of_death
                )

                db.session.add(author)
                db.session.commit()

                flash("Autor erfolgreich hinzugefügt!", "success")
                return redirect(url_for("add_author"))

    return render_template("add_author.html")


# ----------------------------------
# Bücher hinzufügen
# ----------------------------------

@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip()
        title = request.form.get("title", "").strip()

        try:
            publication_year = int(
                request.form.get("publication_year", "")
            )
            author_id = int(request.form.get("author_id", ""))

        except ValueError:
            flash("Ungültige Jahreszahl oder Autor-ID.", "error")

        else:
            author = db.session.get(Author, author_id)

            if not isbn or not title or publication_year <= 0:
                flash("Bitte gültige Buchdaten eingeben.", "error")

            elif author is None:
                flash("Der ausgewählte Autor existiert nicht.", "error")

            else:
                book = Book(
                    isbn=isbn,
                    title=title,
                    publication_year=publication_year,
                    author_id=author_id
                )

                db.session.add(book)

                try:
                    db.session.commit()

                except IntegrityError:
                    db.session.rollback()
                    flash(
                        "Buch konnte nicht gespeichert werden. "
                        "Möglicherweise existiert die ISBN bereits.",
                        "error"
                    )

                else:
                    flash("Buch erfolgreich hinzugefügt!", "success")
                    return redirect(url_for("add_book"))

    authors = db.session.scalars(
        select(Author).order_by(Author.name)
    ).all()

    return render_template("add_book.html", authors=authors)


# ----------------------------------
# Bücher löschen
# ----------------------------------

@app.route("/book/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    book = db.session.get(Book, book_id)

    if book is None:
        flash("Book not found.", "error")
        return redirect(url_for("home"))

    book_title = book.title

    db.session.delete(book)
    db.session.commit()

    flash(f'Book "{book_title}" deleted successfully!', "success")

    return redirect(url_for("home"))



if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=5002, debug=True)
