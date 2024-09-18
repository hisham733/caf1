# import requests
# import frappe

# @frappe.whitelist(allow_guest=True)
# def test_green_api():
#     print("SOMETHING" * 100)
    
#     # GreenAPI URL to receive notification
#     url = "https://7103.api.greenapi.com/waInstance7103950521/receiveNotification/bdd5af304e1746c1ab1b79cff8da3fcb974ec9e7139b49aeac"
    
#     payload = {}  # Ensure payload is as expected by the endpoint
#     headers = {}  # Ensure headers are as expected by the endpoint
    
#     print("=" * 10, payload)
#     print("#" * 10, requests)
    
#     try:
#         response = requests.get(url, headers=headers, json=payload)
#         response.raise_for_status()
#         print("Response received:", response.text.encode('utf8'))
#     except requests.exceptions.RequestException as e:
#         print(f"Error making request: {e}")
#         print(f"Request URL: {url}")
#         print(f"Request Headers: {headers}")
#         print(f"Request Payload: {payload}")
    
#     print("test_green_api function completed.")


#       # url = "https://7103.api.greenapi.com/waInstance7103950521/deleteNotification/f0520105c1634509946321e0d1eb939e66a1f1cf39c4480ca7/1234567"

#       # payload = {}
#       # headers= {}

#       # response = requests.request("DELETE", url, headers=headers, json = payload)

#       # print(response.text.encode('utf8'))

#       # response=(100*"hisham")