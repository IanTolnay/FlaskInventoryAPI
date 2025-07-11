from flask import Flask, jsonify, request, send_file
import gspread
from flask_cors import CORS
import os
import json
from functools import wraps

app = Flask(__name__)
CORS(app)

# Set up gspread using the Google service account from a secret file
with open("creds.json", "r") as f:
    creds_dict = json.load(f)

gc = gspread.service_account_from_dict(creds_dict)
spreadsheet = gc.open("Inventory_Tracker")

# Authorization decorator for write endpoints
def require_write_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.args.get("key")
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            key = auth_header.split(" ")[1]
        if key != os.environ.get("INVENTORY_WRITE_KEY"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route("/inventory/<sheet_name>", methods=["GET"])
def get_inventory(sheet_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        headers = worksheet.row_values(1)
        all_values = worksheet.get_all_values()
        rows = all_values[1:] if len(all_values) > 1 else []
        records = [
            {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            for row in rows
        ] if rows else []
        return jsonify(records if records else [{"headers_only": headers}]), 200
    except Exception as e:
        print(f"Error in get_inventory: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/inventory/headers/<sheet_name>", methods=["GET"])
def get_headers(sheet_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        headers = worksheet.row_values(1)
        return jsonify({"headers": headers}), 200
    except Exception as e:
        print(f"Error in get_headers: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/inventory/raw/<sheet_name>", methods=["GET"])
def get_raw_sheet(sheet_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        max_rows = worksheet.row_count
        raw = worksheet.get(f"A1:Z{max_rows}")
        return jsonify(raw), 200
    except Exception as e:
        print(f"Error in get_raw_sheet: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/inventory/structured/<sheet_name>", methods=["GET"])
def get_structured_sheet(sheet_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        values = worksheet.get_all_values()
        headers = values[0] if values else []
        records = values[1:] if len(values) > 1 else []
        return jsonify({
            "headers": headers,
            "rows": records
        }), 200
    except Exception as e:
        print(f"Error in get_structured_sheet: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/inventory/item/<sheet_name>/<item_name>")
def get_item(sheet_name, item_name):
    try:
        key_column = request.args.get("key_column")
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        if not records:
            return jsonify({"error": "No data in sheet."}), 404

        match = None
        if key_column:
            if key_column not in records[0]:
                return jsonify({"error": f"Column '{key_column}' not found."}), 400
            match = next((row for row in records if str(row.get(key_column, "")).lower() == item_name.lower()), None)
        elif "Item" in records[0]:
            match = next((row for row in records if str(row.get("Item", "")).lower() == item_name.lower()), None)
        else:
            first_col = list(records[0].keys())[0]
            match = next((row for row in records if str(row.get(first_col, "")).lower() == item_name.lower()), None)

        if match:
            return jsonify(match), 200
        else:
            return jsonify({"error": "Item not found"}), 404

    except Exception as e:
        print(f"Error in get_item: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/location/<sheet_name>/<location_id>")
def get_by_location(sheet_name, location_id):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        result = [row for row in records if row.get("Location", "") == location_id]
        return jsonify(result), 200
    except Exception as e:
        print(f"Error in get_by_location: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/sheet/update_structure", methods=["POST"])
@require_write_key
def update_structure():
    data = request.get_json()
    sheet_name = data.get("sheet_name")
    remove_columns = data.get("remove_columns", [])
    print(f"[LOG] Received request to update structure: sheet_name='{sheet_name}', remove_columns={remove_columns}")
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
        print(f"Error in update_structure: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/sheet/set_headers", methods=["POST"])
@require_write_key
def set_headers():
    data = request.get_json()
    sheet_name = data.get("sheet_name")
    headers = data.get("headers")
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.delete_rows(1)
        worksheet.insert_row(headers, 1)
        return jsonify({"message": "Headers updated successfully"}), 200
    except Exception as e:
        print(f"Error in set_headers: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/sheet/list_all", methods=["GET"])
def list_all_sheets():
    try:
        sheet_titles = [ws.title for ws in spreadsheet.worksheets()]
        return jsonify({"sheets": sheet_titles}), 200
    except Exception as e:
        print(f"Error in list_all_sheets: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/integration/log", methods=["POST"])
@require_write_key
def log_integration():
    try:
        data = request.get_json()
        worksheet = spreadsheet.worksheet("Integration_Log")
        headers = worksheet.row_values(1)
        new_keys = [key for key in data.keys() if key not in headers]
        if new_keys:
            worksheet.insert_row(headers + new_keys, 1)
            headers += new_keys
        row = [data.get(header, "") for header in headers]
        worksheet.append_row(row)
        return jsonify({"message": "Log added successfully"}), 200
    except Exception as e:
        print(f"Error in log_integration: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/openapi.yaml")
def openapi_spec():
    return send_file("openapi.yaml", mimetype="text/yaml")

@app.route("/sheet/create", methods=["POST"])
@require_write_key
def create_sheet():
    try:
        data = request.get_json()
        sheet_name = data.get("sheet_name")
        headers = data.get("headers", [])
        if not sheet_name:
            return jsonify({"error": "Missing 'sheet_name'"}), 400
        existing_titles = [ws.title for ws in spreadsheet.worksheets()]
        if sheet_name in existing_titles:
            return jsonify({"message": f"Sheet '{sheet_name}' already exists"}), 200
        new_worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")
        if headers:
            new_worksheet.append_row(headers)
        return jsonify({"message": f"Sheet '{sheet_name}' created successfully"}), 200
    except Exception as e:
        print(f"Error in create_sheet: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/sheet/rename", methods=["POST"])
@require_write_key
def rename_sheet():
    data = request.get_json()
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    if not old_name or not new_name:
        return jsonify({"error": "Both 'old_name' and 'new_name' are required"}), 400
    try:
        worksheet = spreadsheet.worksheet(old_name)
        worksheet.update_title(new_name)
        return jsonify({"message": f"Renamed {old_name} to {new_name}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/sheet/delete", methods=["POST"])
@require_write_key
def delete_sheet():
    data = request.get_json()
    sheet_name = data.get("sheet_name")
    if not sheet_name:
        return jsonify({"error": "'sheet_name' is required"}), 400
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        spreadsheet.del_worksheet(worksheet)
        return jsonify({"message": f"Sheet '{sheet_name}' deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/inventory/add", methods=["POST"])
@require_write_key
def add_inventory_item():
    try:
        data = request.get_json()
        sheet_name = data.get("sheet_name")
        item = data.get("item", {})
        if not sheet_name or not item:
            return jsonify({"error": "Missing sheet_name or item"}), 400
        worksheet = spreadsheet.worksheet(sheet_name)
        headers = worksheet.row_values(1)
        new_keys = [key for key in item.keys() if key not in headers]
        if new_keys:
            headers += new_keys
            worksheet.delete_rows(1)
            worksheet.insert_row(headers, 1)
        row = [item.get(header, "") for header in headers]
        worksheet.append_row(row)
        return jsonify({"message": "Item added successfully"}), 200
    except Exception as e:
        print(f"Error in add_inventory_item: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
