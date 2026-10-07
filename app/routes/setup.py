import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.connection import admin_invitations_collection, users_collection
from app.schemas.setup import InitialAdminCreate
from app.services.audit_service import create_audit_log
from app.services.auth_service import hash_password


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


@router.post("/setup/admin")
def create_initial_admin(admin: InitialAdminCreate):
    existing_admin = users_collection.find_one({"role": "admin"})
    if existing_admin:
        raise HTTPException(
            status_code=403,
            detail="Initial admin setup has already been completed",
        )

    email = admin.email.strip().lower()
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(admin.invitation_token.encode("utf-8")).hexdigest()
    invitation = admin_invitations_collection.find_one_and_update(
        {
            "token_hash": token_hash,
            "email": email,
            "used": False,
            "expires_at": {"$gt": now},
        },
        {"$set": {"used": True, "used_at": now}},
        return_document=ReturnDocument.BEFORE,
    )
    if invitation is None:
        raise HTTPException(
            status_code=403,
            detail="Invitation is invalid, expired, already used, or does not match this email",
        )

    user_data = {
        "email": email,
        "password": hash_password(admin.password),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
    }

    try:
        result = users_collection.insert_one(user_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=403,
            detail="Initial admin setup has already been completed",
        )

    create_audit_log(
        action="CREATE",
        collection="users",
        record_id=str(result.inserted_id),
        current_user={"email": email, "role": "admin"},
    )

    return {"message": "Initial admin created successfully"}
