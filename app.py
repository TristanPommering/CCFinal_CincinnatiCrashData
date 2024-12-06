from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Database connection
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

# Endpoint: Crashes by Vehicle Type
@app.route("/data/vehicle-type", methods=["GET"])
def crashes_by_vehicle_type():
    try:
        with engine.connect() as connection:
            query = """
                SELECT VEHICLETYPE, COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                WHERE VEHICLETYPE IS NOT NULL
                GROUP BY VEHICLETYPE
                ORDER BY CrashCount DESC;
            """
            result = connection.execute(text(query))
            data = [{"label": row[0], "value": int(row[1])} for row in result]
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error fetching vehicle type data: {e}")
        return jsonify({"error": "Failed to fetch data from the database."}), 500

# Endpoint: Crashes by Gender
@app.route("/data/gender", methods=["GET"])
def crashes_by_gender():
    try:
        with engine.connect() as connection:
            query = """
                SELECT 
                    CASE 
                        WHEN GENDER IN ('F - FEMALE', 'FEMALE') THEN 'Female'
                        WHEN GENDER IN ('M - MALE', 'MALE') THEN 'Male'
                        ELSE 'Unknown'
                    END AS CleanedGender,
                    COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                WHERE GENDER IS NOT NULL
                GROUP BY 
                    CASE 
                        WHEN GENDER IN ('F - FEMALE', 'FEMALE') THEN 'Female'
                        WHEN GENDER IN ('M - MALE', 'MALE') THEN 'Male'
                        ELSE 'Unknown'
                    END
                ORDER BY CrashCount DESC;
            """
            result = connection.execute(text(query))
            data = [{"label": row[0], "value": int(row[1])} for row in result]
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error fetching gender data: {e}")
        return jsonify({"error": "Failed to fetch data from the database."}), 500


# Endpoint: Crashes by Light Conditions (Day vs Night)
@app.route("/data/light-conditions", methods=["GET"])
def crashes_by_light_conditions():
    try:
        with engine.connect() as connection:
            query = """
                SELECT 
                    CASE 
                        WHEN LIGHTCONDITIONSPRIMARY IN ('1 - DAYLIGHT') THEN 'Day'
                        ELSE 'Night'
                    END AS LightCondition,
                    COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                WHERE LIGHTCONDITIONSPRIMARY IS NOT NULL
                GROUP BY 
                    CASE 
                        WHEN LIGHTCONDITIONSPRIMARY IN ('1 - DAYLIGHT') THEN 'Day'
                        ELSE 'Night'
                    END;
            """
            result = connection.execute(text(query))
            data = [{"label": row[0], "value": int(row[1])} for row in result]
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error fetching light condition data: {e}")
        return jsonify({"error": "Failed to fetch data from the database."}), 500
    
@app.route("/data/crashes-by-month", methods=["GET"])
def crashes_by_month():
    try:
        vehicle_type = request.args.get("vehicle_type", None)
        query = """
            SELECT INTEGERMONTH, COUNT(*) AS CrashCount
            FROM [dbo].[CrashData]
            WHERE (:vehicle_type IS NULL OR VEHICLETYPE = :vehicle_type)
            GROUP BY INTEGERMONTH
            ORDER BY INTEGERMONTH;
        """
        with engine.connect() as connection:
            result = connection.execute(text(query), {"vehicle_type": vehicle_type})
            data = [{"month": row[0], "count": int(row[1])} for row in result]
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error fetching crashes by month: {e}")
        return jsonify({"error": "Failed to fetch data from the database."}), 500
    
    

if __name__ == "__main__":
    app.run(debug=True)
