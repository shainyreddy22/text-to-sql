import urllib.request

print("Downloading sakila_master.db...")
url = "https://github.com/bradleygrant/sakila-sqlite3/raw/main/sakila_master.db"
urllib.request.urlretrieve(url, "sakila.db")
print("sakila.db downloaded successfully!")
