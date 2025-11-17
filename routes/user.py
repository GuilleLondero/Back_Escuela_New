from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from models.modelo import (
    session, User, UserDetail, PivoteUserCareer,
    InputUser, InputLogin, InputUserAddCareer,
    InputPaginatedRequest, InputPaginatedRequestFilter,
    AsyncSessionLocal
)
from auth.security import Security

user = APIRouter()

# ENDPOINTS ORIGINALES (SÍNCRONOS)

@user.get("/")
def helloUser():
    return "Hello Usuario !!!!!"

@user.get("/users/all")
def getAllUsers(req: Request):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" in has_access:
            usersConDetail = session.query(User).options(joinedload(User.userdetail)).all()
            usuarios_con_detalle = [
                {
                    "id": u.id,
                    "username": u.username,
                    "password": u.password,
                    "first_name": u.userdetail.first_name,
                    "last_name": u.userdetail.last_name,
                    "dni": u.userdetail.dni,
                    "type": u.userdetail.type,
                    "email": u.userdetail.email,
                }
                for u in usersConDetail
            ]
            return JSONResponse(status_code=200, content=usuarios_con_detalle)
        else:
            return JSONResponse(status_code=401, content=has_access)
    except Exception as ex:
        print("Error ---->> ", ex)
        return {"message": "Error al obtener los usuarios"}

@user.post("/users/add")
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
        user = session.query(User).filter(User.username == userIn.username).first()
        if user and user.password == userIn.password:
            tkn = Security.generate_token(user)
            if not tkn:
                return JSONResponse(status_code=500, content={"message": "Error en la generación del token"})
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
            return JSONResponse(status_code=200, content=res)
        else:
            return JSONResponse(status_code=401, content={"message": "Usuario o contraseña inválida"})
    except Exception as ex:
        print("Error ---->>", ex)
    finally:
        session.close()

@user.post("/user/addcareer")
def addCareer(ins: InputUserAddCareer):
    try:
        newInsc = PivoteUserCareer(ins.id_user, ins.id_career)
        session.add(newInsc)
        session.commit()
        res = f"{newInsc.user.userdetail.first_name} {newInsc.user.userdetail.last_name} fue inscripto correctamente a {newInsc.career.name}"
        return res
    except Exception as ex:
        session.rollback()
        print("Error al inscribir al alumno:", ex)
    finally:
        session.close()

@user.get("/user/career/{_username}")
def get_career_user(_username: str):
    try:
        userEncontrado = session.query(User).filter(User.username == _username).first()
        arraySalida = []
        if userEncontrado:
            for inscripcion in userEncontrado.pivoteusercareer:
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


# NUEVOS ENDPOINTS: PAGINACIÓN ASINCRÓNICA


@user.post("/users/paginated")
async def get_users_paginated(req: Request, body: InputPaginatedRequest):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" not in has_access:
            return JSONResponse(status_code=401, content=has_access)

        limit = body.limit
        last_seen_id = body.last_seen_id
        search_text = body.search.strip() if body.search else None

        async with AsyncSessionLocal() as session:
            stmt = select(User).options(joinedload(User.userdetail)).order_by(User.id)

            if last_seen_id:
                stmt = stmt.filter(User.id > last_seen_id)

            if search_text:
                stmt = stmt.join(User.userdetail).filter(
                    or_(
                        User.username.ilike(f"%{search_text}%"),
                        UserDetail.first_name.ilike(f"%{search_text}%"),
                        UserDetail.last_name.ilike(f"%{search_text}%"),
                        UserDetail.email.ilike(f"%{search_text}%")
                    )
                )

            count_stmt = select(func.count(User.id))
            if search_text:
                count_stmt = count_stmt.join(User.userdetail).filter(
                    or_(
                        User.username.ilike(f"%{search_text}%"),
                        UserDetail.first_name.ilike(f"%{search_text}%"),
                        UserDetail.last_name.ilike(f"%{search_text}%"),
                        UserDetail.email.ilike(f"%{search_text}%")
                    )
                )

            total_count = (await session.execute(count_stmt)).scalar()
            result = await session.execute(stmt.limit(limit))
            users = result.scalars().all()

            items = [
                {
                    "id": u.id,
                    "username": u.username,
                    "first_name": u.userdetail.first_name,
                    "last_name": u.userdetail.last_name,
                    "email": u.userdetail.email
                }
                for u in users
            ]

            next_cursor = items[-1]["id"] if len(items) == limit else None

            return JSONResponse(
                status_code=200,
                content={
                    "items": items,
                    "next_cursor": next_cursor,
                    "total_count": total_count,
                    "limit": limit
                }
            )
    except Exception as e:
        print("Error en paginación de usuarios:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno"})


@user.post("/users/paginated/filtered")
async def get_users_paginated_filtered(req: Request, body: InputPaginatedRequestFilter):
    try:
        has_access = Security.verify_token(req.headers)
        if "iat" not in has_access:
            return JSONResponse(status_code=401, content=has_access)

        limit = body.limit
        last_seen_id = body.last_seen_id
        filters = body.filters or {}

        async with AsyncSessionLocal() as session:
            stmt = select(User).join(User.userdetail).options(joinedload(User.userdetail)).order_by(User.id)

            if last_seen_id:
                stmt = stmt.filter(User.id > last_seen_id)

            if "username" in filters:
                stmt = stmt.filter(User.username.ilike(f"%{filters['username']}%"))
            if "type" in filters:
                stmt = stmt.filter(UserDetail.type == filters["type"])
            if "email" in filters:
                stmt = stmt.filter(UserDetail.email.ilike(f"%{filters['email']}%"))

            count_stmt = select(func.count(User.id)).join(User.userdetail)
            if "username" in filters:
                count_stmt = count_stmt.filter(User.username.ilike(f"%{filters['username']}%"))
            if "type" in filters:
                count_stmt = count_stmt.filter(UserDetail.type == filters["type"])
            if "email" in filters:
                count_stmt = count_stmt.filter(UserDetail.email.ilike(f"%{filters['email']}%"))

            total_count = (await session.execute(count_stmt)).scalar()
            result = await session.execute(stmt.limit(limit))
            users = result.scalars().all()

            items = [
                {
                    "id": u.id,
                    "username": u.username,
                    "first_name": u.userdetail.first_name,
                    "last_name": u.userdetail.last_name,
                    "email": u.userdetail.email
                }
                for u in users
            ]

            next_cursor = items[-1]["id"] if len(items) == limit else None

            return JSONResponse(
                status_code=200,
                content={
                    "items": items,
                    "next_cursor": next_cursor,
                    "total_count": total_count,
                    "limit": limit
                }
            )
    except Exception as e:
        print("Error en paginación filtrada:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno"})