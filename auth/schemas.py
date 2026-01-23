from pydantic import BaseModel , EmailStr , field_validator , Field


class UserCreate(BaseModel):
    email : EmailStr
    password : str = Field(min_length=8,max_length=64)

    @field_validator("password")
    @classmethod

    def password_length(cls , v):
        if len(v.encode("UTF-8")) > 72:
            raise ValueError("Password too long (max 72 bytes)")
        if len(v) < 8 :
            raise ValueError("password too short (min 8 chars)")
        return v 


class UserResponse(BaseModel):
    id : int
    email : EmailStr

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email : EmailStr
    password : str

class ForgotPasswordRequest(BaseModel):
    email : EmailStr

class ResetPasswordRequest(BaseModel):
    token : str
    new_password : str
    


