from flask import Flask, jsonify, request, send_file
import gspread
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

# Set up gspread using the Google service account
creds_json = os.environ.get("GOOGLE_CREDS_JSON")
if not creds_json:
    raise ValueError("GOOGLE_CREDS_JSON environment variable not set")

# Fix newline parsing in private_key
creds_dict = json.loads(creds_json)
if "private_key" in creds_dict:
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

gc = gspread.service_account_from_dict(creds_dict)
spreadsheet = gc.open("Inventory_Tracker")

# Retrieve all rows from a specified sheet (as dicts using first row as headers)
@app.route("/inventory/<sheet_name>", methods=["GET"])
def get_inventory(sheet_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        values = worksheet.get_all_values()
        headers = values[0] if values else []
        rows = values[1:] if len(values) > 1 else []

        records = [
            {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            for row in rows
        ]
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# View raw values (for debugging)
@app.route("/inventory/raw/<sheet_name>", methods=["GET"])
def get_raw_sheet(sheet_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        raw = worksheet.get_all_values()
        return jsonify(raw), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Retrieve one item by name
@app.route("/inventory/item/<sheet_name>/<item_name>")
def get_item(sheet_name, item_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        for row in records:
            if row.get("Item", "").lower() == item_name.lower():
                return jsonify(row), 200
        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Filter by location
@app.route("/location/<sheet_name>/<location_id>")
def get_by_location(sheet_name, location_id):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        result = [row for row in records if row.get("Location", "") == location_id]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Remove columns
@app.route("/sheet/update_structure", methods=["POST"])
def update_structure():
    data = request.get_json()
    sheet_name = data.get("sheet_name")
    remove_columns = data.get("remove_columns", [])

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        all_data = worksheet.get_all_values()
        if not all_data:
            return jsonify({"error": "Sheet is empty"}), 400

        header = all_data[0]
        new_header = [h for h in header if h not in remove_columns]
        new_data = []

        for row in all_data[1:]:
            new_row = [val for i, val in enumerate(row) if header[i] not in remove_columns]
            new_data.append(new_row)

        worksheet.clear()
        worksheet.append_row(new_header)
        for row in new_data:
            worksheet.append_row(row)

        return jsonify({"message": "Structure updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Set new headers
@app.route("/sheet/set_headers", methods=["POST"])
def set_headers():
    key = request.args.get("key")
    if key != os.environ.get("INVENTORY_WRITE_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    sheet_name = data.get("sheet_name")
    headers = data.get("headers")

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.delete_rows(1)
        worksheet.insert_row(headers, 1)
        return jsonify({"message": "Headers updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# List all sheets
@app.route("/sheet/list_all", methods=["GET"])
def list_all_sheets():
    try:
        sheet_titles = [ws.title for ws in spreadsheet.worksheets()]
        return jsonify({"sheets": sheet_titles}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve OpenAPI spec
@app.route("/openapi.yaml")
def openapi_spec():
    return send_file("openapi.yaml", mimetype="text/yaml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
