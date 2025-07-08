from flask import Flask, request, render_template_string
import requests
import json
import pandas as pd
import os

app = Flask(__name__)

def get_token():
    auth_url = "https://uatvisibility.tvsscs.com/token/authenticate"
    credentials = {
        "userName": "Anish25",
        "password": "Anish@25"
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(auth_url, json=credentials, headers=headers)
        response.raise_for_status()
        return response.json().get("token")
    except Exception as e:
        print("Auth error:", e)
        return None




def load_part_numbers():
    try:
        print("📂 Current files:", os.listdir())
        df = pd.read_csv("PartExportData.csv")
        return df["partNumber"].dropna().astype(str).tolist()
    except Exception as e:
        print("⚠️ CSV load failed:", e)
        return ["141414", "5156", "P8979"]


form_html = """
<!DOCTYPE html>
<html>
<head>
  <title>Submit Inbound Order</title>
  <style>
    table, th, td { border: 1px solid black; border-collapse: collapse; padding: 8px; }
    th { background-color: #f2f2f2; }
    .part-row { margin-bottom: 10px; }
  </style>

  <datalist id="parts">
    {% for part in part_numbers %}
      <option value="{{ part }}">
    {% endfor %}
  </datalist>
</head>
<body>
  <h2>Submit Inbound Order</h2>
  <form method="post">
    Account Master ID: <input name="accountMasterId" required><br><br>
    Comment: <input name="comment"><br><br>
    Customer Reference: <input name="customerReference" required><br><br>
    Invoice Number: <input name="invoiceNumber"><br><br>

    <div id="parts">
      <div class="part-row">
        <h3>Part</h3>
        Part Number: <input name="partNumber[]" list="parts" autocomplete="off" required>
        Quantity: <input name="quantity[]" required>
      </div>
    </div>

    <button type="button" onclick="addPartRow()">+ Add Another Part</button><br><br>
    <button type="submit">Submit Order</button>
  </form>

  <script>
  function addPartRow() {
    const partDiv = document.createElement("div");
    partDiv.classList.add("part-row");

    // Create part number input
    const partNumberInput = document.createElement("input");
    partNumberInput.name = "partNumber[]";
    partNumberInput.setAttribute("list", "parts");
    partNumberInput.setAttribute("autocomplete", "off");
    partNumberInput.required = true;

    // Create quantity input
    const quantityInput = document.createElement("input");
    quantityInput.name = "quantity[]";
    quantityInput.required = true;

    partDiv.innerHTML = "<hr><h3>Part</h3>Part Number: ";
    partDiv.appendChild(partNumberInput);
    partDiv.innerHTML += " Quantity: ";
    partDiv.appendChild(quantityInput);

    document.getElementById("parts").appendChild(partDiv);
  }
</script>
</body>
</html>
"""

result_template = """
<!DOCTYPE html>
<html>
<head>
  <title>Order Response</title>
  <style>
    table, th, td { border: 1px solid black; border-collapse: collapse; padding: 8px; }
    th { background-color: #f2f2f2; }
  </style>
</head>
<body>
  <h2>Order Submission Result</h2>
  <p><b>Status:</b> {{ status }}</p>
  <p><b>Order ID:</b> {{ order_id }}</p>
  <p><b>Message:</b> {{ message }}</p>

  {% if replen %}
    <h3>Replen Items:</h3>
    <table>
      <tr>
        <th>Part Number</th>
        <th>Quantity</th>
        <th>Destination</th>
      </tr>
      {% for item in replen %}
      <tr>
        <td>{{ item.partNumber }}</td>
        <td>{{ item.quantity }}</td>
        <td>{{ item.destination }}</td>
      </tr>
      {% endfor %}
    </table>
  {% endif %}
  <br><a href="/">Back to Form</a>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def inbound():
    if request.method == "POST":
        token = get_token()
        if not token:
            return "Authentication failed. Cannot proceed."

        account_id = request.form['accountMasterId']
        comment = request.form.get('comment', '')
        customer_ref = request.form['customerReference']
        invoice_num = request.form.get('invoiceNumber', '')

        part_numbers = request.form.getlist('partNumber[]')
        quantities = request.form.getlist('quantity[]')

        replen_items = []
        for part, qty in zip(part_numbers, quantities):
            if part and qty:
                replen_items.append({
                    "destination": "IN01071",
                    "partNumber": part,
                    "stockTypeCode": "GOOD",
                    "customerReference": customer_ref,
                    "quantity": qty,
                    "invoiceNumber": invoice_num,
                    "serialNumber": "",
                    "batchNumber": "",
                    "manufacturingDate": "",
                    "expiryDate": "",
                    "reference1": "",
                    "reference2": "DEMO",
                    "reference3": "DEMO",
                    "returnReason": "",
                    "partRef": "P8979",
                    "pallet": "pallet",
                    "lineNumber": "12"
                })

        payload = {
            "orderTypesMasterId": "OTYM-1",
            "siteMasterId": "IN01071",
            "sendMail": True,
            "isSave": True,
            "partialSave": True,
            "accountMasterId": account_id,
            "actorType": "AM001",
            "vehicleAssigned": False,
            "isGrnReady": False,
            "comment": comment,
            "replen": replen_items
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "AppId": "008",
            "timezone": "Asia/Calcutta",
            "accountMasterId": account_id
        }

        response = requests.post(
            "https://uatvisibility.tvsscs.com/api/visibility/api/import/importOrder",
            headers=headers,
            data={"paramWarehouse": json.dumps(payload)}
        )

        try:
            res_json = response.json()
            order_id = (
                res_json.get("orderId")
                or (res_json.get("orderIdLst") or [None])[0]
                or (res_json.get("sWhInbounds") or [{}])[0].get("orderId")
                or "Not returned"
            )
            return render_template_string(
                result_template,
                status=res_json.get("status", "Unknown"),
                order_id=order_id,
                message=res_json.get("errorMessages") or res_json.get("successMessages") or "No message",
                replen=replen_items
            )
        except Exception:
            return f"<pre>{response.text}</pre><br><a href='/'>Back</a>"

    part_list = load_part_numbers()
    return render_template_string(form_html, part_numbers=part_list)

if __name__ == "__main__":
    app.run(debug=True)
