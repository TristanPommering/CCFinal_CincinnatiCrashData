from flask import Flask, render_template
from sqlalchemy import create_engine
import os

app = Flask(__name__)

connection_string = os.getenv("sql_a8293")

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={connection_string}")

@app.route("/")
def index():
    with engine.connect() as connection:
        result = connection.execute("SELECT TOP 10 * CrashData")
        rows = [dict(row) for row in result]

    return render_template("index.html", data=rows)

if __name__ == "__main__":
    app.run(debug=True)
