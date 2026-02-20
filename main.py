from fastapi import FastAPI, HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from database import sessionLocal, engine, get_db
import database_models
from models import ProductCreate, ProductResponse

from auth.routes import router as auth_router
from auth.utils import get_current_user
from core.logger import logger

# -------------------------------
# NEW IMPORTS (AI + RATE LIMIT)
# -------------------------------
from ai_routes import router as ai_router
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# -------------------------------
# App Setup
# -------------------------------
app = FastAPI()

# middleware 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# -------------------------------
# Rate Limiter Setup
# -------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Slow down."},
    )


# -------------------------------
# Routers
# -------------------------------
app.include_router(auth_router)
app.include_router(ai_router)  # NEW AI ROUTER


@app.get("/")
def health():
    return {"status": "ok"}


# -------------------------------
# Startup
# -------------------------------
@app.on_event("startup")
def startup():
    logger.info("Application startup initiated")

    try:
        database_models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured successfully")
    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise

    logger.info("Application startup completed")


# -------------------------------
# Product Routes (UNCHANGED)
# -------------------------------
@app.get("/products", response_model=list[ProductResponse])
def get_all_products(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    logger.info(f"Products fetched by user_id={current_user.id}")
    return db.query(database_models.Product).all()


@app.get("/product/{id}", response_model=ProductResponse)
def get_product_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    product = db.query(database_models.Product).filter(
        database_models.Product.id == id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    logger.info(f"Product {id} fetched by user_id={current_user.id}")
    return product


@app.post(
    "/product",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductResponse
)
def add_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    db_product = database_models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    logger.info(f"Product created by user_id={current_user.id}")
    return db_product


@app.put("/product/{id}", response_model=ProductResponse)
def update_product(
    id: int,
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    db_product = db.query(database_models.Product).filter(
        database_models.Product.id == id
    ).first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db_product.quantity = product.quantity

    db.commit()
    db.refresh(db_product)

    logger.info(f"Product {id} updated by user_id={current_user.id}")
    return db_product


@app.delete("/product/{id}")
def delete_product(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    db_product = db.query(database_models.Product).filter(
        database_models.Product.id == id
    ).first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()

    logger.warning(f"Product {id} deleted by user_id={current_user.id}")
    return {"message": "deleted successfully"}
