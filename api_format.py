import requests
import json
import re


def parse_basket_string(s: str) -> dict:
    """
    Converts a specific string format into a dictionary, with validation.

    Args:
        s: The input string, e.g., "Basket=name.NQ_1,Order=*A.NQ:10,B.NQ:20*,Infos=(Stop=1,Profit=3,)"

    Returns:
        A dictionary with 'name', 'orders', and 'infos' keys.

    Raises:
        ValueError: If the 'Basket' name or 'Orders' section is missing or empty.
    """
    result_dict = {}

    # --- Parse Basket Name ---
    name_match = re.search(r"Basket=([^,]+)", s)
    if not name_match or not name_match.group(1):
        raise ValueError("Basket must not be empty.")
    result_dict['name'] = name_match.group(1)

    # --- Parse Orders ---
    orders_match = re.search(r"Order=\*(.*?)\*", s)
    if not orders_match or not orders_match.group(1):
        raise ValueError("Orders must not be empty.")
    
    orders_content = orders_match.group(1)
    orders_dict = {}
    for item in orders_content.split(','):
        if ':' in item:
            key, value = item.split(':')
            # The key is the full name (e.g., 'A.NQ')
            item_key = key
            orders_dict[item_key] = {'share': int(value)}
    result_dict['orders'] = orders_dict

    # --- Parse Infos (optional) ---
    infos_match = re.search(r"Infos=\((.*?)\)", s)
    infos_dict = {}
    if infos_match and infos_match.group(1):
        infos_content = infos_match.group(1)
        for item in infos_content.split(','):
            if '=' in item:
                key, value = item.split('=')
                infos_dict[key] = int(value)
    result_dict['infos'] = infos_dict

    return result_dict


def send_data_with_post(data_dict: dict, url: str):
    """
    Sends a dictionary as a JSON payload to a specified URL using HTTP POST.
    """
    try:
        # requests.post automatically serializes the 'json' parameter to a JSON string
        response = requests.post(url, json=data_dict, timeout=2)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        print(f"Data sent successfully to {url}.")
        print(f"Server response: {response.status_code} - {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"Error: Connection refused. Is a server running and listening on {url}?")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

# Example usage:
Basket_string = "Basket=name.NQ_1,Order=*A.NQ:10,B.NQ:20*,Infos=(Stop=1,Profit=3,)"
parsed_dict = parse_basket_string(Basket_string)
print(parsed_dict)

# Example usage:
Basket_string = "Basket=name.NQ_1,Order=*A.NQ:10,B.NQ:20*,Infos=(Stop=1)"
parsed_dict = parse_basket_string(Basket_string)
print(parsed_dict)

# Example usage:
Basket_string = "Basket=name,Order=*A.NQ:10*"
parsed_dict = parse_basket_string(Basket_string)
print(parsed_dict)


for i in range(60,100):

    x ='T'
    if i%2==0:
        x='S'
    req = f"https://tnv.ngrok.io/Basket=BB_TESTS{str(i)},Order=*{str(x)}QQQ.NQ:{str(i)}*"

    parsed_dict = parse_basket_string(req)
    print(parsed_dict)

    send_data_with_post(parsed_dict,'http://10.29.10.129:4440/command')