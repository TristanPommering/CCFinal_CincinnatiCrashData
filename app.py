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
            # Base query to get crashes grouped by month (1-12)
            query = """
                SELECT 
                    MONTH([CRASHDATE]) AS CrashMonth, -- Numeric month
                    COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                WHERE (:unit_type IS NULL OR [UNITTYPE] = :unit_type) -- Optional filter
                GROUP BY MONTH([CRASHDATE])
                ORDER BY CrashMonth
            """

            result = connection.execute(
                text(query), {"unit_type": unit_type} if unit_type else {}
            )

            # Format rows as dictionaries with proper keys
            crash_data = [{"month": row["CrashMonth"], "count": row["CrashCount"]} for row in result]

        return jsonify(crash_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/vehicle-types", methods=["GET"])
def get_vehicle_types():
    # Fetch distinct UNITTYPE values
    try:
        with engine.connect() as connection:
            query = "SELECT DISTINCT [UNITTYPE] FROM [dbo].[CrashData] ORDER BY [UNITTYPE]"
            result = connection.execute(text(query))
            vehicle_types = [row["UNITTYPE"] for row in result]
        return jsonify(vehicle_types)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
