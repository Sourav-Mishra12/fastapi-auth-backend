from fastapi import APIRouter , Depends , status , HTTPException
from sqlalchemy.orm import Session
from datetime import datetime , timezone , timedelta
from database import get_db
from auth.schemas import UserResponse , UserCreate , ForgotPasswordRequest , ResetPasswordRequest
from auth.models import User , RefreshToken , PasswordResetToken
from auth.utils import hash_password , verify_password , create_access_token , get_current_user , generate_refresh_token , hash_refresh_token , get_refresh_token_expiry , verify_refresh_token , create_refresh_token_pair
import secrets
from auth.schemas import UserLogin
from core.logger import logger
from core.email import send_reset_password_email
import os 



router = APIRouter(prefix="/auth" , tags=["Auth"])

@router.post("/register" , response_model=UserResponse)
def register(user : UserCreate , db : Session = Depends(get_db)):

    logger.info(f"Registration attempt for email={user.email}")

    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        logger.warning(f"Registration failed: email already exists email={user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    new_user = User(
        email = user.email,
        hashed_password = hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User registered successfully user_id={new_user.id}")
    return new_user


@router.post("/login")
def userlogin(user: UserLogin, db: Session = Depends(get_db)):

    logger.info(f"Login attempt for email={user.email}")

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        logger.warning(f"Login failed: user not found email={user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if db_user.lock_until and db_user.lock_until > datetime.now(timezone.utc):
        logger.warning(f"Login blocked: account locked user_id={db_user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(user.password, db_user.hashed_password):
        logger.warning(f"Login failed: invalid password user_id={db_user.id}")

        db_user.failed_login_attempts += 1
        db_user.last_failed_login = datetime.now(timezone.utc)

        if db_user.failed_login_attempts >= 5:
            db_user.lock_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            logger.warning(f"Account locked due to brute force user_id={db_user.id}")

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    db_user.failed_login_attempts = 0
    db_user.lock_until = None
    db_user.last_failed_login = None
    db.commit()

    payload = {"user_id": db_user.id}
    access_token = create_access_token(payload)

    refresh_token = generate_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)

    db_refresh_token = RefreshToken(
        user_id=db_user.id,
        token_hash=refresh_token_hash,
        expires_at=get_refresh_token_expiry(days=7),
        revoked=False
    )

    db.add(db_refresh_token)
    db.commit()

    logger.info(f"Login successful user_id={db_user.id}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }



@router.get("/me" , response_model=UserResponse)

def get_me(current_user = Depends(get_current_user)):
    return current_user 



@router.post("/logout")

def logout(current_user = Depends(get_current_user)):
    return{
        "message" : "logged out successfully"
    }




@router.post("/refresh")
def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    logger.info("Refresh token attempt received")

    db_tokens = db.query(RefreshToken).filter(
        RefreshToken.expires_at > datetime.now(timezone.utc)
    ).all()

    matched_token = None

    for token in db_tokens:
        if verify_refresh_token(refresh_token, token.token_hash):
            matched_token = token
            break

    if not matched_token:
        logger.warning("Invalid refresh token used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    if matched_token.revoked:
        logger.error(f"Refresh token reuse detected user_id={matched_token.user_id}")

        db.query(RefreshToken).filter(
            RefreshToken.user_id == matched_token.user_id
        ).update({RefreshToken.revoked: True})

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session compromised. Please login again."
        )

    matched_token.revoked = True
    db.commit()

    new_refresh_token_data = create_refresh_token_pair()

    new_db_refresh_token = RefreshToken(
        user_id=matched_token.user_id,
        token_hash=new_refresh_token_data["token_hash"],
        expires_at=new_refresh_token_data["expires_at"],
        revoked=False
    )

    db.add(new_db_refresh_token)
    db.commit()

    new_access_token = create_access_token(
        payload={"user_id": matched_token.user_id}
    )

    logger.info(f"Refresh token rotated user_id={matched_token.user_id}")

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token_data["refresh_token"],
        "token_type": "bearer"
    }



@router.post("/forgot-password")
def forgot_password(
    data : ForgotPasswordRequest ,
    db : Session = Depends(get_db)):

    logger.info(f"Password reset requested for email={data.email}")

    user = db.query(User).filter(User.email == data.email).first()

    if user:
        reset_token = secrets.token_urlsafe(64)
        reset_token_hash = hash_refresh_token(reset_token)

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        db_token = PasswordResetToken(
            user_id = user.id,
            token_hash = reset_token_hash,
            expires_at=expires_at,
            used=False
        )

        db.add(db_token)
        db.commit()

        logger.info(f"Password reset token issued user_id={user.id}")

        reset_link= f"{os.getenv('FRONTEND_URL')}/reset-password?token={reset_token}"

        send_reset_password_email(user.email , reset_link)

    return {
        "message" : "If the email exists , you will receive a password reset link"
    }



@router.post("/reset-paasword")
def reset_password(
    data : ResetPasswordRequest,
    db : Session = Depends(get_db)
):

    tokens = db.query(PasswordResetToken).filter(
        PasswordResetToken.expires_at > datetime.now(timezone.utc),
        PasswordResetToken.used == False
    ).all()

    matched_token = None

    for token in tokens:
        if verify_refresh_token(data.token , token.token_hash):
            matched_token = token
            break

    if not matched_token:
        logger.warning("Invalid or expired password reset token used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token"
        )

    user = db.query(User).filter(user.id == matched_token.user_id).first()

    if not user:
        logger.error("Password reset failed: user not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reset request"
        )

    user.hashed_password = hash_password(data.new_password)
    matched_token.used = True

    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id
    ).update({RefreshToken.revoked : True})

    db.commit()

    logger.info(f"Password reset successful user_id={user.id}")

    return {
        "message" : "Password reset successful. Please login again"
    }
