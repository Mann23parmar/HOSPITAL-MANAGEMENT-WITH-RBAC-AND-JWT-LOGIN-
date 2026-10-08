"""Create a one-time link for setting up the first admin account."""

import hashlib
import secrets
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlsplit

from app.core.config import settings
from app.database.connection import admin_invitations_collection, users_collection
from app.schemas.user import normalize_and_validate_email

#check weather email is provided in the command line arguments or not
if len(sys.argv) != 2:
    print("email should be in this formate= client@example.com")
    sys.exit(1)
    
    
try:
    email = normalize_and_validate_email(sys.argv[1])
except ValueError:
    print("Please provide a valid email address.")
    sys.exit(1)

#rstrip("/") simply removes / if it exists at the end
setup_url = settings.admin_setup_url.rstrip("/")


#break the url into pieces
url_parts = urlsplit(setup_url)



#check weather url is http or https because invitation toke is contain secret token so https is secure
if url_parts.scheme not in {"http", "https"} or not url_parts.netloc:
    print("ADMIN_SETUP_URL must be a full HTTP or HTTPS URL.")
    sys.exit(1)

#here this part is tell that http is ok for local development but production shoud use https
if url_parts.scheme == "http" and url_parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
    print("Use HTTPS for an invitation link outside local testing.")
    sys.exit(1)


#here this is simple that if this check that admin already exist or not 
if users_collection.find_one({"role": "admin"}):
    print("An admin already exists. No invitation was created.")
    sys.exit(1)


# Make a random token. Only its hash will be saved in MongoDB.
token = secrets.token_urlsafe(32)

#hash the token 
token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

#current utc time 
created_at = datetime.now(timezone.utc)

#calculate expiration time
expires_at = created_at + timedelta(minutes=settings.admin_invitation_expire_minutes)

#it ask mongodb that find old invitation that is not being used yet and make invalid them.
admin_invitations_collection.update_many(
    {"used": False},
    {"$set": {"used": True, "revoked_at": created_at}},
)


#now save the invitation in mongodb
admin_invitations_collection.insert_one(
    {
        "token_hash": token_hash,
        "email": email,
        "expires_at": expires_at,
        "used": False,
        "created_at": created_at,
    }
)

# The token goes in the URL fragment so the browser does not send it in the page request.
email_for_url = quote(email, safe="")

#create the invitation link
invitation_link = (f"{setup_url}?email={email_for_url}#token={token}")

print(f"Invitation created for {email}")
print(f"Expires at: {expires_at.isoformat()}")
print("Send this link to the client:")
print(invitation_link)
