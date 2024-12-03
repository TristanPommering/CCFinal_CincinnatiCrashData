from flask import Flask, render_template
from sqlalchemy import create_engine
import pyodbc
import os

app = Flask(__name__)

# Azure SQL Database connection with managed identity
def get_connection_string():
    server = "trafficscrash-server.database.windows.net"
    database = "TrafficCrashDB"
    driver = "ODBC Driver 17 for SQL Server"
    return f"Driver={{{driver}}};Server={server};Database={database};Authentication=ActiveDirectoryMsi;Encrypt=yes;TrustServerCertificate=no;"

connection_string = get_connection_string()
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={connection_string}")

@app.route("/")
def index():
    try:
        # Fetch data from the database
        with engine.connect() as connection:
            result = connection.execute("SELECT TOP 10 * FROM dbo.CrashData")
            rows = [dict(row) for row in result]

        # Render data in the HTML template
        return render_template("index.html", data=rows)
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    app.run(debug=True)
