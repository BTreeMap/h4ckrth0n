# GitHub Copilot Guide for h4ckrth0n

This document provides guidance on using GitHub Copilot effectively with the h4ckrth0n project.

## Project Structure

```
h4ckrth0n/
├── h4ckrth0n/
│   ├── __init__.py         # Main package initialization
│   ├── auth/               # Authentication functionality
│   ├── database/           # Database operations
│   ├── api/                # API development tools
│   ├── tasks/              # Background task processing
│   └── utils/              # Utility functions
└── tests/                  # Test suite
```

## Effective Prompts

When using GitHub Copilot with h4ckrth0n, consider these effective prompting strategies:

### Creating Models

```python
# Create a User model with username, email, and password fields
```

### API Endpoints

```python
# Create a RESTful CRUD endpoint for the Product model
```

### Authentication Logic

```python
# Implement JWT token validation middleware
```

### Database Queries

```python
# Create a function to query users by email with pagination
```

### Background Tasks

```python
# Define a background task that runs every hour to clean up expired sessions
```

## Common Patterns

### Route Definition

The h4ckrth0n library uses decorator-based routing:

```python
@app.route("/path", methods=["GET"])
@auth.require_login
def handler():
    # Function implementation
```

### Model Definition

Models follow the SQLAlchemy declarative pattern with h4ckrth0n enhancements:

```python
class ModelName(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    field = db.Column(db.String(255), nullable=False)
    
    # Helper methods often follow
    def to_dict(self):
        # ...
```

### Task Definition

Background tasks use the @create_task decorator:

```python
@tasks.create_task(schedule="daily")
def task_name():
    # Task implementation
```

## Testing

For test files, use pytest fixtures provided by h4ckrth0n:

```python
def test_feature(client, db_session):
    # Test implementation using standard fixtures
```

## Best Practices

1. Use type hints to improve Copilot suggestions
2. Write descriptive docstrings for complex functions
3. Follow the established naming conventions in existing code
4. Break complex operations into smaller, well-named functions
