import requests
import time
import xmltodict
import json
import os
import pandas as pd

BASE_URL = "http://127.0.0.1:8080"  # Use 127.0.0.1 for faster resolution

start_time = time.time()
# Run the XML parsing test
url = "http://127.0.0.1:8080/GetTransactions?user=QIAOSUN" 
response = requests.get(url)
# parsed = response.json()
# print_structure(t)
response.raise_for_status()
xml_text = response.text
data = xmltodict.parse(xml_text)

duration = time.time() - start_time
print(f"Saved transactions to (took {duration:.3f} seconds)")

start_time = time.time()
#print(parsed)
# json_string = json.dumps(parsed)
# size_in_bytes = len(json_string.encode('utf-8'))
# print(f"Size in memory: {size_in_bytes / 1024:.2f} KB")

# print(parsed['Response']['Content']['Trader'])
#print_structure(parsed['Response']['Content']['Trader']['Region'][0]['Transaction'])
#print(data['Response']['Content']['Trader']['Region'][0]['Transaction'][0])


# file_path = os.path.join(os.getcwd(), "transactions_from_xml.json")
# with open(file_path, "w", encoding="utf-8") as f:
#     json.dump(parsed, f, indent=2)  # or remove `indent=2` for compact version

# # Step 4: Print file size
# size_kb = os.path.getsize(file_path) / 1024
# print(f"Saved to: {file_path}")
# print(f"File size: {size_kb:.2f} KB")




orders = (
    data['Response']
        ['Content']
        ['Trader']
        ['Region'][0]
        ['Transaction']
)

# Step 3: Filter required fields only
filtered = []
for entry in orders:
    filtered.append({
        'Symbol': entry.get('@Symbol'),
        'Side': entry.get('@Side'),
        'OrderNumber': entry.get('@OrderNumber'),
        'Price': float(entry.get('@Price', 0)),
        'Shares': int(entry.get('@Shares', 0))
    })

duration = time.time() - start_time
print(f"DF transactions to (took {duration:.3f} seconds)")


# Step 4: Convert to DataFrame
df = pd.DataFrame(filtered)

print(f"Conversion to (took {duration:.3f} seconds)")


df['Shares'] = df['Shares'].astype(int)

df.loc[df['Side']!='B','Shares'] = df.loc[df['Side']!='B','Shares']*-1
print(df.head)


print(df.groupby('Symbol').sum()['Shares'])

