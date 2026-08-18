document.addEventListener("DOMContentLoaded", () => {
  const capabilitiesList = document.getElementById("capabilities-list");
  const capabilitySelect = document.getElementById("capability");
  const registerForm = document.getElementById("register-form");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const authStatus = document.getElementById("auth-status");
  const logoutButton = document.getElementById("logout-button");
  const pendingContainer = document.getElementById("pending-container");
  const pendingList = document.getElementById("pending-list");
  let currentUser = JSON.parse(localStorage.getItem("capabilitiesUser") || "null");
  let accessToken = localStorage.getItem("capabilitiesToken");

  function authHeaders() {
    return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  }

  function updateAuthUI() {
    const signedIn = Boolean(accessToken && currentUser);
    loginForm.classList.toggle("hidden", signedIn);
    logoutButton.classList.toggle("hidden", !signedIn);
    authStatus.classList.toggle("hidden", !signedIn);
    authStatus.textContent = signedIn
      ? `Signed in as ${currentUser.username} (${currentUser.role.replace("_", " ")})`
      : "";
    if (signedIn && currentUser.role === "practice_lead") {
      refreshPendingRequests();
    } else {
      pendingContainer.classList.add("hidden");
    }
  }

  async function refreshPendingRequests() {
    const response = await fetch("/registrations/pending", { headers: authHeaders() });
    if (!response.ok) {
      pendingContainer.classList.add("hidden");
      return;
    }
    const requests = await response.json();
    pendingList.innerHTML = requests.length
      ? requests.map((request, index) => `
          <li>
            ${request.email} requested ${request.capability}
            <button class="approve-btn" data-request-index="${index}" type="button">Approve</button>
          </li>`).join("")
      : "<li>No pending requests</li>";
    pendingContainer.classList.remove("hidden");
    document.querySelectorAll(".approve-btn").forEach((button) => {
      button.addEventListener("click", handleApproval);
    });
  }

  async function handleApproval(event) {
    const requestIndex = event.target.getAttribute("data-request-index");
    const response = await fetch(`/registrations/pending/${requestIndex}/approve`, {
      method: "POST",
      headers: authHeaders(),
    });
    const result = await response.json();
    messageDiv.textContent = result.message || result.detail;
    messageDiv.className = response.ok ? "success" : "error";
    messageDiv.classList.remove("hidden");
    if (response.ok) {
      refreshPendingRequests();
      fetchCapabilities();
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      authStatus.textContent = result.detail || "Unable to sign in";
      authStatus.className = "error";
      authStatus.classList.remove("hidden");
      return;
    }
    accessToken = result.access_token;
    currentUser = result.user;
    localStorage.setItem("capabilitiesToken", accessToken);
    localStorage.setItem("capabilitiesUser", JSON.stringify(currentUser));
    loginForm.reset();
    updateAuthUI();
    fetchCapabilities();
  }

  async function handleLogout() {
    await fetch("/auth/logout", { method: "POST", headers: authHeaders() });
    accessToken = null;
    currentUser = null;
    localStorage.removeItem("capabilitiesToken");
    localStorage.removeItem("capabilitiesUser");
    updateAuthUI();
    fetchCapabilities();
  }

  // Function to fetch capabilities from API
  async function fetchCapabilities() {
    try {
      const response = await fetch("/capabilities");
      const capabilities = await response.json();

      // Clear loading message
      capabilitiesList.innerHTML = "";

      // Populate capabilities list
      Object.entries(capabilities).forEach(([name, details]) => {
        const capabilityCard = document.createElement("div");
        capabilityCard.className = "capability-card";

        const availableCapacity = details.capacity || 0;
        const currentConsultants = details.consultants ? details.consultants.length : 0;

        // Create consultants HTML with delete icons
        const consultantsHTML =
          details.consultants && details.consultants.length > 0
            ? `<div class="consultants-section">
              <h5>Registered Consultants:</h5>
              <ul class="consultants-list">
                ${details.consultants
                  .map(
                    (email) =>
                      `<li><span class="consultant-email">${email}</span><button class="delete-btn" data-capability="${name}" data-email="${email}">❌</button></li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No consultants registered yet</em></p>`;

        capabilityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Practice Area:</strong> ${details.practice_area}</p>
          <p><strong>Industry Verticals:</strong> ${details.industry_verticals ? details.industry_verticals.join(', ') : 'Not specified'}</p>
          <p><strong>Capacity:</strong> ${availableCapacity} hours/week available</p>
          <p><strong>Current Team:</strong> ${currentConsultants} consultants</p>
          <div class="consultants-container">
            ${consultantsHTML}
          </div>
        `;

        capabilitiesList.appendChild(capabilityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        capabilitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      capabilitiesList.innerHTML =
        "<p>Failed to load capabilities. Please try again later.</p>";
      console.error("Error fetching capabilities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const capability = button.getAttribute("data-capability");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(
          capability
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh capabilities list to show updated consultants
        fetchCapabilities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const capability = document.getElementById("capability").value;

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(
          capability
        )}/register?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        registerForm.reset();

        // Refresh capabilities list to show updated consultants
        fetchCapabilities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to register. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error registering:", error);
    }
  });

  // Initialize app
  loginForm.addEventListener("submit", handleLogin);
  logoutButton.addEventListener("click", handleLogout);
  updateAuthUI();
  fetchCapabilities();
});
