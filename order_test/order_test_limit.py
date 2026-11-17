import time
import requests

# Configuration
base_url = "http://tnv.ngrok.io/Basket=BB_TEST4,Order=*TSLA.NQ:1*,Limit=*TSLA.NQ:"
base_url2 = "http://tnv.ngrok.io/Basket=BB_TEST5,Order=*TSLA.NQ:1*,Limit=*TSLA.NQ:"
base_url3 = "http://tnv.ngrok.io/Basket=BB_TEST6,Order=*TSLA.NQ:1*,Limit=*TSLA.NQ:"
limit_price = 300
interval = 5  # seconds

print(f"Monitoring and sending to: {base_url}")
print("Press Ctrl+C to terminate.")

try:
    for i in range(40):
        # Construct the specific URL with the incremented price
        full_url = f"{base_url}{limit_price}*"
        full_url2 = f"{base_url}{limit_price+2}*"
        full_url3 = f"{base_url}{limit_price+3}*"
        try:
            # Sending the GET request
            # timeout=5 prevents the script from hanging forever if ngrok is slow
            response = requests.get(full_url, timeout=5)
            response = requests.get(full_url2, timeout=5)
            response = requests.get(full_url3, timeout=5)
            # Realistic status check: 200 means OK
            if response.status_code == 200:
                print(f"[SUCCESS] Price {limit_price} sent.")
            else:
                print(f"[FAILURE] Received status {response.status_code} for price {limit_price}")
        
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection failed: {e}")

        # Update for next iteration
        limit_price += 1
        time.sleep(interval)

except KeyboardInterrupt:
    print("\nExecution stopped by user.")