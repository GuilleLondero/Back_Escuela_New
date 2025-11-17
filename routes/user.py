from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from models.modelo import session, User, UserDetail, PivoteUserCareer, InputUser, InputLogin, InputUserAddCareer, InputPaginatedRequest, InputPaginatedRequestFilter, AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from auth.security import Security
from sqlalchemy import or_


# Creamos router para agrupar las rutas relacionadas con usuarios:
user = APIRouter()

@user.get("/")
### Ruta de prueba para verificar si el módulo de usuarios está funcionando bien
def helloUser():
    return "Hello Usuario !!!!!"

# region endpoints sin filtrados
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

"""
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
"""    

#permite cambiar contraseña de cada usuario
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
    
"""
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

"""

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


"""
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
"""

"""
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

"""
@user.post("/user/paginated")
def get_users_paginated(req: Request, body: InputPaginatedRequest):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" not in has_access:
            return JSONResponse(status_code=401, content=has_access)

        limit = body.limit
        last_seen_id = body.last_seen_id

        query = (
            session.query(User).options(joinedload(User.userdetail)).order_by(User.id)
        )

        if last_seen_id is not None:
            query = query.filter(User.id > last_seen_id)

        users_with_detail = query.limit(limit)

        usuarios_con_detalles = []
        for us in users_with_detail:
            user_con_detalle = {
                "id": us.id,
                "username": us.username,
                "first_name": us.userdetail.first_name,
                "last_name": us.userdetail.last_name,
                "dni": us.userdetail.dni,
                "type": us.userdetail.type,
                "email": us.userdetail.email,
            }
            usuarios_con_detalles.append(user_con_detalle)

        next_cursor = (
            usuarios_con_detalles[-1]["id"]
            if len(usuarios_con_detalles) == limit
            else None
        )

        print("SQL query:", str(query))

        return JSONResponse(
            status_code=200,
            content={"users": usuarios_con_detalles, "next_cursor": next_cursor},
        )

    except Exception as error:
        print("Error al obtener página de usuarios ----> ", error)
        return JSONResponse(
            status_code=500, content={"message": "Error al obtener página de usuarios"}
        )
    
# endregion endpoints sin filtrados

# region endpoints PaGinado filtrados

# region endpoints paginado filtrados SINcro
# ruta paginated filtrada (recibe un str) con fcion sincronica
@user.post("/user/paginated/filtered-sync")
def get_users_paginated_filtered(req: Request, body: InputPaginatedRequest):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" not in has_access:
            return JSONResponse(status_code=401, content=has_access)

        limit = body.limit
        last_seen_id = body.last_seen_id
        search_text = getattr(body, "search", "").strip()  # Nuevo parámetro opcional

        query = (
            session.query(User)
            .join(User.userdetail)  # join explícito para poder filtrar
            .options(joinedload(User.userdetail))  # mantiene la carga automática
            .order_by(User.id)
        )

        if last_seen_id is not None:
            query = query.filter(User.id > last_seen_id)

        # Filtrado por search_text si se envía
        if search_text:
            search_pattern = f"%{search_text}%"
            query = query.filter(
                or_(
                    UserDetail.first_name.ilike(search_pattern),
                    UserDetail.last_name.ilike(search_pattern),
                    UserDetail.email.ilike(search_pattern),
                )
            )

        users_with_detail = query.limit(limit).all()

        usuarios_con_detalles = []
        for us in users_with_detail:
            user_con_detalle = {
                "id": us.id,
                "username": us.username,
                "first_name": us.userdetail.first_name,
                "last_name": us.userdetail.last_name,
                "dni": us.userdetail.dni,
                "type": us.userdetail.type,
                "email": us.userdetail.email,
            }
            usuarios_con_detalles.append(user_con_detalle)

        next_cursor = (
            usuarios_con_detalles[-1]["id"]
            if len(usuarios_con_detalles) == limit
            else None
        )

        print("Search text:", search_text)
        print("SQL query:", str(query))

        return JSONResponse(
            status_code=200,
            content={"users": usuarios_con_detalles, "next_cursor": next_cursor},
        )

    except Exception as error:
        print("Error al obtener página de usuarios filtrada ----> ", error)
        return JSONResponse(
            status_code=500,
            content={"message": "Error al obtener página de usuarios filtrada"},
        )


# ruta paginated filtered (recibe un dict) con funcion sincronica
@user.post("/user/paginated/filtered-dict-sync")
def get_users_paginated_filtered(req: Request, body: InputPaginatedRequestFilter):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" not in has_access:
            return JSONResponse(status_code=401, content=has_access)

        limit = body.limit
        last_seen_id = body.last_seen_id

        query = (
            session.query(User)
            .join(User.userdetail)  # join explícito para poder filtrar
            .options(joinedload(User.userdetail))  # mantiene la carga automática
            .order_by(User.id)
        )

        # 🔹 Filtros adicionales
        if hasattr(body, "filters") and body.filters:
            if "username" in body.filters:
                query = query.filter(
                    User.username.ilike(f"%{body.filters['username']}%")
                )
            if "type" in body.filters:
                query = query.filter(UserDetail.type == body.filters["type"])
            if "email" in body.filters:
                query = query.filter(
                    UserDetail.email.ilike(f"%{body.filters['email']}%")
                )

        # 🔹 Filtro por cursor
        if last_seen_id is not None:
            query = query.filter(User.id > last_seen_id)

        users_with_detail = query.limit(limit)

        usuarios_con_detalles = []
        for us in users_with_detail:
            user_con_detalle = {
                "id": us.id,
                "username": us.username,
                "first_name": us.userdetail.first_name,
                "last_name": us.userdetail.last_name,
                "dni": us.userdetail.dni,
                "type": us.userdetail.type,
                "email": us.userdetail.email,
            }
            usuarios_con_detalles.append(user_con_detalle)

        next_cursor = (
            usuarios_con_detalles[-1]["id"]
            if len(usuarios_con_detalles) == limit
            else None
        )

        print("Filters:", body.filters)
        print("Query: ", str(query))

        return JSONResponse(
            status_code=200,
            content={"users": usuarios_con_detalles, "next_cursor": next_cursor},
        )

    except Exception as error:
        print("Error al obtener página de usuarios ----> ", error)
        return JSONResponse(
            status_code=500, content={"message": "Error al obtener página de usuarios"}
        )

 # endregion endpoints paginado filtrados SINcro

