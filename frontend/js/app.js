/**
 * app.js
 * Powers the main dashboard (index.html): loading, rendering,
 * creating, editing, completing, and deleting tasks.
 */

const taskListEl = document.getElementById("task-list");
const emptyStateEl = document.getElementById("empty-state");
const welcomeText = document.getElementById("welcome-text");

const filterStatus = document.getElementById("filter-status");
const filterPriority = document.getElementById("filter-priority");
const sortBy = document.getElementById("sort-by");
const searchInput = document.getElementById("search-input");

const totalCount = document.getElementById("total-count");
const completedCount = document.getElementById("completed-count");
const pendingCount = document.getElementById("pending-count");

// ---- Guard: must be logged in to see this page ----
api.me().then((res) => {
  if (!res.authenticated) {
    window.location.href = "login.html";
  } else {
    welcomeText.textContent = `Hi, ${res.username}`;
    loadTasks();
  }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  await api.logout();
  window.location.href = "login.html";
});

// ---- Load + render tasks ----
async function loadTasks() {
  const filters = {};
  if (filterStatus.value) filters.completed = filterStatus.value;
  if (filterPriority.value) filters.priority = filterPriority.value;
  if (sortBy.value) filters.sort = sortBy.value;

  const tasks = await api.getTasks(filters);

  totalCount.textContent = tasks.length;
  completedCount.textContent = tasks.filter(task => task.completed).length;
  pendingCount.textContent = tasks.filter(task => !task.completed).length;

  const searchText = searchInput.value.trim().toLowerCase();

  const filteredTasks = tasks.filter((task) => {
    return (
      task.title.toLowerCase().includes(searchText) ||
      (task.description || "").toLowerCase().includes(searchText)
    );
  });

  renderTasks(filteredTasks);
}

[filterStatus, filterPriority, sortBy].forEach((el) =>
  el.addEventListener("change", loadTasks)
);

searchInput.addEventListener("input", loadTasks);

function isOverdue(dueDate, completed) {
  if (!dueDate || completed) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return new Date(dueDate) < today;
}

function renderTasks(tasks) {
  taskListEl.innerHTML = "";

  if (tasks.length === 0) {
    emptyStateEl.style.display = "block";
    return;
  }
  emptyStateEl.style.display = "none";

  for (const task of tasks) {
    const li = document.createElement("li");
    li.className = "task-card" + (task.completed ? " completed" : "");

    const overdue = isOverdue(task.due_date, task.completed);

    li.innerHTML = `
      <input type="checkbox" class="task-checkbox" ${task.completed ? "checked" : ""}>
      <div class="task-body">
        <p class="task-title"></p>
        ${task.description ? `<p class="task-desc"></p>` : ""}
        <div class="task-meta">
          <span class="badge ${task.priority}"></span>
          ${task.due_date ? `<span class="due-date ${overdue ? "overdue" : ""}"></span>` : ""}
        </div>
      </div>
      <div class="task-actions">
        <button class="icon-btn edit">Edit</button>
        <button class="icon-btn delete">Delete</button>
      </div>
    `;

    // Set text content via JS (avoids any HTML-injection issues with user input)
    li.querySelector(".task-title").textContent = task.title;
    if (task.description) li.querySelector(".task-desc").textContent = task.description;
    li.querySelector(".badge").textContent = task.priority.charAt(0).toUpperCase() + task.priority.slice(1);
    if (task.due_date) {
      const dueEl = li.querySelector(".due-date");
      dueEl.textContent = (overdue ? "⚠ Overdue: " : "Due: ") + task.due_date;
    }

    li.querySelector(".task-checkbox").addEventListener("change", async (e) => {
      await api.toggleComplete(task.id, e.target.checked);
      loadTasks();
    });

    li.querySelector(".edit").addEventListener("click", () => openEditModal(task));
    li.querySelector(".delete").addEventListener("click", async () => {
      if (confirm(`Delete "${task.title}"?`)) {
        await api.deleteTask(task.id);
        loadTasks();
      }
    });

    taskListEl.appendChild(li);
  }
}

// ---- Add task ----
const taskForm = document.getElementById("task-form");
const formError = document.getElementById("form-error");

taskForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  formError.style.display = "none";

  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim();
  const priority = document.getElementById("priority").value;
  const due_date = document.getElementById("due_date").value || null;

  try {
    await api.createTask({ title, description, priority, due_date });
    taskForm.reset();
    document.getElementById("priority").value = "medium";
    loadTasks();
  } catch (err) {
    formError.textContent = err.message;
    formError.style.display = "block";
  }
});

// ---- Edit modal ----
const modalOverlay = document.getElementById("modal-overlay");
const editForm = document.getElementById("edit-form");
const editError = document.getElementById("edit-error");

function openEditModal(task) {
  document.getElementById("edit-id").value = task.id;
  document.getElementById("edit-title").value = task.title;
  document.getElementById("edit-description").value = task.description || "";
  document.getElementById("edit-priority").value = task.priority;
  document.getElementById("edit-due_date").value = task.due_date || "";
  editError.style.display = "none";
  modalOverlay.classList.add("open");
}

document.getElementById("cancel-edit").addEventListener("click", () => {
  modalOverlay.classList.remove("open");
});

modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) modalOverlay.classList.remove("open");
});

editForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  editError.style.display = "none";

  const id = document.getElementById("edit-id").value;
  const payload = {
    title: document.getElementById("edit-title").value.trim(),
    description: document.getElementById("edit-description").value.trim(),
    priority: document.getElementById("edit-priority").value,
    due_date: document.getElementById("edit-due_date").value || null,
  };

  try {
    await api.updateTask(id, payload);
    modalOverlay.classList.remove("open");
    loadTasks();
  } catch (err) {
    editError.textContent = err.message;
    editError.style.display = "block";
  }
});
