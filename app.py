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

with open("creds.json", "w") as f:
    json.dump(parsed_creds, f)
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# Open your sheet
sheet = client.open("Inventory_Tracker").sheet1  # Change name if different

# GET all inventory
@app.route("/inventory", methods=["GET"])
def get_inventory():
    data = sheet.get_all_records()
    pretty_json = json.dumps(data, indent=2)
    return Response(pretty_json, mimetype="application/json")

# GET one item
@app.route("/inventory/<item_name>", methods=["GET"])
def get_item(item_name):
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

if __name__ == "__main__":
    app.run(debug=True)

