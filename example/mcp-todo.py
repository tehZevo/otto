import json
import os
import uuid
import sys
from fastmcp import FastMCP
import subprocess

app = FastMCP()

# Get the todo file path from command line argument, default to "todos.json"
TODO_FILE = sys.argv[1] if len(sys.argv) > 1 else "todos.json"

def load_todos():
    """Load todos from JSON file"""
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, 'r') as f:
            return json.load(f)
    return []

def save_todos(todos):
    """Save todos to JSON file"""
    with open(TODO_FILE, 'w') as f:
        json.dump(todos, f, indent=2)

def validate_todo_ids(todo_ids: list[str]) -> tuple[list[str], list[str]]:
    todos = load_todos()
    existing_ids = {todo["id"] for todo in todos}
    valid_ids = [e for e in todo_ids if e in existing_ids]
    invalid_ids = [e for e in todo_ids if e not in existing_ids]
    
    return valid_ids, invalid_ids

def list_todos_helper():
    """Helper function to display current list of todos"""
    todos = load_todos()
    if not todos:
        return "The todo list is empty"
    
    result = "Current todo list:\n"
    for todo in todos:
        status = "☑️" if todo["completed"] else "☐"
        result += f"{todo['id']}: {status} {todo['task']}\n"
    return result

@app.tool()
def add_todos(tasks: list[str]):
    """Add multiple todo items"""
    todos = load_todos()
    added_tasks = []
    for task in tasks:
        todo_id = str(uuid.uuid4())
        todos.append({
            "id": todo_id,
            "task": task,
            "completed": False
        })
        added_tasks.append(f"{task} (ID: {todo_id})")
    save_todos(todos)
    return f"Added todos: {', '.join(added_tasks)}\n\n{list_todos_helper()}"

@app.tool()
def remove_todos(todo_ids: list[str]):
    """Remove multiple todo items by UUIDs"""
    valid_ids, invalid_ids = validate_todo_ids(todo_ids)
    
    if invalid_ids:
        return f"Invalid todo IDs not found: {', '.join(invalid_ids)}"
    
    if not valid_ids:
        return "No valid todo IDs provided"
    
    # Remove valid todos
    todos = load_todos()
    removed_tasks = []
    remaining_todos = []
    
    for todo in todos:
        if todo["id"] in valid_ids:
            removed_tasks.append(todo["task"])
        else:
            remaining_todos.append(todo)
    
    save_todos(remaining_todos)
    return f"Removed todos: {', '.join(removed_tasks)}\n\n{list_todos_helper()}"

@app.tool()
def complete_todos(todo_ids: list[str]):
    """Complete multiple todo items by UUIDs"""
    valid_ids, invalid_ids = validate_todo_ids(todo_ids)
    
    if invalid_ids:
        return f"Invalid todo IDs not found: {', '.join(invalid_ids)}"
    
    if not valid_ids:
        return "No valid todo IDs provided"
    
    # Mark valid todos as complete
    todos = load_todos()
    completed_tasks = []
    
    for todo in todos:
        if todo["id"] in valid_ids:
            todo["completed"] = True
            completed_tasks.append(todo["task"])
    
    save_todos(todos)
    return f"Completed todos: {', '.join(completed_tasks)}\n\n{list_todos_helper()}"

@app.tool()
def reorder_todos(todo_ids: list[str], new_position: int):
    """Reorder multiple todo items to a new position (0-indexed). Use -1 to move the selected todos to the end of the list."""
    todos = load_todos()
    
    valid_ids, invalid_ids = validate_todo_ids(todo_ids)
    
    if invalid_ids:
        return f"Invalid todo IDs not found: {', '.join(invalid_ids)}"
    
    if not valid_ids:
        return "No valid todo IDs provided"
    
    # Handle special case: -1 means add to the end
    if new_position == -1:
        new_position = len(todos)
    
    # Validate position
    if not (0 <= new_position <= len(todos)):
        return f"Invalid position. Must be between 0 and {len(todos)} inclusive, or -1."
    
    todos_by_id = {todo["id"]: todo for todo in todos}
    todos_to_move = [todos_by_id[id_val] for id_val in valid_ids]
    remaining_todos = list(filter(lambda todo: todo["id"] not in valid_ids, todos))
    
    # Insert todos at new position in the order they appear in todo_ids
    if new_position >= len(remaining_todos):
        result_todos = remaining_todos + todos_to_move
    else:
        result_todos = remaining_todos[:new_position] + todos_to_move + remaining_todos[new_position:]
    
    save_todos(result_todos)
    return f"Reordered todos to position {new_position}: {', '.join([todo['id'] for todo in todos_to_move])}\n\n{list_todos_helper()}"

@app.tool()
def clear_todos():
    """Clear all todo items"""
    save_todos([])
    return list_todos_helper()

@app.tool()
def list_todos():
    """List all todo items"""
    return list_todos_helper()

app.run()
