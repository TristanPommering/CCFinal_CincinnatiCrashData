from flask import Flask, render_template, jsonify
from sqlalchemy import create_engine
from sqlalchemy.sql import text

app = Flask(__name__)

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
            data = [{"label": row["VEHICLETYPE"], "value": row["CrashCount"]} for row in result]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Crashes by Gender
@app.route("/data/gender", methods=["GET"])
def crashes_by_gender():
    try:
        with engine.connect() as connection:
            query = """
                SELECT GENDER, COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                WHERE GENDER IS NOT NULL
                GROUP BY GENDER
                ORDER BY CrashCount DESC;
            """
            result = connection.execute(text(query))
            data = [{"label": row["GENDER"], "value": row["CrashCount"]} for row in result]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            data = [{"label": row["LightCondition"], "value": row["CrashCount"]} for row in result]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
