"""Pydantic schemas for authentication request and response models."""

from pydantic import BaseModel, ConfigDict


class SignupRequest(BaseModel):
    """Request schema for user registration."""

    email: str
    password: str


class LoginRequest(BaseModel):
    """Request schema for user authentication."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Response schema containing JWT access token."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response schema exposing authenticated user details."""

    id: str
    email: str
    gmail_connected: bool
    gmail_send_scope_granted: bool

    model_config = ConfigDict(from_attributes=True)
