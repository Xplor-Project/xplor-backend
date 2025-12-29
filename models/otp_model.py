from pydantic import BaseModel, EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
