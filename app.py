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
    # Get VEHICLETYPE filter from the request (default: None)
    vehicle_type = request.args.get("vehicle_type", None)

    try:
        with engine.connect() as connection:
            # Base query to get crashes grouped by month
            query = """
                SELECT 
                    INTEGERMONTH AS CrashMonth,
                    COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                WHERE (:vehicle_type IS NULL OR VEHICLETYPE = :vehicle_type)
                GROUP BY INTEGERMONTH
                ORDER BY INTEGERMONTH;
            """

            # Execute the query with or without the filter
            params = {"vehicle_type": vehicle_type} if vehicle_type else {}
            result = connection.execute(text(query), params)

            # Format rows as dictionaries with proper keys
            crash_data = [{"month": row["CrashMonth"], "count": row["CrashCount"]} for row in result]

        return jsonify(crash_data)
    except Exception as e:
        app.logger.error(f"Error fetching crash data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/vehicle-types", methods=["GET"])
def get_vehicle_types():
    try:
        with engine.connect() as connection:
            query = "SELECT DISTINCT [VEHICLETYPE] FROM [dbo].[CrashData] ORDER BY [VEHICLETYPE];"
            result = connection.execute(text(query))
            vehicle_types = [row["VEHICLETYPE"] for row in result]
        return jsonify(vehicle_types)
    except Exception as e:
        app.logger.error(f"Error fetching vehicle types: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
