import requests

url = 'http://10.254.109.38:5000//add_books'
data = {
    "books": ["A job to love the school of life"]
}

response = requests.post(url, json=data)
print(response.json())
