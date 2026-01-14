from sqlalchemy import Column , Integer , String , Float , ForeignKey , Boolean , DateTime
from sqlalchemy.sql import func 
from database_models import Base

# creating the users table and columns 

class User(Base):

    __tablename__ = "users"

    id = Column(Integer , primary_key=True , index=True)
    email = Column(String , unique=True , index=True , nullable=False)
    hashed_password = Column(String,nullable=False)
    failed_login_attempts = Column(Integer , default=0)
    lock_until = Column(DateTime(timezone=True) , nullable=True)
    last_failed_login = Column(DateTime(timezone=True) , nullable=True)


# creating the table to store refresh tokens


class RefreshToken(Base):

    __tablename__ = "refresh_tokens"

    id = Column(Integer , primary_key=True , index=True)
    user_id = Column(Integer,ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    token_hash = Column(String , nullable=False , unique=True)
    experies_at = Column(DateTime , nullable=False)
    revoked = Column(Boolean , default=False)

    created_by = Column(DateTime(timezone=True) , server_default=func.now())


# model schema for 'forgot password' functionality

class PasswordResetToken(Base):

    __tablename__ = "password_reset_tokens"

    id = Column(Integer , primary_key=True , index=True)
    user_id = Column(Integer , ForeignKey("users.id"), nullable=False)
    token_hash = Column(String , nullable=False , index=True)
    expires_at = Column(DateTime(timezone=True) ,  nullable=False)
    used = Column(Boolean , default=False , nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now() , nullable=False)