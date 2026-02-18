from sqlalchemy.ext.declarative import declarative_base  # this is used to convert python classes into DB tables
from sqlalchemy import Column , Integer , Float , String  # this is for making columns and their dtypes



Base = declarative_base()

class Product(Base):

    __tablename__ = "product"   # this is for table name

    id = Column(Integer , primary_key=True , index=True)
    name = Column(String)
    description = Column(String)
    price = Column(Float)
    quantity = Column(Integer)


class AIUser(Base):

    __tablename__ = "ai_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    api_key = Column(String, unique=True, index=True)
    usage_count = Column(Integer, default=0)
    last_reset = Column(String)
    plan = Column(String, default="free")
