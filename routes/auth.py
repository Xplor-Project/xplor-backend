from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse

from core.database import users_collection
from core.config import settings
from models.user_model import UserCreate, UserInDB, Token, TokenData, UserBase
from models.otp_model import OTPVerify
from utils.security import get_password_hash, verify_password, create_access_token, generate_otp
from utils.email import send_verification_email

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

@router.post("/register")
async def register(user: UserCreate):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    verification_otp = generate_otp()
    
    user_dict = UserInDB(
        **user.model_dump(), # Pydantic V2 syntax
        hashed_password=hashed_password,
        provider="email",
        verification_otp=verification_otp,
        is_verified=False
    ).model_dump()
    
    users_collection.insert_one(user_dict)
    await send_verification_email(user.email, verification_otp)
    
    return {"message": "OTP sent to email. Please verify."}

@router.get("/google")
async def login_google(request: Request):
    # This automatically creates a 'state' and saves it in the session cookie
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_google(request: Request):
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
    return {"access_token": access_token, "token_type": "bearer"}