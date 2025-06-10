from flask import Flask, jsonify, Response, send_file, request
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import datetime

app = Flask(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
raw_creds = os.environ["GOOGLE_CREDS_JSON"]
parsed_creds = json.loads(raw_creds)
parsed_creds["private_key"] = parsed_creds["private_key"].replace("\\n", "\n")

with open("creds.json", "w") as f:
    json.dump(parsed_creds, f)

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

spreadsheet = client.open("Inventory_Tracker")

@app.route("/inventory/<sheet_name>", methods=["GET"])
def get_inventory(sheet_name):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        return Response(json.dumps(data, indent=2), mimetype="application/json")
    except Exception as e:
        return jsonify({"error": f"Could not access sheet: {str(e)}"}), 400

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

@app.route("/location/<sheet_name>/<location_id>", methods=["GET"])
def get_by_location(sheet_name, location_id):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        results = [row for row in data if str(row.get("Location", "")).strip().lower() == location_id.strip().lower()]
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/sheets", methods=["GET"])
def list_sheets():
    try:
        sheet_titles = [ws.title for ws in spreadsheet.worksheets()]
        return jsonify(sheet_titles)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/sheetnames", methods=["GET"])
def list_sheetnames():
    return list_sheets()

@app.route("/inventory/add", methods=["POST"])
def add_inventory_item():
    try:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {os.environ['INVENTORY_WRITE_KEY']}":
            return jsonify({"error": "Unauthorized"}), 401

        data = request.json
        sheet_name = data.get("sheet_name")
        sheet = spreadsheet.worksheet(sheet_name)

        if sheet_name == "Integration_Log":
            headers = sheet.row_values(1)
            if not headers:
                headers = [
                    "Timestamp",
                    "Task Name",
                    "Description of Step",
                    "Outcome",
                    "Status",
                    "Script Link or Snippet",
                    "Notes / Next Steps"
                ]
                sheet.insert_row(headers, 1)

            new_keys = [key for key in data if key not in headers and key != "sheet_name"]
            if new_keys:
                headers.extend(new_keys)
                sheet.update('A1', [headers])

            row = [data.get(h, "") for h in headers]
        else:
            row = [
                data.get("Item", ""),
                data.get("Stock", ""),
                data.get("Location", ""),
                data.get("Arrival Date", ""),
                data.get("Date Accessed", "")
            ]

        sheet.append_row(row)

        log_sheet = spreadsheet.worksheet("Change_Log")
        log_sheet.append_row([
            "ADD",
            json.dumps(row),
            datetime.datetime.now().isoformat()
        ])

        return jsonify({"status": "Item added", "item": row}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/sheet/update_structure", methods=["POST"])
def update_sheet_structure():
    try:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {os.environ['INVENTORY_WRITE_KEY']}":
            return jsonify({"error": "Unauthorized"}), 401

        data = request.json
        sheet_name = data["sheet_name"]
        remove_columns = data.get("remove_columns", [])

        sheet = spreadsheet.worksheet(sheet_name)
        headers = sheet.row_values(1)
        all_values = sheet.get_all_values()

        # Create new headers
        new_headers = [h for h in headers if h not in remove_columns]
        new_sheet = [new_headers]

        # Rebuild the sheet rows with only the kept columns
        col_indices = [headers.index(h) for h in new_headers]
        for row in all_values[1:]:  # skip headers
            filtered_row = [row[i] if i < len(row) else "" for i in col_indices]
            new_sheet.append(filtered_row)

        # Clear and replace entire sheet
        sheet.clear()
        sheet.update('A1', new_sheet)

        return jsonify({"status": "Headers updated", "new_headers": new_headers}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/sheet/set_headers", methods=["POST"])
def set_headers():
    try:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {os.environ['INVENTORY_WRITE_KEY']}":
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        sheet_name = data.get("sheet_name")
        headers = data.get("headers")

        if not sheet_name or not headers:
            return jsonify({"error": "Missing sheet_name or headers"}), 400

        sheet = spreadsheet.worksheet(sheet_name)
        sheet.delete_row(1)
        sheet.insert_row(headers, index=1)

        return jsonify({"status": "Headers updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/.well-known/ai-plugin.json")
def plugin_manifest():
    return send_file("ai-plugin.json", mimetype="application/json")

@app.route("/openapi.yaml")
def openapi_spec():
    return send_file("openapi.yaml", mimetype="text/yaml")

if __name__ == "__main__":
    app.run(debug=True)
