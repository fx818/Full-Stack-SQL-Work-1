# SQL Agent API with Memory

A FastAPI application that processes natural language questions into SQL queries with conversation memory stored in Supabase PostgreSQL database.

## Features

- **Natural Language to SQL**: Convert questions to SQL queries using LangChain and Groq
- **Conversation Memory**: Store and retrieve conversation history per user in Supabase
- **Context Resolution**: Resolve pronouns and contextual references using conversation history
- **User-based Memory**: Separate memory storage for different usernames
- **Health Monitoring**: Built-in health checks for database connections

## Project Structure

```
sql_agent_api/
├── app/
│   ├── main.py                 # FastAPI main application
│   ├── models/
│   │   ├── memory.py           # Memory data models
│   │   └── request_response.py # API request/response models
│   ├── services/
│   │   ├── sql_agent.py        # Core SQL agent logic
│   │   ├── memory_service.py   # Memory management service
│   │   └── database.py         # Supabase database service
│   ├── api/
│   │   └── routes.py           # API route definitions
│   └── core/
│       └── config.py           # Configuration settings
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
├── student.db                  # SQLite database (your existing file)
└── README.md                   # This file

```

## Setup Instructions

### 1. Environment Setup

Create a `.env` file in the project root:

```bash
# API Keys
API_KEY=your_groq_api_key_here
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

The application will automatically create the required tables in your Supabase database on startup:

- `conversation_memory`: Stores user conversation histories, question patterns, and entities
- Indexes and triggers for performance optimization

### 4. Place Your SQLite Database

Ensure your `student.db` file is in the project root directory.

### 5. Run the Application

```bash

uvicorn app.main:app --reload

```

## API Endpoints

### Core Query Processing

**POST `/api/v1/query`**
```json
{
  "username": "john_doe",
  "question": "What are the marks of Alice?"
}
```

Response:
```json
{
  "question": "What are the marks of Alice?",
  "resolved_question": "What are the marks of Alice?",
  "sql_query": "SELECT marks FROM students WHERE name LIKE '%alice%' LIMIT 10",
  "result": "[(85,), (92,)]",
  "answer": "Alice has marks of 85 and 92.",
  "success": true,
  "error": null
}
```

### Memory Management

**POST `/api/v1/memory/command`**
```json
{
  "username": "john_doe",
  "command": "/history"
}
```

Available commands:
- `/history` - Get conversation history
- `/clear` - Clear user memory
- `/entities` - Get known entities
- `/summary` - Get conversation summary
- `/users` - Get all users (admin)

**GET `/api/v1/memory/{username}/history`**
- Get conversation history for specific user

**DELETE `/api/v1/memory/{username}`**
- Clear memory for specific user

### Administrative

**GET `/api/v1/users`**
- Get all users with conversation memory

**GET `/api/v1/health`**
- Health check for database connections


## Database Schema (Supabase)

The application creates this table in your Supabase database:

```sql
CREATE TABLE conversation_memory (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    conversation_history JSONB DEFAULT '[]'::jsonb,
    question_patterns JSONB DEFAULT '{}'::jsonb,
    entity_memory JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Development

### Adding New Features
1. Add models in `app/models/`
2. Implement business logic in `app/services/`
3. Add API endpoints in `app/api/routes.py`
4. Update configuration in `app/core/config.py`

### Testing
```bash
# Run the application
uvicorn app.main:app --reload

# Visit http://localhost:8000/docs for interactive API documentation
```

