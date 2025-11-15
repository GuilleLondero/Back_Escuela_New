from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from models.modelo import session, User, UserDetail, PivoteUserCareer, InputUser, InputLogin, InputUserAddCareer
from sqlalchemy.orm import joinedload
from auth.security import Security


# Creamos router para agrupar las rutas relacionadas con usuarios:
user = APIRouter()

@user.get("/")
### Ruta de prueba para verificar si el módulo de usuarios está funcionando bien
def helloUser():
    return "Hello Usuario !!!!!"

@user.get("/users/all")
### Devuelve todos los usuarios registrados junto con sus detalles personales.
### Hacemos uso de 'joinedload' para evitar múltiples consultas a la DB
def getAllUsers(req: Request):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" in has_access:
            # Ejecutamos una consulta a la DB de todos los usuarios y sus detalles en una sola consulta
            usersConDetail = session.query(User).options(joinedload(User.userdetail)).all()
            
            # Lista de salida para almacenar los datos formateados
            usuarios_con_detalle = []

            for user in usersConDetail:
                user_con_detalle = {
                    "id": user.id,
                    "username": user.username,
                    "password": user.password,
                    "first_name": user.userdetail.first_name,
                    "last_name": user.userdetail.last_name,
                    "dni": user.userdetail.dni,
                    "type": user.userdetail.type,
                    "email": user.userdetail.email,
                }
                usuarios_con_detalle.append(user_con_detalle)
            return JSONResponse(status_code=200, content=usuarios_con_detalle)
        else:
            return JSONResponse(
           status_code=401,
           content=has_access,
       )
    except Exception as ex:
        print("Error ---->> ", ex)
        return {"message": "Error al obtener los usuarios"}
    

@user.post("/users/add")
### Creamos un nuevo usuario junto con su detalle personal.
def create_user(us: InputUser):
    try:
        newUser = User(us.username, us.password)
        newUserDetail = UserDetail(us.firstname, us.lastname, us.dni, us.type, us.email)
        newUser.userdetail = newUserDetail
        session.add(newUser)
        session.commit()
        return "Usuario creado con éxito!"
    except Exception as ex:
        session.rollback()
        print("Error ---->> ", ex)
    finally:
        session.close()
       
@user.post("/users/login") 
def login_post(userIn: InputLogin):
   try:
        # Buscamos al usuario por username:
        user = session.query(User).filter(User.username == userIn.username).first()
        
        # Verificamos que el usuario exista y que coincida la contraseña:
        if user and user.password == userIn.password:
            tkn = Security.generate_token(user) # Generamos token con los datos del usuario
            if not tkn:
                return JSONResponse(
                    status_code=500,
                    content={"message": "Error en la generación del token"}
                )
            # Preparamos respuesta c/datos user
            res = {
                "status": "success",
                "token": tkn,
                "user": {
                    "username": user.username,
                    "first_name": user.userdetail.first_name,
                    "last_name": user.userdetail.last_name,
                    "email": user.userdetail.email,
                    "type": user.userdetail.type
                },
                "message": "Usuario logueado con éxito"
            }
            print(res)
            return JSONResponse(status_code=200, content=res)
        else:
            return JSONResponse(
            status_code=401,
            content={"message": "Usuario o contraseña inválida"}
        )
   except Exception as ex:
       print("Error ---->>", ex)
   finally:
       session.close()

   
@user.post("/user/addcareer")
### Inscribe un usuario (alumno) a una carrera.
### Creamos una entrada en la tabla pivote entre User y Career.
def addCareer(ins: InputUserAddCareer):
    try: 
        newInsc = PivoteUserCareer(ins.id_user, ins.id_career)
        session.add(newInsc)
        session.commit()
        res = f"{newInsc.user.userdetail.first_name} {newInsc.user.userdetail.last_name} fue inscripto correctamente a {newInsc.career.name}"
        print(res)
        return res
    except Exception as ex:
        session.rollback()
        print("Error al inscribir al alumno:", ex)
        import traceback
        traceback.print_exc()    
    finally:
        session.close()

@user.get("/user/career/{_username}")
### Devuelve una lista de carreras en las que está inscripto un usuario específico.
### Buscamos al usuario por username y recorre sus relaciones de inscripción.
def get_career_user(_username: str):
    try:
        userEncontrado = session.query(User).filter(User.username == _username ).first()
        arraySalida = []
        if(userEncontrado):
            inscrip_user = userEncontrado.pivoteusercareer
            for inscripcion in inscrip_user:
                career_detail = {
                    "usuario": f"{inscripcion.user.userdetail.first_name} {inscripcion.user.userdetail.last_name}",
                    "carrera": inscripcion.career.name,
                }
                arraySalida.append(career_detail)
            return arraySalida
        else:
            return "Usuario no encontrado!"
    except Exception as ex:
        session.rollback()
        print("Error al traer usuario y/o pagos")
    finally:
        session.close()


@user.get("/users/alumnos")
def get_all_students():
    try:
        alumnos = session.query(User).all()
        salida = []
        for u in alumnos:
            if u.userdetail.type.lower() == "alumno":
                # Filtrar solo carreras activas
                carreras = [
                    p.career.name
                    for p in u.pivoteusercareer
                    if p.career and p.career.active
                ] if u.pivoteusercareer else []
                
                salida.append({
                    "id": u.id,
                    "username": u.username,
                    "nombre": u.userdetail.first_name,
                    "apellido": u.userdetail.last_name,
                    "email": u.userdetail.email,
                    "carreras": carreras
                })
        return salida
    except Exception as e:
        session.rollback()
        print("Error al traer alumnos:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno"})
    

