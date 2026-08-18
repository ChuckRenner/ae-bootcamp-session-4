"""
Slalom Capabilities Management System API

A FastAPI application that enables Slalom consultants to register their
capabilities and manage consulting expertise across the organization.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
from pathlib import Path

app = FastAPI(title="Slalom Capabilities Management API",
              description="API for managing consulting capabilities and consultant expertise")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SESSION_DURATION = timedelta(hours=8)
sessions = {}
pending_registrations = []
audit_log = []


class LoginRequest(BaseModel):
    username: str
    password: str


def load_users():
    with (current_dir / "practice_leads.json").open(encoding="utf-8") as users_file:
        return json.load(users_file)


def verify_password(password, user):
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(user["salt"]),
        user["iterations"],
    ).hex()
    return secrets.compare_digest(password_hash, user["password_hash"])


def record_audit_event(actor, action, capability_name, email):
    audit_log.append({
        "actor": actor,
        "action": action,
        "capability": capability_name,
        "email": email,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.removeprefix("Bearer ").strip()
    session = sessions.get(token)
    if not session or session["expires_at"] <= datetime.now(timezone.utc):
        sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return session["user"]


def require_practice_lead(user=Depends(get_current_user)):
    if user["role"] != "practice_lead":
        raise HTTPException(status_code=403, detail="Practice lead permission required")
    return user


@app.post("/auth/login")
def login(credentials: LoginRequest):
    user = next((item for item in load_users() if item["username"] == credentials.username), None)
    if not user or not verify_password(credentials.password, user):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "user": {"username": user["username"], "role": user["role"]},
        "expires_at": datetime.now(timezone.utc) + SESSION_DURATION,
    }
    return {"access_token": token, "token_type": "bearer", "user": sessions[token]["user"]}


@app.post("/auth/logout")
def logout(user=Depends(get_current_user), authorization: Annotated[str | None, Header()] = None):
    token = authorization.removeprefix("Bearer ").strip()
    sessions.pop(token, None)
    return {"message": f"Logged out {user['username']}"}


@app.get("/auth/me")
def current_user(user=Depends(get_current_user)):
    return user


@app.get("/audit-log")
def get_audit_log(user=Depends(require_practice_lead)):
    return audit_log


@app.get("/registrations/pending")
def get_pending_registrations(user=Depends(require_practice_lead)):
    return pending_registrations


@app.post("/registrations/pending/{request_index}/approve")
def approve_registration(request_index: int, user=Depends(require_practice_lead)):
    if request_index < 0 or request_index >= len(pending_registrations):
        raise HTTPException(status_code=404, detail="Registration request not found")

    request = pending_registrations.pop(request_index)
    capability = capabilities[request["capability"]]
    if request["email"] not in capability["consultants"]:
        capability["consultants"].append(request["email"])
    record_audit_event(user["username"], "approve_registration", request["capability"], request["email"])
    return {"message": f"Approved {request['email']} for {request['capability']}"}

# In-memory capabilities database
capabilities = {
    "Cloud Architecture": {
        "description": "Design and implement scalable cloud solutions using AWS, Azure, and GCP",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["AWS Solutions Architect", "Azure Architect Expert"],
        "industry_verticals": ["Healthcare", "Financial Services", "Retail"],
        "capacity": 40,  # hours per week available across team
        "consultants": ["alice.smith@slalom.com", "bob.johnson@slalom.com"]
    },
    "Data Analytics": {
        "description": "Advanced data analysis, visualization, and machine learning solutions",
        "practice_area": "Technology", 
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Tableau Desktop Specialist", "Power BI Expert", "Google Analytics"],
        "industry_verticals": ["Retail", "Healthcare", "Manufacturing"],
        "capacity": 35,
        "consultants": ["emma.davis@slalom.com", "sophia.wilson@slalom.com"]
    },
    "DevOps Engineering": {
        "description": "CI/CD pipeline design, infrastructure automation, and containerization",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"], 
        "certifications": ["Docker Certified Associate", "Kubernetes Admin", "Jenkins Certified"],
        "industry_verticals": ["Technology", "Financial Services"],
        "capacity": 30,
        "consultants": ["john.brown@slalom.com", "olivia.taylor@slalom.com"]
    },
    "Digital Strategy": {
        "description": "Digital transformation planning and strategic technology roadmaps",
        "practice_area": "Strategy",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Digital Transformation Certificate", "Agile Certified Practitioner"],
        "industry_verticals": ["Healthcare", "Financial Services", "Government"],
        "capacity": 25,
        "consultants": ["liam.anderson@slalom.com", "noah.martinez@slalom.com"]
    },
    "Change Management": {
        "description": "Organizational change leadership and adoption strategies",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Prosci Certified", "Lean Six Sigma Black Belt"],
        "industry_verticals": ["Healthcare", "Manufacturing", "Government"],
        "capacity": 20,
        "consultants": ["ava.garcia@slalom.com", "mia.rodriguez@slalom.com"]
    },
    "UX/UI Design": {
        "description": "User experience design and digital product innovation",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Adobe Certified Expert", "Google UX Design Certificate"],
        "industry_verticals": ["Retail", "Healthcare", "Technology"],
        "capacity": 30,
        "consultants": ["amelia.lee@slalom.com", "harper.white@slalom.com"]
    },
    "Cybersecurity": {
        "description": "Information security strategy, risk assessment, and compliance",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["CISSP", "CISM", "CompTIA Security+"],
        "industry_verticals": ["Financial Services", "Healthcare", "Government"],
        "capacity": 25,
        "consultants": ["ella.clark@slalom.com", "scarlett.lewis@slalom.com"]
    },
    "Business Intelligence": {
        "description": "Enterprise reporting, data warehousing, and business analytics",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Microsoft BI Certification", "Qlik Sense Certified"],
        "industry_verticals": ["Retail", "Manufacturing", "Financial Services"],
        "capacity": 35,
        "consultants": ["james.walker@slalom.com", "benjamin.hall@slalom.com"]
    },
    "Agile Coaching": {
        "description": "Agile transformation and team coaching for scaled delivery",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Certified Scrum Master", "SAFe Agilist", "ICAgile Certified"],
        "industry_verticals": ["Technology", "Financial Services", "Healthcare"],
        "capacity": 20,
        "consultants": ["charlotte.young@slalom.com", "henry.king@slalom.com"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/capabilities")
def get_capabilities():
    return capabilities


@app.post("/capabilities/{capability_name}/register")
def register_for_capability(capability_name: str, email: str, user=Depends(get_current_user)):
    """Register a consultant for a capability"""
    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get the specific capability
    capability = capabilities[capability_name]

    # Validate consultant is not already registered
    if email in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is already registered for this capability"
        )

    if user["role"] == "consultant":
        pending_registrations.append({
            "capability": capability_name,
            "email": email,
            "requested_by": user["username"],
        })
        record_audit_event(user["username"], "request_registration", capability_name, email)
        return {"message": f"Registration request submitted for {email} to {capability_name}", "status": "pending"}

    capability["consultants"].append(email)
    record_audit_event(user["username"], "register", capability_name, email)
    return {"message": f"Registered {email} for {capability_name}", "status": "approved"}


@app.delete("/capabilities/{capability_name}/unregister")
def unregister_from_capability(capability_name: str, email: str, user=Depends(require_practice_lead)):
    """Unregister a consultant from a capability"""
    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get the specific capability
    capability = capabilities[capability_name]

    # Validate consultant is registered
    if email not in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is not registered for this capability"
        )

    # Remove consultant
    capability["consultants"].remove(email)
    record_audit_event(user["username"], "unregister", capability_name, email)
    return {"message": f"Unregistered {email} from {capability_name}"}
