#Importaciones:
import sys
sys.tracebacklimit = 1
from fastapi import FastAPI
from routes.user import user
from routes.career import career
from routes.payment import payment
from routes.notification import notification
from fastapi.middleware.cors import CORSMiddleware

# Creamos la aplicación FastAPI:
api_escu = FastAPI()

# Incorporamos las rutas importadas:
api_escu.include_router(user)
api_escu.include_router(career)
api_escu.include_router(payment)
api_escu.include_router(notification)
# Agregamos middleware de CORS para permitir conexión desde frontend:
api_escu.add_middleware(
    CORSMiddleware, # es el tipo de middleware a agregar
    allow_origins=["*"], # Parámetro q define acceso para conexión de FrontEnd (temporalmente)
    allow_credentials=True, # Permitimos el uso de cookies,etc
    allow_methods=["*"], # Permitimos todos los métodos HTTP
    allow_headers=["*"], # Permitimos cualquier encabezado (ej: Authorization)
)


# uvicorn app:api_escu --reload 