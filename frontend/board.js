"use strict";

// Behavior of the board. Task text comes from anyone, so it is only ever put
// on the page with textContent, never as HTML.

const STATUSES = ["To Do", "In Progress", "Done"];

const form = document.getElementById("task-form");
const titleInput = document.getElementById("title");
const descriptionInput = document.getElementById("description");
const statusInput = document.getElementById("status");
const submitButton = document.getElementById("submit");
const cancelButton = document.getElementById("cancel");
const message = document.getElementById("message");

// The task being edited, or null when the form adds a new one.
let editingId = null;
// The last list from the server. Edit and status changes read from it.
let tasks = [];

/**
 * Call the API and return the parsed JSON (null for an empty 204).
 * Throws an Error whose message is safe to show to the person using the board.
 */
async function api(method, path, body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new Error("Could not reach the server. Check your connection and try again.");
  }

  if (response.status === 204) {
    return null;
  }

  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    // Not JSON, for example an error page from Nginx or Flask.
  }

  if (!response.ok) {
    throw new Error((data && data.error) || `Something went wrong (HTTP ${response.status}). Try again.`);
  }
  return data;
}

function showMessage(text) {
  message.textContent = text;
  message.hidden = false;
}

function clearMessage() {
  message.textContent = "";
  message.hidden = true;
}

/**
 * Run an action, show its error if it fails, then reload the board so the page
 * always shows what is in the database, not what it assumes.
 */
async function run(action) {
  clearMessage();
  try {
    await action();
  } catch (error) {
    showMessage(error.message);
  }
  try {
    await loadBoard();
  } catch (error) {
    showMessage(error.message);
  }
}

async function loadBoard() {
  tasks = await api("GET", "/api/tasks");
  render();
}

function render() {
  for (const column of document.querySelectorAll(".column")) {
    const status = column.dataset.status;
    const inColumn = tasks.filter((task) => task.status === status);
    column.querySelector(".count").textContent = `(${inColumn.length})`;
    column.querySelector(".cards").replaceChildren(...inColumn.map(buildCard));
  }
}

function buildCard(task) {
  const card = document.createElement("li");
  card.className = "card";

  const title = document.createElement("h3");
  title.textContent = task.title;
  card.append(title);

  if (task.description) {
    const description = document.createElement("p");
    description.textContent = task.description;
    card.append(description);
  }

  const actions = document.createElement("div");
  actions.className = "card-actions";

  // Changing the status saves immediately.
  const statusSelect = document.createElement("select");
  statusSelect.setAttribute("aria-label", `Status of ${task.title}`);
  for (const status of STATUSES) {
    const option = document.createElement("option");
    option.textContent = status;
    option.selected = status === task.status;
    statusSelect.append(option);
  }
  statusSelect.addEventListener("change", () =>
    run(() =>
      api("PUT", `/api/tasks/${task.id}`, {
        title: task.title,
        description: task.description,
        status: statusSelect.value,
      })
    )
  );

  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.textContent = "Edit";
  editButton.addEventListener("click", () => startEditing(task));

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "delete";
  deleteButton.textContent = "Delete";
  deleteButton.addEventListener("click", () => {
    if (!window.confirm(`Delete "${task.title}"?`)) {
      return;
    }
    if (editingId === task.id) {
      resetForm();
    }
    run(() => api("DELETE", `/api/tasks/${task.id}`));
  });

  actions.append(statusSelect, editButton, deleteButton);
  card.append(actions);
  return card;
}

function startEditing(task) {
  clearMessage();
  editingId = task.id;
  titleInput.value = task.title;
  descriptionInput.value = task.description;
  statusInput.value = task.status;
  submitButton.textContent = "Save";
  cancelButton.hidden = false;
  titleInput.focus();
}

function resetForm() {
  form.reset();
  editingId = null;
  submitButton.textContent = "Add task";
  cancelButton.hidden = true;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const body = {
      title: titleInput.value,
      description: descriptionInput.value,
      status: statusInput.value,
    };
    if (editingId) {
      await api("PUT", `/api/tasks/${editingId}`, body);
    } else {
      await api("POST", "/api/tasks", body);
    }
    // Only reached on success, so a failed save keeps what was typed.
    resetForm();
  });
});

cancelButton.addEventListener("click", () => {
  clearMessage();
  resetForm();
});

run(async () => {});
