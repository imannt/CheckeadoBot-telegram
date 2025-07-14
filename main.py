from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from datetime import datetime
import re
import requests
import os
from dotenv import load_dotenv

# Cargar token desde archivo .env
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Estados del flujo de conversación
NOMBRE, APELLIDO, CEDULA, CORREO, TELEFONO, FECHA_NAC, SEXO, ESTADO, MUNICIPIO, PARROQUIA = range(10)

# 🟢 Comando /start con verificación previa
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    nombre = user.first_name or user.username or "Participante"

    try:
        respuesta = requests.get(f"http://localhost:5000/verificar/{user_id}")
        resultado = respuesta.json()
        registrado = resultado.get("registrado", False)
    except:
        registrado = False

    if registrado:
        mensaje = f"""
            👋 ¡Hola de nuevo, {nombre}!

            Ya estás registrado en nuestro sistema 🟢.

            Puedes usar los siguientes comandos para interactuar con el bot:
            /asistencia - Registrar tu asistencia.
            /actualizacion - Actualizar tus datos.
            /eventos - Ver tus eventos asistidos.
        """
        await update.message.reply_text(mensaje)
        return ConversationHandler.END
    else:
        await update.message.reply_text(f"""
                👋 ¡Hola, {nombre}!
                Estás usando Checkeado, un chatbot para registrar asistencia en los eventos de la Fundación KPMG Venezuela 🌱

                Aquí podrás:
                🔸 Registrar tus datos personales
                🔸 Confirmar tu participación en eventos
                🔸 Recibir notificaciones directamente por Telegram

                Por favor, escribe tu primer y segundo nombre para comenzar 📝.
            """
        )
        return NOMBRE

# *** Registro del usuario ***
async def apellido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nombre'] = update.message.text.strip()
    await update.message.reply_text("Ahora escribe tu apellido completo:")
    return APELLIDO

async def cedula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['apellido'] = update.message.text.strip()
    await update.message.reply_text("Introduce tu número de cédula, sin agregar puntos. ej: 12345678")
    return CEDULA

async def correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cedula'] = update.message.text.strip()
    await update.message.reply_text("Introduce tu correo electrónico:")
    return CORREO

async def telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['correo'] = update.message.text.strip()
    boton = KeyboardButton(text="📱 Compartir número", request_contact=True)
    teclado = ReplyKeyboardMarkup([[boton]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Presiona el botón para compartir tu número de teléfono o escríbelo sin agregar guiones o paréntesis.", reply_markup=teclado)
    return TELEFONO

async def fecha_nac(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contacto = update.message.contact
    context.user_data['telefono'] = contacto.phone_number if contacto else update.message.text.strip()
    await update.message.reply_text("Introduce tu fecha de nacimiento (DD/MM/AAAA):")
    return FECHA_NAC

async def sexo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha_str = update.message.text.strip()
    try:
        fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
        context.user_data['fecha_nac'] = fecha_obj.strftime("%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("⚠️ Formato incorrecto. Usa DD/MM/AAAA.")
        return SEXO

    opciones = [["Mujer", "Hombre", "Prefiero no decirlo"]]
    teclado = ReplyKeyboardMarkup(opciones, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Selecciona tu sexo según los botones:", reply_markup=teclado)
    return SEXO

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sexo'] = update.message.text.strip()
    try:
        respuesta = requests.get("http://localhost:5000/estados")
        estados = respuesta.json()

        if not isinstance(estados, list):
            raise ValueError("Respuesta inesperada")

        teclado = ReplyKeyboardMarkup(
            [estados[i:i+2] for i in range(0, len(estados), 2)],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text("Selecciona tu estado:", reply_markup=teclado)
        return ESTADO
    except Exception:
        await update.message.reply_text("❌ No se pudo obtener la lista de estados. Inténtalo más tarde.")
        return ConversationHandler.END

async def municipio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado = update.message.text.strip()
    context.user_data["estado"] = estado

    try:
        respuesta = requests.get(f"http://localhost:5000/municipios/{estado}")
        municipios = respuesta.json()

        if isinstance(municipios, dict) and "error" in municipios:
            raise ValueError("Estado inválido")

        teclado = ReplyKeyboardMarkup(
            [municipios[i:i+2] for i in range(0, len(municipios), 2)],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text("Selecciona tu municipio:", reply_markup=teclado)
        return MUNICIPIO
    except Exception:
        await update.message.reply_text("❌ Error al obtener los municipios. Inténtalo más tarde.")
        return ConversationHandler.END

async def parroquia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    municipio = update.message.text.strip()
    estado = context.user_data["estado"]  # ← recuperamos el estado elegido
    context.user_data["municipio"] = municipio

    try:
        respuesta = requests.get(f"http://localhost:5000/parroquias/{estado}/{municipio}")
        parroquias = respuesta.json()

        if isinstance(parroquias, dict) and "error" in parroquias:
            raise ValueError("Municipio no válido dentro de ese estado")

        teclado = ReplyKeyboardMarkup(
            [parroquias[i:i+2] for i in range(0, len(parroquias), 2)],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text("Selecciona tu parroquia:", reply_markup=teclado)
        return PARROQUIA  # o el siguiente paso como confirmación
    except Exception:
        await update.message.reply_text("❌ Error al obtener las parroquias. Inténtalo más tarde.")
        return ConversationHandler.END


# Confirmar y enviar al backend
async def confirmacion_registro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['parroquia'] = update.message.text.strip()
    datos = context.user_data.copy()
    datos["id_participante"] = update.effective_user.id

    try:
        respuesta = requests.post("http://localhost:5000/registrar", json=datos)
        resultado = respuesta.json()
        if respuesta.status_code == 201:
            await update.message.reply_text("✅ Registro completado. ¡Gracias por formar parte!")
        else:
            await update.message.reply_text(f"❌ Error: {resultado.get('error', 'No se pudo registrar')}")
    except:
        await update.message.reply_text("⚠️ No se pudo contactar con el servidor.")
    return ConversationHandler.END

# Flujo del bot
registro_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apellido)],
        APELLIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, cedula)],
        CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, correo)],
        CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, telefono)],
        TELEFONO: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), fecha_nac)],
        FECHA_NAC: [MessageHandler(filters.TEXT & ~filters.COMMAND, sexo)],
        SEXO: [MessageHandler(filters.TEXT & ~filters.COMMAND, estado)],
        ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, municipio)],
        MUNICIPIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, parroquia)],
        PARROQUIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmacion_registro)],
    },
    fallbacks=[],
)

# Iniciar aplicación
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(registro_handler)
    app.run_polling()