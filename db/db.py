import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime
import json
import time 
# ====================================================================================
# !!! CRITICAL SECURITY WARNING !!!
# The following dictionary contains your actual Firebase project's service account key.
# Embedding this directly in your Python file is EXTREMELY INSECURE.
# If this file is ever compromised (e.g., uploaded to a public repository, accessed
# by unauthorized individuals), your Firebase project could be fully controlled by others.
#
# FOR PRODUCTION OR ANY SENSITIVE USE:
# 1. Store this JSON content in a separate file (e.g., `serviceAccountKey.json`).
# 2. NEVER commit that file to version control.
# 3. Reference it via its path: `credentials.Certificate('path/to/serviceAccountKey.json')`.
# 4. Or, even better for Google Cloud deployments, remove explicit credential
#    initialization and let the SDK handle default credentials.
# ====================================================================================

# Your Firebase service account key content
service_account_json_content = {
  "type": "service_account",
  "project_id": "trading-site-ticketing",
  "private_key_id": "34438bf8c5be2fc8f951f945f201ba25129bc335",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDI4k2Yz1OGNpAU\nRTs0ZjuRQG2PEPbDz7g6JaRtKRpRLz+mKE48Z3tG26PPVTDRpx42OsBWpIQFoI8H\nuLlfvob7QGWO4NGV7j1lcWEugT4EGN9zJnK00EnFWVkdJEeV/HKAlurT+GDFQkxG\nDXBJWN8eUctxOWv6wzwAleslfcX1Rf7ED+f5dGyFKyItBrA+52XhQc2osGdK0ZDZ\naVWr/wI3eIbx/y94IQ8hAfhW7ZQ3KOxJ4k7OQi4AJVIuV2okP2YRScXJVHDPXdVI\ndqc025Vqo9g8x9XxERe7blYumTvEwc1K2RxuoqnXYuuaHA/ECtnhcsdHjgfJUjEv\nA2cV2eQLAgMBAAECggEAFE6UK4th1SJ05CeveXeQM/nAWYMMfvTjmbUubv6Fs4lE\nNObEKeUIGDyhzZa+DaOIMVE1Gk0dL3hwnQY2bxBSktmKqqvdY/umZzfT7CCShVWC\nWSCc3dxkaLfEg2akeewAIzGeYXktRyORlE9Nd4ytWWJJX5O/b6UGzsRY9fxF46pW\nkLLNuEn3Kd1hJzySaQhUrAFXsfVLFT6nlHVDpcl1wDNR8pKFwxq576tpjOS3yM/S\nXH+5gJHGExQcZPDHcBxTPcBG4cASMxiQM4VWmqA6cEDTfB5ACM9PAFpbZRjul1LH\n5m4Oc65+gXgJkpvnXta0wGtoCrz91Ph+a2uqCqVCkQKBgQD/KI0xMgGfVK/z5PwU\n+G4ohkQ11ozf5Eq8o3/sSHY5u/Pj4yyD2x6MaYiHTVxRQ5SrOQjFS40B/RlrvLZj\nHe3FYSExZFsC//E0Qw5QywHwncilEl+7oi52YPW+mlcwqtLYerYflEN911sGXaP/\n4HnHTanI3DgnsdLXEqmnZ/paiQKBgQDJi+x/joqqHATSNqnSvbs2T0ga/0XDgYIy\n4MB8ecmkNhOa1NeuS0Oet2waCyQwYhIGjNjXcGtrRhUUHbtJ/qNrDP55f7dQtOzo\nRdc73j6wVd5qz8OPsuBRsAxUDgsbb9GyL9p2UDr/Bdg/tatDSsZzy2JYGcMN4ijb\ncnqxLTlU8wKBgAhI+MywIv1Zcp0owkasCmemdHCLFufuMb8OUAkMEUqun6y2o6tk\nYgmNI7HBAU5iM2Gb6Hz/hwSZg0nMRt/RCPdvv/Qqngnq5Zoc00osTVPSy8EQZ6tg\nCMIvQ8t8l3gtE8uTsHY2Cjr70yjRwZF9aHbgPrMW83vWelIheQDGj4qBAoGACrFe\nwcG5P58u7kwyJFkmlpIMPEpw1BeJ5dMgwzne5dRso9lI/BlIJCKNHLCcoeiCFlDg\nrEVtnYphUejl594Xo3VUBvQssJ54tzYFXkrDPq2/mCEfuf7+gbb6YHdCRZlgIbkC\nOSa2ipMvzul/hZlw//G5bP0o6RKnokTnl4DTutsCgYEAoIHFHz42/vwkTzQ4d3kN\n2FZBnb7oegnU5ebQ6SvRpuLjO07HZF0ZfCGFv70i/PiRLNe3WHIF99sDPRhbZpsT\ngp6Zd5UAy2gMbTGNNxLE9lrm7LjSK9mvjQZXxS43eRUiK2ByUEBY+3a9VSwo5qIo\nAs/9D4FNM8dJU/Wq1xR4qn0=\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@trading-site-ticketing.iam.gserviceaccount.com",
  "client_id": "111404885912050248197",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40trading-site-ticketing.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}


