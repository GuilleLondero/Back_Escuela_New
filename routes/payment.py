from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models.modelo import Payment, InputPayment, User, session
from sqlalchemy.orm import joinedload
from datetime import datetime

meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

payment = APIRouter()


@payment.post("/payment/add")
def add_payment(pay: InputPayment):
    try:
        # Convertir string a datetime.date
        fecha = datetime.strptime(pay.affected_month, "%Y-%m").date()

        newPayment = Payment(
            pay.id_career,
            pay.id_user,
            pay.amount,
            fecha  
        )
        session.add(newPayment)
        session.commit()
        return {"message": "Pago registrado con éxito"}
    except Exception as ex:
        session.rollback()
        print("Error:", ex)
        return JSONResponse(status_code=500, content={"message": "Error al guardar pago"})


@payment.get("/payment/user/{_username}")
def payment_user(_username: str):
    try:
        user = session.query(User).filter(User.username == _username).first()
        if not user:
            return JSONResponse(status_code=404, content={"message": "Usuario no encontrado"})

        payments = (
            session.query(Payment)
            .filter(Payment.id_user == user.id, Payment.active == True)
            .order_by(Payment.created_at.desc())
            .all()
        )

        result = [
            {
                "id": pay.id,
                "amount": pay.amount,
                "fecha_pago": pay.created_at,
                "usuario": f"{user.userdetail.first_name} {user.userdetail.last_name}",
                "carrera": pay.career.name,
                "mes_afectado": f"{meses[pay.affected_month.month]} de {pay.affected_month.year}",
            }
            for pay in payments
        ]

        return result
    except Exception as ex:
        session.rollback()
        print("Error:", ex)
        return JSONResponse(status_code=500, content={"message": "Error interno"})


@payment.put("/payments/{id}")
def update_payment(id: int, input: InputPayment):
    try:
        pay = session.query(Payment).filter(Payment.id == id).first()
        if not pay:
            return JSONResponse(status_code=404, content={"message": "Pago no encontrado"})

        # Actualizar campos básicos
        pay.id_user = input.id_user
        pay.id_career = input.id_career
        pay.amount = input.amount
        pay.active = input.active
        
        # Convertir affected_month de string a datetime si es necesario
        if isinstance(input.affected_month, str):
            pay.affected_month = datetime.strptime(input.affected_month, "%Y-%m").date()
        else:
            pay.affected_month = input.affected_month

        session.commit()
        return {"success": True, "message": "Pago actualizado correctamente"}
    except ValueError as ve:
        session.rollback()
        print("Error de formato de fecha:", ve)
        return JSONResponse(status_code=400, content={"message": "Formato de fecha incorrecto. Use YYYY-MM"})
    except Exception as e:
        session.rollback()
        print("Error al actualizar pago:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno"})


@payment.delete("/payment/{id}")
def delete_payment(id: int):
    try:
        pay = session.query(Payment).filter(Payment.id == id).first()
        if not pay:
            return JSONResponse(status_code=404, content={"message": "Pago no encontrado"})

        pay.active = False
        session.commit()
        return {"success": True, "message": "Pago dado de baja lógicamente"}
    except Exception as ex:
        session.rollback()
        print("Error al eliminar pago:", ex)
        return JSONResponse(status_code=500, content={"message": "Error interno"})


@payment.get("/payments/active")
def get_active_payments():
    try:
        pagos = (
            session.query(Payment)
            .filter(Payment.active == True)
            .order_by(Payment.created_at.desc())  # 👈 IMPORTANTE
            .all()
        )
        result = [
            {
                "id": p.id,
                "monto": p.amount,
                "fecha": p.created_at,
                "mes_afectado": f"{meses[p.affected_month.month]} de {p.affected_month.year}",
                "alumno": f"{p.user.userdetail.first_name} {p.user.userdetail.last_name}",
                "carrera": p.career.name
            }
            for p in pagos
        ]
        return result
    except Exception as e:
        session.rollback()
        print("Error al traer pagos activos:", e)
        return JSONResponse(status_code=500, content={"message": "Error interno"})