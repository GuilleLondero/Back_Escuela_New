import datetime, pytz, jwt
from fastapi.responses import JSONResponse

class Security:
    secret = "cualqueira coso"

    @classmethod
    def hoy(cls):
        return datetime.datetime.now(pytz.timezone("America/Buenos_Aires"))

    @classmethod
    def generate_token(cls, authUser):
        payload = {
            "iat": cls.hoy(),
            "exp": cls.hoy() + datetime.timedelta(minutes=480),
            "username": authUser.username
        }
        try:
            return jwt.encode(payload, cls.secret, algorithm="HS256")
        except Exception as e:
            print("ERROR en generate_token:", e)
            return None
    
    @classmethod
    def verify_token(cls, headers):
        if headers["authorization"]:
            tkn = headers["authorization"].split(" ")[1]
            try:
                payload = jwt.decode(tkn, cls.secret, algorithms=["HS256"])
                return payload
            except jwt.ExpiredSignatureError:
                return {"success": False, "message": "Token expirado!"}
            except jwt.InvalidSignatureError:
                return {"success": False, "message": "Error de firma invalida!"}
            except jwt.DecodeError as e:
                return {"success": False, "message": "Error de codificacion!"}
            except Exception as e:
                return {"success": False, "message": "Error desconocido al validar!"}
        else:
            return JSONResponse(
            status_code=401,
            content={"message": "Usuario o contraseña inválida"}
        )
