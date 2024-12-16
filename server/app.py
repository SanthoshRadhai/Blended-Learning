from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token,get_jwt_identity
from flask_cors import CORS
from pymongo import MongoClient
from flask_jwt_extended import jwt_required
import ollama

app = Flask(__name__)
CORS(app)

# Configuration
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Use a strong, random secret key
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# MongoDB setup
client = MongoClient('mongodb://192.168.171.73:27017/')
db = client['user_database']
users_collection = db['users']
problems_collection = db['problems']

# User Registration Route
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    year = data.get('year')
    job_role = data.get('jobRole')  # Update key to match React
    register_number = data.get('registerNumber')  # Update key to match React
    password = data.get('password')
    confirm_password = data.get('confirmPassword')  # Update key to match React

    # Debugging prints
    print("Received data:", data)
    print("Password:", password)
    print("Confirm Password:", confirm_password)

    if password != confirm_password:
        print("Passwords do not match!")  # Debugging statement
        return jsonify(message="Passwords do not match"), 400

    if users_collection.find_one({"register_number": register_number}):
        return jsonify(message="User already exists"), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user_data = {
        "name": name,
        "year": year,
        "job_role": job_role,
        "register_number": register_number,
        "password": hashed_password
    }
    users_collection.insert_one(user_data)

    return jsonify(message="User registered successfully"), 201


# User Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    register_number = data.get('registerNumber')
    password = data.get('password')

    print("recived register numbe : ",register_number)
    print("getted password: ",password)
    print("recived json is : ",data)

    user = users_collection.find_one({"register_number": register_number})
    if not user or not bcrypt.check_password_hash(user['password'], password):
        return jsonify(message="Invalid credentials"), 401

    access_token = create_access_token(identity=register_number)
    return jsonify(access_token=access_token), 200

# Helper function to check if the user is a teacher
def is_teacher(register_number):
    user = users_collection.find_one({"register_number": register_number})
    return user and user.get("job_role") == "teacher"

# Problem Upload Route
@app.route('/upload_problem', methods=['POST'])
@jwt_required()  # Protect this route with JWT authentication
def upload_problem():
    # Get the current user's register number from the JWT
    register_number = get_jwt_identity()

    # Check if the user is a teacher
    if not is_teacher(register_number):
        return jsonify(message="Access denied: Only teachers can upload problems"), 403

    # Get the problem data from the request
    data = request.json
    id = data.get('id')
    title = data.get('title')
    description = data.get('description')
    editorial = data.get('editorial')
    solution_page = data.get('solutionPage')
    submission_page = data.get('submissionPage')
    test_cases = data.get('testCases')
    hint = data.get('hint')
    difficulty = data.get("difficulty")
    editor = data.get("editor")
    hidden_test_case = data.get("hiddenCase")

    # Check if all required fields are provided
    if not all([title, description, solution_page, submission_page, test_cases]):
        return jsonify(message="Missing required fields"), 400

    # Create a problem document
    problem_data = {
        "id":id,
        "title": title,
        "description": description,
        "editorial": editorial,
        "solutionPage": solution_page,
        "submissionPage": submission_page,
        "testCases": test_cases,
        "hint": hint,
        "difficulty":difficulty,
        "editor":editor,
        "hidden_test_case":hidden_test_case
    }

    # Insert the problem into the database
    problems_collection.insert_one(problem_data)

    print(problem_data)

    return jsonify(message="Problem uploaded successfully"), 201


@app.route('/problem/<int:id>', methods=['GET'])
# @jwt_required()  # Requires authentication
def get_problem(id):
    # Convert the id to a string for the query
    problem = problems_collection.find_one({"id": str(id)})  # Use str(id) instead of int(id)
    
    print(problem)  # Debug: print the problem
    print(id)       # Debug: print the id

    if not problem:
        return jsonify(message="Problem not found"), 404

    # Convert the MongoDB document to a dictionary
    problem_data = {
        "id": problem["id"],
        "title": problem["title"],
        "description": problem["description"],
        "editorial": problem["editorial"],
        "solutionPage": problem["solutionPage"],
        "submissionPage": problem["submissionPage"],
        "testCases": problem["testCases"],
        "hint": problem.get("hint"),
        "difficulty": problem.get("difficulty"),
        "editor": problem.get("editor"),
        "hidden_test_case": problem.get("hidden_test_case"),
    }

    return jsonify(problem_data), 200


@app.route('/problems', methods=['GET'])
# @jwt_required()  # Uncomment this if you want to require authentication
def get_problems():
    problems = problems_collection.find()
    problem_list = []
    for problem in problems:
        problem_data = {
            "id": problem["id"],
            "title": problem["title"],
            "description": problem["description"],
            "editorial": problem["editorial"],
            "solutionPage": problem["solutionPage"],
            "submissionPage": problem["submissionPage"],
            "testCases": problem["testCases"],
            "hint": problem.get("hint"),
            "difficulty": problem.get("difficulty"),
            "editor": problem.get("editor"),
            "hidden_test_case": problem.get("hidden_test_case"),
        }
        problem_list.append(problem_data)
    
    return jsonify(problem_list), 200

def get_response(ollama_query):
    # Make a request to the LLaMA model using Ollama's API
    response = ollama.chat(
        model='llama3.1', 
        messages=[
            {
                'role': 'system',
                'content': 'Give me answer as short as possible .'
            },
            {
                'role': 'user',
                'content': ollama_query
            }
        ]
    )
    
    # Get the full response content
    generated_string = response['message']['content']
    return generated_string

# Route to handle incoming query
@app.route('/ollama_query', methods=['POST'])
def query_model():
    try:
        # Get the ollama_query from the incoming JSON request
        data = request.get_json()
        ollama_query = data.get('ollama_query', '')

        # Check if the ollama_query is empty
        if not ollama_query:
            return jsonify({"error": "No query provided."}), 400
        
        # Get the response by making a normal (non-streaming) request to the model
        response = get_response(ollama_query)
        
        # Return the response in JSON format
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500




if __name__ == '__main__':
    app.run(debug=True, host='192.168.171.73', port=5000)

