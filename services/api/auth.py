import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Annotated
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from tinydb import Query, TinyDB


ROOT = Path(__file__).resolve().parents[2]
auth_lock = Lock()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
public_router = APIRouter()
users_router = APIRouter(prefix="/users", tags=["Users"])
profiles_router = APIRouter(prefix="/profiles", tags=["Profiles"])
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    user = "user"


class ProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    address: str = Field(default="", max_length=500)


class Profile(ProfileFields):
    id: str
    user_id: str


class UserRead(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    role: Role
    created_at: datetime


class User(UserRead):
    hashed_password: str = Field(exclude=True)


class PasswordFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return value


class UserCreate(PasswordFields, ProfileFields):
    email: EmailStr
    role: Role = Role.user

    @field_validator("role")
    @classmethod
    def registration_role(cls, value: Role) -> Role:
        if value != Role.user:
            raise ValueError("Registration may only create the user role.")
        return value


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr | None = None
    password: str | None = None
    role: Role | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is not None:
            return PasswordFields(password=value).password
        return value

    @field_validator("email", "password", "role", "is_active")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Update fields cannot be null; omit unchanged fields.")
        return value


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    address: str = Field(default="", max_length=500)


class CurrentUserRead(UserRead):
    profile: Profile


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


def open_auth_database() -> TinyDB:
    path = Path(os.environ.get("AUTH_DB_PATH", str(ROOT / "data" / "auth.json")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    return TinyDB(path)


def configure_auth(app) -> None:
    load_dotenv(ROOT / ".env")
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("Set JWT_SECRET_KEY to a random secret of at least 32 bytes in .env.")
    expiry = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    if expiry <= 0:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive.")
    app.state.jwt_secret = secret
    app.state.token_expiry = expiry


def get_auth_database(request: Request):
    with auth_lock:
        yield request.app.state.auth_db


Database = Annotated[TinyDB, Depends(get_auth_database)]
BearerToken = Annotated[str | None, Depends(oauth2_scheme)]


def find_user(database: TinyDB, user_id: str) -> User:
    record = database.table("users").get(Query().id == user_id)
    if record is None:
        raise HTTPException(404, "User not found.")
    return User(**record)


def find_profile(database: TinyDB, user_id: str) -> Profile:
    record = database.table("profiles").get(Query().user_id == user_id)
    if record is None:
        raise HTTPException(404, "Profile not found.")
    return Profile(**record)


def unauthorized() -> HTTPException:
    return HTTPException(401, "Invalid or missing access token.", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(request: Request, database: Database, token: BearerToken) -> User:
    if not token:
        raise unauthorized()
    try:
        payload = jwt.decode(
            token, request.app.state.jwt_secret, algorithms=["HS256"],
            options={"require_exp": True, "require_sub": True, "require_iat": True},
        )
        user_id = payload["sub"]
        if not isinstance(user_id, str) or payload.get("user_id") != user_id:
            raise unauthorized()
        user = find_user(database, user_id)
    except (JWTError, KeyError, ValueError, TypeError, HTTPException) as error:
        raise unauthorized() from error
    if not user.is_active:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_authentication(request: Request, database: Database, token: BearerToken):
    if (request.method, request.url.path) in {("POST", "/users"), ("POST", "/auth/login")}:
        return
    get_current_user(request, database, token)


def require_owner_or_admin(current: User, user_id: str) -> None:
    if current.id != user_id and current.role != Role.admin:
        raise HTTPException(403, "You may only access your own user account.")


def ensure_unique_email(database: TinyDB, email: str, user_id: str | None = None) -> None:
    existing = database.table("users").get(Query().email == email)
    if existing is not None and existing["id"] != user_id:
        raise HTTPException(409, "Email is already registered.")


def create_user(database: TinyDB, payload: UserCreate) -> User:
    email = str(payload.email).lower()
    ensure_unique_email(database, email)
    user_id = uuid4().hex
    record = {
        "id": user_id, "email": email, "hashed_password": bcrypt.hash(payload.password),
        "is_active": True, "role": Role.user.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    profile = Profile(
        id=uuid4().hex, user_id=user_id,
        name=payload.name, phone=payload.phone, address=payload.address,
    )
    users = database.table("users")
    profiles = database.table("profiles")
    users.insert(record)
    try:
        profiles.insert(profile.model_dump())
    except Exception:
        users.remove(Query().id == user_id)
        profiles.remove(Query().user_id == user_id)
        raise
    return User(**record)


def update_user(database: TinyDB, user_id: str, payload: UserUpdate) -> User:
    find_user(database, user_id)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    if "email" in changes:
        changes["email"] = changes["email"].lower()
        ensure_unique_email(database, changes["email"], user_id)
    if "password" in changes:
        changes["hashed_password"] = bcrypt.hash(changes.pop("password"))
    database.table("users").update(changes, Query().id == user_id)
    return find_user(database, user_id)


def delete_user(database: TinyDB, user_id: str) -> None:
    find_user(database, user_id)
    database.table("users").remove(Query().id == user_id)
    database.table("profiles").remove(Query().user_id == user_id)


@public_router.post("/users", response_model=UserRead, status_code=201, tags=["Users"])
def register(payload: UserCreate, database: Database):
    return create_user(database, payload)


@public_router.post(
    "/auth/login", response_model=Token, tags=["Authentication"],
    openapi_extra={"requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": {
                "type": "object", "required": ["email", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string", "format": "password"},
                },
            }},
            "application/x-www-form-urlencoded": {"schema": {
                "type": "object", "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string", "description": "Email address"},
                    "password": {"type": "string", "format": "password"},
                },
            }},
        },
    }},
)
async def login(request: Request, database: Database):
    content_type = request.headers.get("content-type", "").split(";")[0].lower()
    if content_type == "application/json":
        try:
            payload = await request.json()
        except ValueError as error:
            raise HTTPException(422, "Invalid JSON.") from error
        if not isinstance(payload, dict):
            raise HTTPException(422, "Provide email and password.")
        email, password = payload.get("email"), payload.get("password")
    else:
        form = await request.form()
        email, password = form.get("username", form.get("email")), form.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        raise HTTPException(422, "Provide email and password.")
    record = database.table("users").get(Query().email == email.lower())
    valid_length = 0 < len(password.encode("utf-8")) <= 72
    if record is None or not valid_length or not bcrypt.verify(password, record["hashed_password"]):
        raise unauthorized()
    user = User(**record)
    if not user.is_active:
        raise unauthorized()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user.id, "user_id": user.id, "iat": now,
         "exp": now + timedelta(minutes=request.app.state.token_expiry)},
        request.app.state.jwt_secret, algorithm="HS256",
    )
    return Token(access_token=token)


