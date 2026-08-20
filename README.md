# To-Do List App (Flask + MySQL + Vanilla JS)

A full-stack to-do list app with user accounts, so every user only ever
sees their own tasks.

**Stack**
- Backend: Python + Flask (REST API, session-based auth)
- Database: MySQL
- Frontend: plain HTML / CSS / JavaScript (no build step, no framework)

**Features**
- Register / log in / log out (passwords hashed with Werkzeug)
- Add, view, edit, delete tasks
- Mark tasks complete
- Set priority (low / medium / high) and due date
- Filter by status/priority, sort by newest/due date/priority
- Each task is tied to a `user_id` — users can never see each other's tasks

---

## 1. Prerequisites

- Python 3.9+
- MySQL Server 8.x (or MariaDB) running locally or remotely
- `pip`

## 2. Set up the database

Log into MySQL and run the schema file:

```bash
mysql -u root -p < backend/schema.sql
```

This creates a `todo_app` database with `users` and `tasks` tables.
(You can also just paste the contents of `backend/schema.sql` into
MySQL Workbench / phpMyAdmin / TablePlus.)

## 3. Configure environment variables

```bash
cd backend
cp .env.example .env
```

Edit `.env` and set your real MySQL username/password:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=todo_app
DB_PORT=3306
SECRET_KEY=some-long-random-string
```

## 4. Install dependencies & run the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The server starts at **http://localhost:5000**. Flask also serves the
frontend directly from that same address, so there's nothing extra to
run — just open the URL in your browser.

## 5. Use the app

1. Go to `http://localhost:5000/register.html` and create an account.
2. You'll be redirected to the dashboard (`index.html`).
3. Add tasks with a title, optional description, priority, and due date.
4. Check the box to mark a task complete, use Edit/Delete as needed.
5. Log out via the top-right button; log back in at `/login.html`.

---

## Project structure

```
todo-app/
├── backend/
│   ├── app.py            # Flask app: routes, auth, task CRUD
│   ├── db.py              # MySQL connection helper
│   ├── schema.sql          # Database schema (users + tasks tables)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html          # Dashboard (task list, add/edit)
    ├── login.html
    ├── register.html
    ├── css/style.css
    └── js/
        ├── api.js          # fetch() wrapper for the backend API
        └── app.js          # Dashboard logic
```

## API reference

| Method | Endpoint                  | Description                       |
|--------|----------------------------|------------------------------------|
| POST   | `/api/register`            | Create a new user                 |
| POST   | `/api/login`                | Log in, starts a session          |
| POST   | `/api/logout`               | Clears the session                |
| GET    | `/api/me`                   | Check current auth status         |
| GET    | `/api/tasks`                 | List current user's tasks (supports `?completed=`, `?priority=`, `?sort=`) |
| POST   | `/api/tasks`                 | Create a task                     |
| GET    | `/api/tasks/<id>`            | Get one task                      |
| PUT    | `/api/tasks/<id>`            | Update a task                     |
| PATCH  | `/api/tasks/<id>/complete`   | Toggle/set completed status       |
| DELETE | `/api/tasks/<id>`            | Delete a task                     |

All `/api/tasks*` routes require an active login session and are
automatically scoped to `session["user_id"]` — there is no way to
fetch or modify another user's tasks through the API.

## Notes / things you could improve later

- Passwords are hashed, but for production you'd also want HTTPS,
  rate-limiting on login/register, and CSRF protection.
- Sessions are Flask's default cookie-based sessions — fine for
  learning/small projects; for a larger app consider JWTs or a
  server-side session store (e.g. Redis).
- No pagination on `/api/tasks` yet — fine for personal use, but
  worth adding `LIMIT`/`OFFSET` if task lists get huge.
