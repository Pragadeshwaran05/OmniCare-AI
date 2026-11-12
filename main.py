from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

def connect_db():
    return sqlite3.connect("database.db")

# Create database table
with connect_db() as con:
    con.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT,
            completed INTEGER DEFAULT 0
        )
    """)

@app.route("/")
def home():
    return render_template("index.html")

# Display tasks
@app.route("/tasks")
def get_tasks():
    with connect_db() as con:
        rows = con.execute(
            "SELECT * FROM tasks"
        ).fetchall()

    return jsonify([
        {"id": r[0], "task": r[1], "completed": r[2]}
        for r in rows
    ])

# Add task
@app.route("/add", methods=["POST"])
def add_task():
    task = request.json["task"]

    with connect_db() as con:
        con.execute(
            "INSERT INTO tasks(task) VALUES(?)",
            (task,)
        )

    return jsonify({"message": "Task added"})

# Complete task
@app.route("/update/<int:id>", methods=["PUT"])
def update_task(id):
    completed = request.json["completed"]

    with connect_db() as con:
        con.execute(
            "UPDATE tasks SET completed=? WHERE id=?",
            (completed, id)
        )

    return jsonify({"message": "Task updated"})

# Delete task
@app.route("/delete/<int:id>", methods=["DELETE"])
def delete_task(id):
    with connect_db() as con:
        con.execute(
            "DELETE FROM tasks WHERE id=?", (id,)
        )

    return jsonify({"message": "Task deleted"})

if __name__ == "__main__":
    app.run(debug=True)