import json
import requests

def get_holders_count(token_address):
    try:
        splited = token_address.split('::')
        used_address =splited[0]
        url = f"https://api.blockberry.one/sui/v1/coins/{used_address}%3A%3A{splited[-2]}%3A%3A{splited[-1]}"

        headers = {
            "accept": "*/*",
            "x-api-key": "RQHohI3MlLTjDAcbDTjXGk1S0Iv2Wf"
        }

        response = requests.get(url, headers=headers)
        with open('fd.json','w')as file:
            json.dump(response.json(),file,indent=4)
        data = response.json()['holdersCount']
        dev_wallet =response.json()['creatorAddress']

        return data,dev_wallet
    except Exception as e:
        print(e)
    

data = get_holders_count('0xa8b69040684d576828475115b30cc4ce7c7743eab9c7d669535ee31caccef4f5::suiman::SUIMAN')

print(data)