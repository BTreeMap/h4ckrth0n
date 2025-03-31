# h4ckrth0n

A Python library to supercharge hackathon development by handling the boilerplate code for you.

## 🚀 Features

- **Authentication** - User registration, login, JWT tokens, password reset
- **Database** - Easy ORM setup, migrations, and query builders
- **API** - Rapid API development with automatic documentation
- **Background Tasks** - Efficient task queues and scheduling
- **Configuration** - Environment-based configuration management
- **Testing** - Tools to make testing your hackathon project easier

## 📦 Installation

```bash
pip install h4ckrth0n
```

Or if you're using Poetry:

```bash
poetry add h4ckrth0n
```

## 🔧 Quick Start

```python
from h4ckrth0n import create_app, Database, Auth

# Initialize your app with auth and database
app = create_app()
db = Database(app)
auth = Auth(app)

# Create an API endpoint that requires authentication
@app.route("/protected")
@auth.require_login
def protected_route():
    return {"message": "This is a protected endpoint!"}

# Run your app
if __name__ == "__main__":
    app.run()
```

## 💡 Usage Examples

### Database Operations

```python
from h4ckrth0n.database import Model, Column, String, Integer

# Define your model
class User(Model):
    name = Column(String)
    age = Column(Integer)

# Create tables
db.create_all()

# Create a new user
user = User(name="Hackathon Hero", age=25)
db.session.add(user)
db.session.commit()

# Query users
users = User.query.filter_by(name="Hackathon Hero").all()
```

### Authentication

```python
from h4ckrth0n.auth import require_auth, current_user

@app.route("/profile")
@require_auth
def profile():
    return {
        "user": current_user.to_dict(),
        "message": f"Hello {current_user.username}!"
    }
```

### Background Tasks

```python
from h4ckrth0n.tasks import create_task

@create_task(schedule="every 10 minutes")
def cleanup_old_sessions():
    # Task logic here
    pass
```

## 📚 Documentation

Full documentation is available at [https://h4ckrth0n.readthedocs.io/](https://h4ckrth0n.readthedocs.io/)

## 🧪 Development

Clone the repository:

```bash
git clone https://github.com/username/h4ckrth0n.git
cd h4ckrth0n
```

Install development dependencies:

```bash
poetry install --with dev
```

Run the tests:

```bash
poetry run pytest
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
