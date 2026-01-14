from passlib.context import CryptContext
import os
from jose import JWTError , jwt 
from dotenv import load_dotenv
from datetime import datetime , timedelta , timedelta , timezone
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends , HTTPException , status
from sqlalchemy.orm import Session
from database import get_db
from auth.models import User
import secrets



load_dotenv()

# password storing and hashing

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(password : str) -> str:
     return pwd_context.hash(password)

def verify_password(plain_password : str , hashed_password : str) -> bool:
     return pwd_context.verify(plain_password , hashed_password)




# JWT 

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


# function for creating token

def create_access_token(data:dict):  # access token creation
     to_encode = data.copy()

     expire = datetime.now(timezone.utc) + timedelta(
          minutes = ACCESS_TOKEN_EXPIRE_MINUTES
     )

     to_encode.update({"exp":expire})

     encoded_jwt = jwt.encode(
          to_encode,
          SECRET_KEY,
          algorithm=ALGORITHM
     )

     return encoded_jwt



# getting the current user 

#token extractor
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
          token : str =  Depends(oauth2_scheme) ,
          db : Session = Depends(get_db)
          ):
     

     try : 
          payload = jwt.decode(
               token,
               SECRET_KEY,
               algorithms=[ALGORITHM]
          )
     
     except JWTError :
          raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail = "Could not validate credentials"
          )
     

     user_id = payload.get("user_id")

     if user_id is None :
          raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Could not validate credentials "
          )
     

     user = db.query(User).filter(User.id == user_id).first()

     if user is None:
          raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail= "Could not validate credentials"
          )
     
     return user 


# creating the function to create and secure the refresh token

def generate_refresh_token() -> str:
     return secrets.token_urlsafe(64)    # generating the refresh token


def hash_refresh_token(token : str) -> str:
     return pwd_context.hash(token)    # hashing the token for safety


def verify_refresh_token(token :str , hash_token : str) -> bool:
     return pwd_context.verify(token , hash_token)  # verifying the token and the hashed token

def get_refresh_token_expiry(days : int = 7):
     return datetime.now(timezone.utc) + timedelta(days=days) # checking the expiry time



def create_refresh_token_pair() -> dict:
     
     refresh_token = secrets.token_urlsafe(64)

     hashed_refresh_token = pwd_context.hash(refresh_token)

     expiry_date = datetime.now(timezone.utc) + timedelta(days=7)

     return {
          "refresh_token" : refresh_token,
          "token_hash" : hashed_refresh_token,
          "expires_at" : expiry_date,
     }