@users_router.get("", response_model=list[UserRead])
def list_users(current: CurrentUser, database: Database):
    if current.role != Role.admin:
        raise HTTPException(403, "Only admins may list users.")
    return database.table("users").all()


@users_router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: str, current: CurrentUser, database: Database):
    require_owner_or_admin(current, user_id)
    return find_user(database, user_id)


@users_router.put("/{user_id}", response_model=UserRead)
def edit_user(user_id: str, payload: UserUpdate, current: CurrentUser, database: Database):
    require_owner_or_admin(current, user_id)
    if {"role", "is_active"} & payload.model_fields_set and current.role != Role.admin:
        raise HTTPException(403, "Only admins may change roles or account activation.")
    return update_user(database, user_id, payload)


@users_router.delete("/{user_id}", status_code=204)
def remove_user(user_id: str, current: CurrentUser, database: Database):
    require_owner_or_admin(current, user_id)
    delete_user(database, user_id)


@profiles_router.get("/me", response_model=Profile)
def read_profile(current: CurrentUser, database: Database):
    return find_profile(database, current.id)


@profiles_router.put("/me", response_model=Profile)
def edit_profile(payload: ProfileUpdate, current: CurrentUser, database: Database):
    find_profile(database, current.id)
    database.table("profiles").update(payload.model_dump(exclude_unset=True), Query().user_id == current.id)
    return find_profile(database, current.id)


@auth_router.get("/me", response_model=CurrentUserRead)
def auth_me(current: CurrentUser, database: Database):
    return {**current.model_dump(), "profile": find_profile(database, current.id)}