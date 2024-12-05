from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy import text
import pyodbc

app = Flask(__name__)

def get_connection_string():
    server = "trafficscrash-server.database.windows.net"
    database = "TrafficCrashDB"
    driver = "ODBC Driver 17 for SQL Server"
    return f"Driver={{{driver}}};Server={server};Database={database};Authentication=ActiveDirectoryMsi;Encrypt=yes;TrustServerCertificate=no;"

connection_string = get_connection_string()
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={connection_string}")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/crash-data", methods=["GET"])
def get_crash_data():
    # Get UNITTYPE filter from the request (default: None)
    unit_type = request.args.get("unit_type", None)

    try:
        with engine.connect() as connection:
            # Base query to get crashes grouped by month
            query = """
                SELECT 
                    FORMAT([CRASHDATE], 'yyyy-MM') AS CrashMonth,
                    COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
            """
            # Add WHERE clause if UNITTYPE is specified
            if unit_type:
                query += " WHERE [UNITTYPE] = :unit_type"
            query += " GROUP BY FORMAT([CRASHDATE], 'yyyy-MM') ORDER BY CrashMonth"

            result = connection.execute(text(query), {"unit_type": unit_type} if unit_type else {})

            # Format rows as dictionaries with proper keys
            crash_data = [{"month": row["CrashMonth"], "count": row["CrashCount"]} for row in result]

        return jsonify(crash_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
