# Volunteer Task Manager

A full-stack web application for managing volunteer assignments. Built as a personal project to practice modern full-stack development with FastAPI and React. Features secure JWT authentication, complete task CRUD, AI-powered task tools, and a clean responsive UI.

---

## Core Features

* **Secure Authentication**
    * User registration with real-time password hashing using the Bcrypt engine.
    * Stateless session management using JSON Web Tokens (JWT).
    * Protected routes on both the frontend and backend requiring a valid bearer token.

* **Task Management**
    * Complete CRUD (Create, Read, Update, Delete) for volunteer tasks.
    * Support for partial updates (PATCH) to modify status or title without data loss.
    * Automated ownership mapping — tasks are always linked to the authenticated user.
    * Optimistic UI updates on the frontend with automatic rollback on failure.

* **AI Features**
    * **AI Categorize** — analyses a task's title and description and returns a one-word category with a brief explanation, powered by GPT-4o Mini.
    * **Extract from Notes** — takes messy freeform notes and uses structured output parsing to extract a properly formatted task title and description.

* **Modern Frontend**
    * React 18 with TypeScript for a fully type-safe component tree.
    * Tailwind CSS dark-mode UI with a consistent design system.
    * Filter tabs, task stats dashboard, modal creation flow, and inline edit/delete on task detail pages.
    * Fully responsive layout down to mobile screen widths.

* **Data Isolation & Security**
    * Strict database-level filtering ensures users can only access their own records.
    * Ownership verification on every update and delete request.
    * CORS middleware pre-configured for the Vite development server.

* **Developer Experience**
    * Interactive API documentation auto-generated via Swagger UI at `/docs`.
    * Rigorous data validation and clear error reporting using Pydantic V2.
    * Clean, modular code structure across both frontend and backend.

---

## Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI | High-performance async web framework |
| **Database** | SQLite | Lightweight relational storage |
| **ORM** | SQLAlchemy | Python object to database table mapping |
| **Security** | Bcrypt & JWT | Industry-standard hashing and session tokens |
| **Validation** | Pydantic V2 | Strict type checking and data serialisation |
| **AI** | OpenAI GPT-4o Mini | Task categorisation and note extraction |
| **Frontend** | React 18 + TypeScript | Type-safe component-based UI |
| **Styling** | Tailwind CSS | Utility-first responsive design |
| **Build Tool** | Vite | Fast dev server with HMR and proxy |
| **HTTP Client** | Axios | API requests with JWT interceptors |
| **Routing** | React Router v6 | Client-side routing with auth guards |

---

## Project Structure

```
volunteer_api/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, all route handlers
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # JWT logic and password hashing
│   ├── database.py      # DB engine, session, Base
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── types/         # Shared TypeScript interfaces
│       ├── services/      # Axios API client
│       ├── context/       # AuthContext, TasksContext
│       ├── hooks/         # useAuth, useTasks
│       ├── components/    # UI primitives, layout, task components
│       └── pages/         # Landing, Login, Register, Dashboard, TaskDetail
└── README.md
```

---

## Setup Instructions

### Backend

#### 1. Clone the Repository
Clone this repository to your local machine and navigate into the project directory.

#### 2. Create a Virtual Environment
```bash
python -m venv venv
```

#### 3. Activate the Environment
```bash
# Windows (PowerShell)
venv\Scripts\activate

# Mac or Linux
source venv/bin/activate
```

#### 4. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

#### 5. Configure Environment Variables
Create a `.env` file in the project root with the following:

```plaintext
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OPENAI_API_KEY=your_openai_api_key_here
```

#### 6. Launch the Backend Server
```bash
fastapi dev backend/main.py
```

The API will be available at `http://127.0.0.1:8000`.

---

### Frontend

#### 1. Navigate to the Frontend Directory
```bash
cd frontend
```

#### 2. Install Dependencies
```bash
npm install
```

#### 3. Start the Development Server
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` and automatically proxies all `/api` requests to the backend on port 8000.

---

## API Endpoints Reference

### Authentication

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/auth/register` | POST | Create a new volunteer account |
| `/auth/login` | POST | Log in and receive a JWT access token |

### Tasks

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/tasks` | GET | Required | List all tasks for the current user |
| `/tasks` | POST | Required | Create a new task |
| `/tasks/{id}` | GET | Required | Retrieve a single task |
| `/tasks/{id}` | PATCH | Required | Update task fields (title, status, description) |
| `/tasks/{id}` | DELETE | Required | Permanently delete a task |

### AI

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/tasks/{id}/ai-categorize` | POST | Required | Categorise a task using GPT-4o Mini |
| `/tasks/extract` | POST | Required | Extract a structured task from freeform notes |

---

## Testing the API

With the backend running, visit `http://127.0.0.1:8000/docs` to access the Swagger UI. Register a user, click **Authorize**, log in with your credentials, and begin interacting with all protected endpoints directly in the browser.
