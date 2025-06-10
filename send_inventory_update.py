import requests
import json

# Your secure API key from Render
API_KEY = "T360_MASTER_KEY"  # Replace with your actual key
API_URL = "https://flask-inventory-api.onrender.com/inventory/add"

# Sample payload from GPT (replace this with your real data)
payload = {
    "action": "add",
    "sheet_name": "Sheet1",
    "Item": "Switch",
    "Stock": "5",
    "Location": "3B",
    "Arrival Date": "2025-05-22",
    "Date Accessed": "2025-05-22"
}

# Remove the "action" field before sending
payload.pop("action", None)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

print("Status Code:", response.status_code)
print("Response:", response.json())
