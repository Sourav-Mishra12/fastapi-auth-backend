import os 
from dotenv import load_dotenv
from sqlalchemy import create_engine # making the engine 
from sqlalchemy.orm import sessionmaker

load_dotenv()   # loading the DATABASE_URL 

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL) # creating the engine 

sessionLocal = sessionmaker(     # making the session 
    autocommit = False,
    autoflush= False,
    bind=engine 
)


def get_db():
   db = sessionLocal()

   try :
      yield db

   finally :
      db.close()
