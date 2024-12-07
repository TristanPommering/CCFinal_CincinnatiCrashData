from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
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
    
# Endpoint: Predict crashes for 2025
@app.route("/data/predictions", methods=["GET"])
def predict_crashes():
    try:
        with engine.connect() as connection:
            query = """
                SELECT YEAR, COUNT(*) AS TotalCrashes
                FROM [dbo].[CrashData]
                GROUP BY YEAR
                ORDER BY YEAR;
            """
            result = connection.execute(text(query))
            data = [{"year": row[0], "crashes": int(row[1])} for row in result]

        # Convert to DataFrame for modeling
        df = pd.DataFrame(data)
        X = df["year"].values.reshape(-1, 1)  # Years as features
        y = df["crashes"].values  # Crash counts as targets

        # Train a simple linear regression model
        model = LinearRegression()
        model.fit(X, y)

        # Predict for 2025
        future_year = np.array([[2025]])
        prediction = model.predict(future_year)

        # Add prediction to the data
        data.append({"year": 2025, "crashes": int(prediction[0])})

        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error in prediction: {e}")
        return jsonify({"error": "Failed to generate predictions."}), 500    

def columns_exist():
    try:
        with engine.connect() as connection:
            # Add INTEGERMONTH column if not exists
            connection.execute("""
                IF NOT EXISTS (
                    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'CrashData' AND COLUMN_NAME = 'INTEGERMONTH'
                )
                ALTER TABLE [dbo].[CrashData] ADD INTEGERMONTH INT;
            """)
            # Add VEHICLETYPE column if not exists
            connection.execute("""
                IF NOT EXISTS (
                    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'CrashData' AND COLUMN_NAME = 'VEHICLETYPE'
                )
                ALTER TABLE [dbo].[CrashData] ADD VEHICLETYPE NVARCHAR(50);
            """)
    except Exception as e:
        app.logger.error(f"Error ensuring columns exist: {e}")
        raise e

# Function to derive INTEGERMONTH and VEHICLETYPE
def process_data(df):
    # Handle missing or mixed data types
    df['AGE'] = pd.to_numeric(df['AGE'], errors='coerce')  # Convert AGE to numeric, set invalid values to NaN
    df['ZIP'] = pd.to_numeric(df['ZIP'], errors='coerce')  # Convert ZIP to numeric

    # Add INTEGERMONTH column
    if 'INTEGERMONTH' not in df.columns:
        df['INTEGERMONTH'] = pd.to_datetime(df['CRASHDATE'], errors='coerce').dt.month
    
    # Add VEHICLETYPE column
    if 'VEHICLETYPE' not in df.columns:
        df['VEHICLETYPE'] = df['UNITTYPE'].map({
            '01 - PASSENGER CAR': 'Passenger Vehicle',
            '02 - PASSENGER VAN (MINIVAN)': 'Passenger Vehicle',
            '03 - SPORT UTILITY VEHICLE': 'SUV',
            '04 - PICK UP': 'Truck',
            '05 - CARGO VAN': 'Commercial Vehicles',
            '06 - VAN (9-15 SEATS)': 'Commercial Vehicles',
            '07 - PICKUP': 'Truck',
            '07 - MOTORCYCLE 2 WHEELED': 'Motorcycle',
            '08 - MOTORCYCLE 3 WHEELED': 'Motorcycle',
            '09 - AUTOCYCLE': 'Motorcycle',
            '10 - MOPED OR MOTORIZED BICYCLE': 'Motorcycle',
            '26 - BICYCLE': 'Bicycle',
            '15 - SEMI-TRACTOR': 'Commercial Vehicles',
            '16 - FARM EQUIPMENT': 'Commercial Vehicles',
            '19 - BUS (16+ PASSENGERS)': 'Commercial Vehicles',
            '21 - HEAVY EQUIPMENT': 'Commercial Vehicles',
            '11 - ALL TERRAIN VEHICLE (ATV/UTV)': 'Other',
            '12 - GOLF CART': 'Other',
            '17 - MOTORHOME': 'Other',
            '20 - OTHER VEHICLE': 'Other',
            '23 - PEDESTRIAN/SKATER': 'Other',
            '24 - WHEELCHAIR (ANY TYPE)': 'Other',
            '25 - OTHER NON-MOTORIST': 'Other',
            '27 - TRAIN': 'Other',
            '99 - UNKNOWN OR HIT/SKIP': 'Other'
        }).fillna('Other')

    return df


