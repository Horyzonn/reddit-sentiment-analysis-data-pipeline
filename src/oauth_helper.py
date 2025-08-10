from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os
from reddit_client import reddit

# Xác định quyền (scope)
scopes = ["identity", "read", "submit", "history"]

auth_url = reddit.auth.url(scopes, "random_state_string", "permanent")
print("Open this URL in your browser:", auth_url)

#URL sau khi xác thực:
callback_url = "http://localhost:8080/?state=random_state_string&code=p8853f-c1c_DSy_1d7Xds9aS_N-8Wg#_"

#Trích xuất mã code
code = parse_qs(urlparse(callback_url).query)['code'][0]

#Lấy refresh_token
refresh_token = reddit.auth.authorize(code)
print("Refresh token:", refresh_token)