#permite cambias contraseña de cada usuario
@user.post("/users/change-password")
def change_password(request: Request, data: dict):
    try:
        headers = request.headers
        payload = Security.verify_token(headers)

        if "iat" not in payload:
            return JSONResponse(status_code=401, content={"message": "Token inválido"})

        username = payload["username"]
        new_password = data.get("new_password")

        if not new_password:
            return JSONResponse(status_code=400, content={"message": "Nueva contraseña requerida"})

        user = session.query(User).filter(User.username == username).first()

        if user:
            user.password = new_password
            session.commit()
            return {"success": True, "message": "Contraseña actualizada correctamente"}
        else:
            return JSONResponse(status_code=404, content={"message": "Usuario no encontrado"})

    except Exception as e:
        session.rollback()
        print("Error al cambiar contraseña:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno del servidor"})
    



@user.put("/users/update")
def update_user_profile(request: Request, data: dict):
    try:
        payload = Security.verify_token(request.headers)

        if "iat" not in payload:
            return JSONResponse(status_code=401, content={"message": "Token inválido"})

        username = payload["username"]

        # Buscar el usuario
        user = session.query(User).filter(User.username == username).first()

        if not user:
            return JSONResponse(status_code=404, content={"message": "Usuario no encontrado"})

        # Actualizar datos del UserDetail
        user.userdetail.first_name = data.get("first_name", user.userdetail.first_name)
        user.userdetail.last_name = data.get("last_name", user.userdetail.last_name)
        user.userdetail.email = data.get("email", user.userdetail.email)
        #Si se mandó una nueva contraseña, también la actualizamos
        if "new_password" in data and data["new_password"]:
         user.password = data["new_password"]

        session.commit()

        return JSONResponse(status_code=200, content={"message": "Perfil actualizado correctamente."})
    except Exception as e:
        session.rollback()
        print("Error al actualizar perfil:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno al actualizar el perfil."})










@user.put("/users/reset-password/{username}")
def reset_password_admin(username: str, request: Request, data: dict):
    try:
        payload = Security.verify_token(request.headers)
        if "iat" not in payload:
            return JSONResponse(status_code=401, content={"message": "Token inválido"})

        new_password = data.get("new_password")
        if not new_password:
            return JSONResponse(status_code=400, content={"message": "Nueva contraseña requerida"})

        user = session.query(User).filter(User.username == username).first()
        if user:
            user.password = new_password
            session.commit()
            return {"success": True, "message": "Contraseña restablecida correctamente"}
        else:
            return JSONResponse(status_code=404, content={"message": "Usuario no encontrado"})

    except Exception as e:
        session.rollback()
        print("Error al restablecer contraseña:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno del servidor"})



@user.get("/users/{username}")
### Devuelve un usuario específico junto con sus detalles personales
def getUserByUsername(username: str, req: Request):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" in has_access:
            # Ejecutamos una consulta a la DB para obtener el usuario específico con sus detalles
            userWithDetail = session.query(User).options(joinedload(User.userdetail)).filter(User.username == username).first()
            
            if not userWithDetail:
                return JSONResponse(
                    status_code=404,
                    content={"message": "Usuario no encontrado"}
                )
            
            # Formatear los datos de salida
            user_data = {
                "id": userWithDetail.id,
                "username": userWithDetail.username,
                "first_name": userWithDetail.userdetail.first_name,
                "last_name": userWithDetail.userdetail.last_name,
                "dni": userWithDetail.userdetail.dni,
                "type": userWithDetail.userdetail.type,
                "email": userWithDetail.userdetail.email,
            }
            
            return JSONResponse(status_code=200, content=user_data)
        else:
            return JSONResponse(
                status_code=401,
                content=has_access,
            )
    except Exception as ex:
        print("Error ---->> ", ex)
        return JSONResponse(
            status_code=500,
            content={"message": "Error al obtener el usuario"}
        )






@user.get("/user/pagos/{username}")
def get_pagos_by_username(username: str, req: Request):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" not in has_access:
            return JSONResponse(status_code=401, content={"message": "Token inválido"})

        user = session.query(User).filter(User.username == username).first()
        if not user:
            return JSONResponse(status_code=404, content={"message": "Usuario no encontrado"})

        pagos = user.payments
        resultado = []

        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        for p in pagos:
            if p.active:
                fecha = p.created_at.strftime("%d/%m/%Y")
                mes_afectado = f"{meses[p.affected_month.month]} de {p.affected_month.year}"
                resultado.append({
                    "id": p.id,
                    "fecha": fecha,
                    "mes_afectado": mes_afectado,
                    "monto": p.amount,
                    "carrera": p.career.name if p.career else "Sin carrera"
                })

        # Ordenar de más nuevo a más viejo
        resultado.sort(key=lambda x: x["fecha"], reverse=True)

        return resultado

    except Exception as e:
        session.rollback()
        print("Error al traer pagos:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno"})
    finally:
        session.close()