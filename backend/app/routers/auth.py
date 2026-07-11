from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from app.database import get_supabase
from supabase import Client

router = APIRouter()

class UserAuthSchema(BaseModel):
    email: EmailStr
    password: str

class AuthResponseSchema(BaseModel):
    user_id: str
    email: str
    access_token: str
    refresh_token: str

class UserProfileSchema(BaseModel):
    id: str
    email: str
    created_at: str

def get_token_header(authorization: str = Header(None)) -> str:
    """Helper dependency to extract authorization token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
        return token
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Use 'Bearer <token>'"
        )

@router.post("/signup", response_model=AuthResponseSchema, status_code=status.HTTP_201_CREATED)
async def sign_up(user_data: UserAuthSchema, db: Client = Depends(get_supabase)):
    try:
        response = db.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed. Email may already be in use or password too weak."
            )
        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/signin", response_model=AuthResponseSchema)
async def sign_in(user_data: UserAuthSchema, db: Client = Depends(get_supabase)):
    try:
        response = db.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.get("/me", response_model=UserProfileSchema)
async def get_me(token: str = Depends(get_token_header), db: Client = Depends(get_supabase)):
    try:
        # Validate current user token using supabase auth API
        user_response = db.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )
        user = user_response.user
        return {
            "id": user.id,
            "email": user.email or "",
            "created_at": str(user.created_at)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/signout")
async def sign_out(token: str = Depends(get_token_header), db: Client = Depends(get_supabase)):
    try:
        # Sign out globally or invalidate session
        # Supabase Python client's sign_out relies on the current client session,
        # but in stateless API routes, we can just sign out using the client or let the client do it.
        # Alternatively, Supabase API manages session sign_out.
        db.auth.sign_out()
        return {"message": "Successfully signed out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
