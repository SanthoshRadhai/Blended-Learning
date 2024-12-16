from pymongo import MongoClient
from bson.objectid import ObjectId  # Import this to work with ObjectId if needed

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB URI
db = client["user_database"]  # Replace with your database name
collection = db["problems"]  # Replace with your collection name

# Query the database for a document where id is '1' (as a string)
query = {"id": "1"}  # Note: '1' is a string

# Retrieve the document
result = collection.find_one(query)

# Check if the result was found and print it
if result:
    print("Data found:", result)
else:
    print("No data found with id = '1'")
