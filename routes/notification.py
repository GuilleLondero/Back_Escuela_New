from fastapi import APIRouter, Request
from models.modelo import session, Notification, InputNotification  
from fastapi.responses import JSONResponse
import traceback
import datetime

notification = APIRouter()


# ✅ Obtener todas las notificaciones
@notification.get("/notifications")
def get_notifications():
    try:
        notis = session.query(Notification).order_by(Notification.created_at.desc()).all()
        return [
            {
                "id": n.id,
                "message": n.message,
                "created_at": n.created_at.strftime("%d/%m/%Y")
            }
            for n in notis
        ]
    except Exception as e:
        print("Error al traer notificaciones:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno"})


# ✅ Crear una nueva notificación (ruta esperada por el frontend)
@notification.post("/notifications")
def create_notification(noti: InputNotification):
    try:
        nueva = Notification(message=noti.message)  # 👈 corregido
        session.add(nueva)
        session.commit()
        return {"success": True, "message": "Notificación creada correctamente"}
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": "Error al crear notificación"})



# ✅ Ruta alternativa para crear (si querés mantenerla)
@notification.post("/notifications/add")
def add_notification(noti: InputNotification):
    return create_notification(noti)


# ✅ Editar una notificación
@notification.put("/notifications/{id}")
def update_notification(id: int, data: InputNotification):
    try:
        n = session.query(Notification).filter(Notification.id == id).first()
        if n:
            n.message = data.message
            session.commit()
            return {"success": True}
        return JSONResponse(status_code=404, content={"message": "No encontrada"})
    except:
        session.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": "Error interno"})


# ✅ Eliminar una notificación
@notification.delete("/notifications/{id}")
def delete_notification(id: int):
    try:
        n = session.query(Notification).filter(Notification.id == id).first()
        if n:
            session.delete(n)
            session.commit()
            return {"success": True}
        return JSONResponse(status_code=404, content={"message": "No encontrada"})
    except:
        session.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": "Error interno"})
