import requests
import json


def getSyro():
    url = "https://api-production.syro.com/cli/secrets"
    payload = {
        "accessTokens": ["pat_Y0w3hfaOyWyPsXDlYoinrFYQe57e50379e9f66e74236d9e7e747c789"]
    }

    try:
        response = requests.post(url, json=payload)
        response_data = response.json()["i"]
        print(response_data)

        if isinstance(response_data, list):
            keys_dict = {entry['key']: entry['value']
                         for entry in response_data}
            return keys_dict
        else:
            print("Invalid response format. Expected a list.")
            return None

    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)
        return None
