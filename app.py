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

with open("creds.json", "w") as f:
    json.dump(parsed_creds, f)
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# ✅ Replaced single-sheet access with reference to the whole spreadsheet
spreadsheet = client.open("Inventory_Tracker")

# ✅ New endpoint to access any sheet dynamically
@app.route("/inventory/<sheet_name>", methods=["GET"])
def get_inventory(sheet_name):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        return Response(json.dumps(data, indent=2), mimetype="application/json")
    except Exception as e:
        return jsonify({"error": f"Could not access sheet: {str(e)}"}), 400

# GET one item (unchanged — still points to the first/default sheet, optional to keep or update later)
@app.route("/inventory/item/<item_name>", methods=["GET"])
def get_item(item_name):
    sheet = spreadsheet.sheet1
    data = sheet.get_all_records()
    for row in data:
        if row["Item"].lower() == item_name.lower():
            return jsonify(row)
    return jsonify({"error": "Item not found"}), 404

@app.route("/.well-known/ai-plugin.json")
def plugin_manifest():
    return send_file("ai-plugin.json", mimetype="application/json")

@app.route("/openapi.yaml")
def openapi_spec():
    return send_file("openapi.yaml", mimetype="text/yaml")

@app.route("/location/<location_id>", methods=["GET"])
def get_by_location(location_id):
    sheet = spreadsheet.sheet1
    data = sheet.get_all_records()
    matches = [
        row for row in data
        if row.get("Location", "").strip().lower() == location_id.strip().lower()
    ]
    if matches:
        return jsonify(matches)
    else:
        return jsonify({"error": "Location not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
