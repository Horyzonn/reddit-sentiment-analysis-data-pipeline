import requests
import requests.auth

client_id = "y4BcQZVJsId3BS2F0IS-Eg"       # chính là personal use script
client_secret = "vV90KaTFbUzcU9O4NOX7d13DSMesoA"
redirect_uri = "http://localhost:8089"   # phải khớp với app bạn đã tạo
code = "W6v0Y2AlgyVgY0dkRvaEs6824NQ6Aw"  # cái bạn vừa lấy

auth = requests.auth.HTTPBasicAuth(client_id, client_secret)

data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": redirect_uri
}

headers = {"User-Agent": "MyRedditApp/0.1 by u/YOURUSERNAME"}

response = requests.post(
    "https://www.reddit.com/api/v1/access_token",
    auth=auth,
    data=data,
    headers=headers
)

print(response.json())