from flask import Flask, jsonify, Response, send_file
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
raw_creds = os.environ["GOOGLE_CREDS_JSON"]
parsed_creds = json.loads(raw_creds)

# Replace escaped newlines with real newlines in the private_key
parsed_creds["private_key"] = parsed_creds["private_key"].replace("\\n", "\n")

# Write credentials to file for gspread
with open("creds.json", "w") as f:
    json.dump(parsed_creds, f)

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# Reference the entire spreadsheet
spreadsheet = client.open("Inventory_Tracker")

# ✅ Get all inventory from a specified sheet
@app.route("/inventory/<sheet_name>", methods=["GET"])
def get_inventory(sheet_name):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        return Response(json.dumps(data, indent=2), mimetype="application/json")
    except Exception as e:
        return jsonify({"error": f"Could not access sheet: {str(e)}"}), 400

# ✅ Get a specific item by name from a specified sheet
@app.route("/inventory/item/<sheet_name>/<item_name>", methods=["GET"])
def get_inventory_item(sheet_name, item_name):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        for row in data:
            if row.get("Item", "").strip().lower() == item_name.strip().lower():
                return jsonify(row)
        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Could not access sheet: {str(e)}"}), 400

# ✅ Get items at a specific location in a specified sheet
@app.route("/location/<sheet_name>/<location_id>", methods=["GET"])
def get_by_location(sheet_name, location_id):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        results = [row for row in data if str(row.get("Location", "")).strip().lower() == location_id.strip().lower()]
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Plugin manifest and OpenAPI spec endpoints
@app.route("/.well-known/ai-plugin.json")
def plugin_manifest():
    return send_file("ai-plugin.json", mimetype="application/json")

@app.route("/openapi.yaml")
def openapi_spec():
    return send_file("openapi.yaml", mimetype="text/yaml")

if __name__ == "__main__":
    app.run(debug=True)