# region endpoints paginado filtrados async

# ruta paginated filtered (Diccio) con funcion async
@user.post("/user/paginated/filtered-dict-async")
async def get_users_paginated_filtered_async(
    req: Request, body: InputPaginatedRequestFilter
):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" not in has_access:
            return JSONResponse(status_code=401, content=has_access)

        limit = body.limit
        last_seen_id = body.last_seen_id

        async with AsyncSessionLocal() as session:

            # Construcción de la consulta
            stmt = (
                select(User)
                .join(User.userdetail)
                .options(joinedload(User.userdetail))
                .order_by(User.id)
            )

            # Filtros adicionales
            if hasattr(body, "filters") and body.filters:
                if "username" in body.filters:
                    stmt = stmt.filter(
                        User.username.ilike(f"%{body.filters['username']}%")
                    )
                if "type" in body.filters:
                    stmt = stmt.filter(UserDetail.type == body.filters["type"])
                if "email" in body.filters:
                    stmt = stmt.filter(
                        UserDetail.email.ilike(f"%{body.filters['email']}%")
                    )

            # Filtro por cursor
            if last_seen_id is not None:
                stmt = stmt.filter(User.id > last_seen_id)

            # Limito resultados
            stmt = stmt.limit(limit)

            # Ejecuto la consulta
            result = await session.execute(stmt)
            users_with_detail = result.scalars().all()

            # Armo la salida de datos
            usuarios_con_detalles = [
                {
                    "id": us.id,
                    "username": us.username,
                    "first_name": us.userdetail.first_name,
                    "last_name": us.userdetail.last_name,
                    "dni": us.userdetail.dni,
                    "type": us.userdetail.type,
                    "email": us.userdetail.email,
                }
                for us in users_with_detail
            ]

            # armo la salida del cursor
            next_cursor = (
                usuarios_con_detalles[-1]["id"]
                if len(usuarios_con_detalles) == limit
                else None
            )

            print("Filters:", body.filters)
            print("Query: ", str(stmt))

            # respondo con datos y cursor
            return JSONResponse(
                status_code=200,
                content={"users": usuarios_con_detalles, "next_cursor": next_cursor},
            )

    except Exception as error:
        print("Error al obtener página de usuarios ----> ", error)
        return JSONResponse(
            status_code=500, content={"message": "Error al obtener página de usuarios"}
        )

# ruta paginada filtrada (recibe un str) con funcion async
@user.post("/user/paginated/filtered-str-async")
async def get_users_paginated_filtered_str_async(
    req: Request, body: InputPaginatedRequest
):
    try:
        has_access = Security.verify_token(req.headers)

        if "iat" not in has_access:
            return JSONResponse(status_code=401, content=has_access)

        limit = body.limit
        last_seen_id = body.last_seen_id
        search_text = getattr(body, "search", "").strip()

        async with AsyncSessionLocal() as session:
            stmt = (
                select(User)
                .join(User.userdetail)
                .options(joinedload(User.userdetail))
                .order_by(User.id)
            )

            if last_seen_id is not None:
                stmt = stmt.filter(User.id > last_seen_id)

            if search_text:
                search_pattern = f"%{search_text}%"
                stmt = stmt.filter(
                    or_(
                        UserDetail.first_name.ilike(search_pattern),
                        UserDetail.last_name.ilike(search_pattern),
                        UserDetail.email.ilike(search_pattern),
                    )
                )

            # ejecutar la query con limit
            result = session.execute(stmt.limit(limit))
            users_with_detail = result.scalars().all()

            usuarios_con_detalles = []
            for us in users_with_detail:
                user_con_detalle = {
                    "id": us.id,
                    "username": us.username,
                    "first_name": us.userdetail.first_name,
                    "last_name": us.userdetail.last_name,
                    "dni": us.userdetail.dni,
                    "type": us.userdetail.type,
                    "email": us.userdetail.email,
                }
                usuarios_con_detalles.append(user_con_detalle)

            next_cursor = (
                usuarios_con_detalles[-1]["id"]
                if len(usuarios_con_detalles) == limit
                else None
            )

            return JSONResponse(
                status_code=200,
                content={"users": usuarios_con_detalles, "next_cursor": next_cursor},
            )
    except Exception as error:
        print("Error al obtener página de usuarios filtradas --->", error)
        return JSONResponse(
            status_code=500,
            content={"message": "Error al obterner página de usuarios filtrada"},
        )

# endregion endpoints paginado filtrados async

# endregion endpoints PaGinado filtrados