# Initialize Firebase Admin SDK using the embedded JSON content
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(service_account_json_content)
    firebase_admin.initialize_app(cred)

# Get a reference to your Firestore database (the 'default' one)
db = firestore.client(database_id="algorecords")

# --- Example 'algo' document fields ---
# Please ensure these field names and types exactly match your existing structure
# in the 'algo' collection for consistency.
algo_data = {
    "account": "ALG-MOM-001",
    "checkbox": "Momentum Scalper",
    "env": "active",
    "wfw":"fjck0",

}
# ----------------------------------------------------------------------------------

# Add the new document to the "algo" collection
# Firestore will automatically generate a unique ID for this new document.
# If you wanted to use "algoId" as the document ID, you would use:
# db.collection("algo").document(algo_data["algoId"]).set(algo_data)

NUM_WRITES = 5

print(f"Starting {NUM_WRITES} sequential writes to 'algorecords/TMS'...")
start_time = time.time() # Record the start time

for i in range(NUM_WRITES):
    # Example 'algo' document fields
    # Adding a unique timestamp to differentiate each document
    algo_data = {
        "account": "ALG-MOM-001",
        "checkbox": "Momentum Scalper",
        "env": "active",
        "wfw": f"fjck0_run_{i}", # Make each 'wfw' field unique
        "created_at": firestore.SERVER_TIMESTAMP # Use server timestamp for creation
    }

    try:
        # Add the new document to the "TMS" collection
        doc_ref = db.collection("TEST").add(algo_data)
        print(f"  Write {i+1}/{NUM_WRITES}: Successfully added document with ID: {doc_ref[1].id}")
        # print(f"    Data written: {json.dumps(algo_data, indent=2, default=str)}") # Uncomment to see full data for each write

    except Exception as e:
        print(f"  Write {i+1}/{NUM_WRITES}: An error occurred while writing to Firestore: {e}")
        break # Stop if an error occurs

end_time = time.time() # Record the end time
total_duration = end_time - start_time
average_duration_per_write = total_duration / NUM_WRITES

print(f"\n--- Write Performance Summary ---")
print(f"Total {NUM_WRITES} writes took: {total_duration:.4f} seconds")
print(f"Average time per write: {average_duration_per_write:.4f} seconds")

# Final verification reminder
print("\n--- Verification ---")
print("After running this script, check your Firebase Console:")
print("Project: trading-site-ticketing -> Firestore Database -> 'algorecords' (select from dropdown) -> 'TMS' collection.")
print(f"You will find {NUM_WRITES} new documents, each with a unique ID and a 'wfw' field like 'fjck0_run_X'.")

print( firestore.SERVER_TIMESTAMP)
# Verification: After running this script, check your Firebase Console:
# Project: trading-site-ticketing -> Firestore Database -> 'algo' collection.
# You will see a new document with an auto-generated ID containing the data specified above.