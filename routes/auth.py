from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse

from core.database import users_collection, check_db_connection
from core.config import settings
from models.user_model import (
    UserCreate, UserInDB, Token, TokenData, UserBase, 
    PasswordResetRequest, PasswordResetConfirm
)
from models.otp_model import OTPVerify
from utils.security import get_password_hash, verify_password, create_access_token, generate_otp
from utils.email import send_verification_email, send_reset_password_email

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# OAuth Setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    check_db_connection()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = users_collection.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception
    
    # Map _id to id if necessary for your UserBase model
    user["id"] = str(user["_id"])
    return UserBase(**user)

@router.post("/register", response_model=dict)
async def register(user: UserCreate):
    check_db_connection()
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    verification_otp = generate_otp()
    
    # Exclude fields that are set by the server to prevent duplicates/overwrites
    user_data = user.model_dump(exclude={"is_verified", "is_superuser"})
    
    user_dict = UserInDB(
        **user_data,
        hashed_password=hashed_password,
        provider="email",
        verification_otp=verification_otp,
        is_verified=False
    ).model_dump()
    
    users_collection.insert_one(user_dict)
    await send_verification_email(user.email, verification_otp)
    
    return {"message": "OTP sent to email. Please verify."}

@router.post("/verify-email", response_model=dict)
async def verify_email(data: OTPVerify):
    check_db_connection()
    user = users_collection.find_one({"email": data.email})
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
        
    if user.get("is_verified"):
        return {"message": "Email already verified"}
        
    if user.get("verification_otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    users_collection.update_one(
        {"email": data.email},
        {"$set": {"is_verified": True, "verification_otp": None}}
    )
    
    return {"message": "Email verified successfully. You can now login."}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    check_db_connection()
    # OAuth2PasswordRequestForm uses 'username' for the email field by default
    user = users_collection.find_one({"email": form_data.username})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user.get("provider") == "google":
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please login with Google",
        )

    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.get("is_verified", False):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please verify your email first.",
        )

    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password", response_model=dict)
async def forgot_password(request: PasswordResetRequest):
    check_db_connection()
    user = users_collection.find_one({"email": request.email})
    if not user:
        # Don't reveal that the user doesn't exist, just pretend to send
        # or raise 404 if less security sensitive. Standard practice is often to return success.
        # But for this sample, I'll return 404 for clarity or just success.
        # Let's return 404 for debugging ease, or success for security.
        # I'll choose specific error for this dev context.
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("provider") == "google":
        raise HTTPException(status_code=400, detail="Please login with Google. Cannot reset password for OAuth accounts.")

    reset_otp = generate_otp()
    users_collection.update_one(
        {"email": request.email},
        {"$set": {"reset_otp": reset_otp}}
    )
    
    await send_reset_password_email(request.email, reset_otp)
    
    return {"message": "Password reset OTP sent to email"}

@router.post("/reset-password", response_model=dict)
async def reset_password(data: PasswordResetConfirm):
    check_db_connection()
    user = users_collection.find_one({"email": data.email})
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
         
    if user.get("reset_otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    hashed_password = get_password_hash(data.new_password)
    
    users_collection.update_one(
        {"email": data.email},
        {"$set": {"hashed_password": hashed_password, "reset_otp": None}}
    )
    
    return {"message": "Password reset successfully. You can now login."}

@router.get("/google")
async def login_google(request: Request):
    # This automatically creates a 'state' and saves it in the session cookie
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_google(request: Request, response: Response):
    check_db_connection()
    try:
        # This looks for the 'state' in the session cookie to compare
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
             user_info = await oauth.google.userinfo(token=token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth Logic Error: {str(e)}")

    email = user_info.get("email")
    user = users_collection.find_one({"email": email})

    if not user:
        new_user = UserInDB(
            email=email,
            full_name=user_info.get("name"),
            hashed_password="", 
            provider="google",
            is_verified=True 
        ).model_dump()
        users_collection.insert_one(new_user)
    
    access_token = create_access_token(data={"sub": email})
    
    # Example of setting a cookie if desired
    # response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserBase)
async def read_users_me(current_user: UserBase = Depends(get_current_user)):
    return current_user
