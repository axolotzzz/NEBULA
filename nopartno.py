from flask import Flask, request, render_template_string
import requests
import json
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

# Use a hardcoded token instead of fetching it every time
def get_token():
    return "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJBbmlzaDI1IiwidXNlck5hbWUiOiJBbmlzaDI1Iiwicm9sZXMiOltudWxsXSwiaWF0IjoxNzUxODgwMDY3LCJleHAiOjE3NTE5MDE2Njd9.KeT2ZtvoagZL5u3ArztFkdU1FEkh5BiBHeQe18pQ19FPUXXwZrwHpxUj4YVKg-oolcTASoXSEHRJhPLXZIEmng"

STATIC_PART_NUMBERS = ["141414", "5156", "P8979", "0001", "0002"]

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
  <script>
    function addPartRow() {
      const container = document.getElementById("parts");
      const wrapper = document.createElement("div");
      wrapper.className = "part-row";
      wrapper.innerHTML = `
        <hr>
        <h3>Part</h3>
        <label>Part Number: <input name="partNumber[]" list="parts" autocomplete="off" required></label>
        <label>Quantity: <input name="quantity[]" required></label>
      `;
      container.appendChild(wrapper);
    }
  </script>
  <datalist id="parts">
    {% for part in part_numbers %}
      <option value="{{ part }}">
    {% endfor %}
  </datalist>
</head>
<body>
  <h2>Submit Inbound Order</h2>
  <form method="post" action="https://d41100d81695.ngrok-free.app>
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

    return render_template_string(form_html, part_numbers=STATIC_PART_NUMBERS)

if __name__ == "__main__":
    app.run(debug=True)
