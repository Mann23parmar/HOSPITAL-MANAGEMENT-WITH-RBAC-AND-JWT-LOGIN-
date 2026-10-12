from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.schemas.setup import InitialAdminCreate
from app.services.setup_service import (
    create_initial_admin as create_initial_admin_workflow,
)


router = APIRouter()


@router.get("/setup/admin/invitation", response_class=HTMLResponse)
def admin_invitation_page():
    return HTMLResponse(
        content="""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Set up hospital administrator</title>
  <style>
    body { font: 16px system-ui, sans-serif; max-width: 30rem; margin: 4rem auto; padding: 0 1rem; }
    label { display: block; margin: 1rem 0 .35rem; }
    input, button { box-sizing: border-box; font: inherit; padding: .65rem; width: 100%; }
    button { margin-top: 1rem; cursor: pointer; }
    #message { margin-top: 1rem; }
  </style>
</head>
<body>
  <h1>Set up your administrator account</h1>
  <p>This one-time invitation is tied to the email address below.</p>
  <form id="setup-form">
    <label for="email">Email</label>
    <input id="email" name="email" type="email" autocomplete="username" required>
    <label for="password">Choose a password (8 to 12 characters)</label>
    <input id="password" name="password" type="password" minlength="8" maxlength="12" autocomplete="new-password" required>
    <button type="submit">Create administrator account</button>
  </form>
  <p id="message" role="status"></p>
  <script>
    const params = new URLSearchParams(window.location.search);
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    document.getElementById("email").value = params.get("email") || "";
    history.replaceState(null, "", window.location.pathname + window.location.search);
    const form = document.getElementById("setup-form");
    const message = document.getElementById("message");
    if (!token) {
      form.hidden = true;
      message.textContent = "This invitation link is missing its token. Ask the sender for a new invitation.";
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      message.textContent = "Submitting...";
      try {
        const response = await fetch("/setup/admin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: document.getElementById("email").value,
            password: document.getElementById("password").value,
            invitation_token: token
          })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Setup failed");
        form.hidden = true;
        message.textContent = "Administrator account created. You can now log in.";
      } catch (error) {
        message.textContent = error.message;
      }
    });
  </script>
</body>
</html>""",
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        },
    )


@router.post("/setup/admin", status_code=201)
def create_initial_admin(admin: InitialAdminCreate):
    return create_initial_admin_workflow(admin)
