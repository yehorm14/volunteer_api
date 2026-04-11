# Volunteer Task Manager API

This is a robust backend foundation designed to help organize community service efforts. Developed as a personal project to practice and master building modern web services with FastAPI, this API provides a secure and fast way to manage volunteer assignments. It uses an asynchronous architecture to ensure high performance while maintaining strict data privacy and isolation for every user.

---

## Core Features

* **Secure Authentication**
    * User registration with real-time password hashing using the Bcrypt engine.
    * Stateless session management using JSON Web Tokens (JWT).
    * Protected routes that strictly require a valid bearer token for access.

* **Task Management**
    * Complete CRUD (Create, Read, Update, Delete) logic for volunteer tasks.
    * Support for partial updates (PATCH) to modify status or titles without data loss.
    * Automated mapping of task ownership to the authenticated user.

* **Data Isolation & Security**
    * Strict database-level filtering ensures users can only access their own records.
    * Ownership verification performed on every update and delete request.
    * CORS middleware pre-configured for seamless integration with React/Vite frontends.

* **Developer Experience**
    * Interactive API documentation generated automatically via Swagger UI.
    * Rigorous data validation and clear error reporting using Pydantic V2.
    * Clean, modular code structure following Software Engineering best practices.

---

## Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI | High-performance asynchronous web framework |
| **Database** | SQLite | Lightweight and portable relational storage |
| **ORM** | SQLAlchemy | Mapping Python objects to database tables |
| **Security** | Bcrypt & JWT | Industry-standard hashing and session tokens |
| **Validation** | Pydantic V2 | Strict type checking and data serialization |

---

## Setup Instructions

Follow these steps to initialize the development environment on your local machine.

### 1. Clone the Repository
Clone this repository to your local machine and navigate into the project directory.

### 2. Create a Virtual Environment
Isolate the project dependencies from your global Python installation.
```bash
python -m venv venv
```

### 3. Activate the Environment
Use the following command to tell your terminal to use the project specific Python version.

```bash
# For Windows
venv\Scripts\activate

# For Mac or Linux
source venv/bin/activate
```
### 4. Install Dependencies
Install the required packages using the latest versions compatible with Python 3.13.

```bash
pip install -r requirements.txt
```
### 5. Configure Environment Variables
Create a file named .env in the root directory. Add the following configurations and ensure you use a unique secret key for development.

```plaintext
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```
### 6. Launch the Development Server
Start the API with the modern FastAPI CLI to enable auto reload.
``` bash
fastapi dev main.py
```
---

### API Endpoints Reference
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/auth/register` | POST | Create a new volunteer account |
| `/auth/login` | POST | Log in to receive a secure access token |
| `/tasks` | GET | List all tasks belonging to the current user |
| `/tasks` | POST | Create a new task assigned to your account |
| `/tasks/{id}` | GET | Retrieve detailed information for a single task |
| `/tasks/{id}` | PATCH | Update specific fields like status or title |
| `/tasks/{id}` | DELETE | Permanently remove a task from the database |

---

### Testing the API
With the server running you can test the entire workflow without a front end. Visit `http://127.0.0.1:8000/docs`  to access the Swagger UI. Register a user then use the Authorize button to log in with your credentials and begin interacting with the secure task endpoints.