# Endpoint for data loading
@app.route("/upload", methods=["POST"])
def upload_data():
    columns_exist()  # Ensure required columns exist
    try:
        # Check if a file is uploaded
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded."}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "Invalid file type. Please upload a CSV file."}), 400
        
        # Read the CSV file into a DataFrame
        try:
            df = pd.read_csv(file)
        except Exception as e:
            app.logger.error(f"Error reading CSV file: {e}")
            return jsonify({"error": "Failed to read the CSV file. Ensure it is correctly formatted."}), 400

        # Process the data
        try:
            df = process_data(df)
        except Exception as e:
            app.logger.error(f"Error processing data: {e}")
            return jsonify({"error": "Failed to process the data."}), 500

        # Insert the data into the database
        try:
            df.to_sql('CrashData', con=engine, if_exists='append', index=False)
        except Exception as e:
            app.logger.error(f"Error inserting data into the database: {e}")
            return jsonify({"error": "Failed to insert data into the database."}), 500

        return jsonify({"message": "Data uploaded and processed successfully."}), 200
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route("/get_filtered_data", methods=["POST"])
def get_filtered_data():
    try:
        # Parse the incoming JSON request
        request_data = request.get_json()
        selected_vehicle_types = request_data.get("vehicleTypes", [])
        
        # Build a query to filter data
        query = """
            SELECT VEHICLETYPE, COUNT(*) AS CrashCount
            FROM [dbo].[CrashData]
            WHERE VEHICLETYPE IS NOT NULL
            AND VEHICLETYPE IN :vehicle_types
            GROUP BY VEHICLETYPE
            ORDER BY CrashCount DESC;
        """
        
        # Execute the query with filtered vehicle types
        with engine.connect() as connection:
            result = connection.execute(text(query), {"vehicle_types": tuple(selected_vehicle_types)})
            data = [{"label": row[0], "value": int(row[1])} for row in result]
        
        return jsonify({"labels": [item["label"] for item in data], "data": [item["value"] for item in data]})
    except Exception as e:
        app.logger.error(f"Error fetching filtered data: {e}")
        return jsonify({"error": "Failed to fetch filtered data."}), 500

@app.route("/data/stats", methods=["GET"])
def get_crash_statistics():
    try:
        with engine.connect() as connection:
            # Total crashes
            total_crashes_query = "SELECT COUNT(*) FROM [dbo].[CrashData];"
            total_crashes = connection.execute(text(total_crashes_query)).scalar()
            
            # Average crashes per day
            avg_crashes_query = """
                SELECT AVG(CrashCount) FROM (
                    SELECT CAST(CRASHDATE AS DATE) AS CrashDay, COUNT(*) AS CrashCount
                    FROM [dbo].[CrashData]
                    GROUP BY CAST(CRASHDATE AS DATE)
                ) AS DailyCrashes;
            """
            avg_crashes = connection.execute(text(avg_crashes_query)).scalar()

            # Most common vehicle type
            common_vehicle_query = """
                SELECT TOP 1 VEHICLETYPE, COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                WHERE VEHICLETYPE IS NOT NULL
                GROUP BY VEHICLETYPE
                ORDER BY CrashCount DESC;
            """
            common_vehicle = connection.execute(text(common_vehicle_query)).fetchone()

            # Peak crash month
            peak_month_query = """
                SELECT TOP 1 INTEGERMONTH, COUNT(*) AS CrashCount
                FROM [dbo].[CrashData]
                GROUP BY INTEGERMONTH
                ORDER BY CrashCount DESC;
            """
            peak_month = connection.execute(text(peak_month_query)).fetchone()

        stats = {
            "total_crashes": total_crashes,
            "avg_crashes_per_day": round(avg_crashes, 2),
            "most_common_vehicle": common_vehicle[0] if common_vehicle else "Unknown",
            "peak_month": peak_month[0] if peak_month else "Unknown"
        }
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"Error fetching statistics: {e}")
        return jsonify({"error": "Failed to fetch statistics."}), 500
    
# Crash severity prediction endpoint
@app.route("/data/predict-severity", methods=["POST"])
def predict_crash_severity():
    try:
        # Query crash data
        with engine.connect() as connection:
            query = """
                SELECT 
                    CRASHSEVERITYID, INTEGERMONTH, VEHICLETYPE, LIGHTCONDITIONSPRIMARY,
                    ROADCONDITIONSPRIMARY, WEATHER
                FROM [dbo].[CrashData]
                WHERE CRASHSEVERITYID IS NOT NULL;
            """
            result = connection.execute(text(query))
            data = pd.DataFrame(result.fetchall(), columns=result.keys())

        # Preprocess data
        features = ['INTEGERMONTH', 'VEHICLETYPE', 'LIGHTCONDITIONSPRIMARY', 
                    'ROADCONDITIONSPRIMARY', 'WEATHER']
        target = 'CRASHSEVERITYID'

        # Encode categorical variables
        data = pd.get_dummies(data, columns=features, drop_first=True)
        
        X = data.drop(columns=[target])
        y = data[target]

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train the model
        model = RandomForestClassifier(random_state=42)
        model.fit(X_train, y_train)

        # Process input data from request
        input_data = request.get_json()
        input_df = pd.DataFrame([input_data])
        input_df = pd.get_dummies(input_df)
        input_df = input_df.reindex(columns=X.columns, fill_value=0)

        # Predict severity
        predicted_severity = int(model.predict(input_df)[0])

        return jsonify({
            "predicted_severity": predicted_severity,
            "message": "Severity prediction completed successfully."
        })
    except Exception as e:
        app.logger.error(f"Error in severity prediction: {e}")
        return jsonify({"error": "Failed to predict crash severity."}), 500


if __name__ == "__main__":
    app.run(debug=True)