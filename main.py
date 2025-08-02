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
NOMBRE, APELLIDO, CEDULA, CORREO, TELEFONO, FECHA_NAC, SEXO, ESTADO, MUNICIPIO, PARROQUIA, RESUMEN = range(11)

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
                Estás usando Checkeado, un chatbot para registrar tu asistencia de eventos sociales.

                Aquí podrás:
                🔸 Confirmar tu participación en eventos.
                🔸 Recibir notificaciones directamente por Telegram.

                📝 Antes de comenzar, por favor, escribe tu *primer y segundo nombre* para comenzar.
            """
        )
        return NOMBRE

# ***Botones del registro***

def teclado_corregir():
    corregir = KeyboardButton("↩️ Corregir anterior")
    return ReplyKeyboardMarkup([[corregir]], one_time_keyboard=True, resize_keyboard=True)

def teclado_telefono():
    boton_contacto = KeyboardButton(text="📱 Compartir número", request_contact=True)
    corregir = KeyboardButton("↩️ Corregir anterior")
    return ReplyKeyboardMarkup(
        [[boton_contacto], [corregir]],
        one_time_keyboard=True,
        resize_keyboard=True
    )

def teclado_sexo():
    opciones = ["Mujer", "Hombre"],
    ["Prefiero no decirlo"],
    ["↩️ Corregir anterior"]
    
    return ReplyKeyboardMarkup(opciones, one_time_keyboard=True, resize_keyboard=True)

# *** Funciones para obtener opciones de estados, municipios y parroquias **
def obtener_opciones(tipo: str, estado=None, municipio=None):
    base = "http://localhost:5000"

    if tipo == "estado":
        url = f"{base}/estados"
    elif tipo == "municipio" and estado:
        url = f"{base}/municipios/{estado}"
    elif tipo == "parroquia" and estado and municipio:
        url = f"{base}/parroquias/{estado}/{municipio}"
    else:
        return []

    try:
        respuesta = requests.get(url)
        opciones = respuesta.json()
        if isinstance(opciones, dict) and "error" in opciones:
            return []
        return opciones if isinstance(opciones, list) else []
    except:
        return []

def teclado_dinamico(opciones):
    botones = [KeyboardButton(opcion) for opcion in opciones]
    agrupados = [botones[i:i+2] for i in range(0, len(botones), 2)]
    opciones = agrupados + [["↩️ Corregir anterior"]]
    return ReplyKeyboardMarkup(opciones, one_time_keyboard=True, resize_keyboard=True)

# *** Registro del usuario ***
async def nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto or len(texto.split()) < 2:
        await update.message.reply_text("⚠️ tu nombre debe tener al menos dos palabras. Por favor, inténtalo de nuevo.")
        return NOMBRE
    context.user_data['nombre'] = texto  # Guardamos el nombre en user_data

    await update.message.reply_text("Ahora escribe tu apellido completo:", reply_markup=teclado_corregir())
    return APELLIDO

async def apellido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu nombre completo nuevamente:")
        return NOMBRE
    texto = update.message.text.strip()
    if not texto or len(texto.split()) < 2:
        await update.message.reply_text("Tu apellido debe tener al menos dos palabras. Por favor, inténtalo de nuevo.")
        return APELLIDO
    
    context.user_data['apellido'] = texto  # Guardamos el apellido en user_data
    
    await update.message.reply_text("Introduce tu número de cédula, sin agregar puntos. ej: 12345678", reply_markup=teclado_corregir())
    return CEDULA

async def cedula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu apellido sbre completo nuevamente:", reply_markup=teclado_corregir())
        return APELLIDO
    texto = update.message.text.strip()
    if not texto.isdigit() or len(texto) < 8:
        await update.message.reply_text("⚠️ Por favor, introduce un número de cédula válido.")
        return CEDULA
    context.user_data['cedula'] = texto  # Guardamos la cédula en user_data

    await update.message.reply_text("Introduce tu correo electrónico:", reply_markup=teclado_corregir())
    return CORREO

def validar_correo(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$" # Expresión regular para validar correos
    return re.match(patron, correo) is not None

async def correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu cédula nuevamente:")
        return CEDULA
    
    if not validar_correo(texto):
        await update.message.reply_text("⚠️ Formato de correo electrónico inválido. Inténtalo de nuevo.")
        return CORREO
    
    context.user_data['correo'] = texto # Guardamos el correo en user_data

    await update.message.reply_text("Presiona el botón para compartir tu número de teléfono o escríbelo sin agregar guiones o paréntesis.", reply_markup=teclado_telefono())
    return TELEFONO


async def telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):

    contacto = update.message.contact
    telefono = contacto.phone_number if contacto else update.message.text.strip()

    if telefono == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu correo nuevamente:")
        return CORREO
    
    
    # Eliminar el prefijo internacional si existe
    if telefono.startswith("+58"):
        telefono = telefono.replace("+58", "0")
    elif telefono.startswith("58"):
        telefono = telefono.replace("58", "0")

    # Validar que comience con 04 y tenga 11 dígitos
    if not telefono.startswith("04") or len(telefono) != 11 or not telefono.isdigit():
        await update.message.reply_text("❌ Número inválido. Procura que comience con '04' y tener 11 dígitos.\nEjemplo: 04121234567")
        return TELEFONO

    await update.message.reply_text("📅 Escribe tu fecha de nacimiento en formato DD/MM/AAAA:", reply_markup=teclado_telefono())
    return FECHA_NAC

async def fecha_nac(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if texto == "↩️ Corregir anterior":
        await update.message.reply_text(
            "Presiona el botón para compartir tu número de teléfono o escríbelo sin agregar guiones o paréntesis.",
            reply_markup=teclado_telefono()
        )
        return TELEFONO

    try:
        fecha_obj = datetime.strptime(texto, "%d/%m/%Y")
        context.user_data["fecha_nac"] = fecha_obj.strftime("%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("⚠️ Formato incorrecto. Usa DD/MM/AAAA.")
        return FECHA_NAC

    await update.message.reply_text("Selecciona tu sexo:", reply_markup=teclado_sexo())
    return SEXO


async def sexo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if texto == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu fecha de nacimiento nuevamente:", reply_markup=teclado_corregir())
        return FECHA_NAC
    
    if texto not in ["Mujer", "Hombre", "Prefiero no decirlo"]:
        await update.message.reply_text("❌ Selección inválida. Usa los botones por favor.")
        return SEXO
    
    context.user_data["sexo"] = texto
    try:
        respuesta = requests.get("http://localhost:5000/estados")
        estados = respuesta.json()

        if not isinstance(estados, list):
            raise ValueError("Respuesta inesperada, intenta más tarde.")

        teclado = teclado_dinamico(estados)
        await update.message.reply_text("Selecciona tu estado:", reply_markup=teclado)
        return ESTADO
    except:
        await update.message.reply_text("❌ No se pudo obtener la lista de estados. Inténtalo más tarde.")
        return ConversationHandler.END

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto == "↩️ Corregir anterior":
        await update.message.reply_text("Selecciona tu sexo nuevamente:", reply_markup=teclado_sexo())
        return SEXO
    
    context.user_data["estado"] = texto

    try:
        respuesta = requests.get(f"http://localhost:5000/municipios/{texto}")
        municipios = respuesta.json()

        if isinstance(municipios, dict) and "error" in municipios:
            raise ValueError("Estado inválido")

        teclado = teclado_dinamico(municipios)
        await update.message.reply_text("Selecciona tu municipio:", reply_markup=teclado)
        return MUNICIPIO
    except Exception:
        await update.message.reply_text("❌ No se pudo obtener la lista de municipios. Inténtalo más tarde.")
        return ConversationHandler.END
    
async def municipio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if texto == "↩️ Corregir anterior":
        estados = obtener_opciones("estado")
        await update.message.reply_text("Selecciona tu estado nuevamente:", reply_markup=teclado_dinamico(estados))
        return ESTADO

    context.user_data["municipio"] = texto
    estado = context.user_data["estado"]

    try:
        respuesta = requests.get(f"http://localhost:5000/parroquias/{estado}/{texto}")
        parroquias = respuesta.json()

        if isinstance(parroquias, dict) and "error" in parroquias:
            raise ValueError("Municipio inválido")

        teclado = teclado_dinamico(parroquias)
        await update.message.reply_text("Selecciona tu parroquia:", reply_markup=teclado)
        return PARROQUIA
    
    except Exception:
        await update.message.reply_text("❌ No se pudo obtener la lista de parroquias. Inténtalo más tarde.")
        return ConversationHandler.END

async def parroquia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if texto == "↩️ Corregir anterior":
        estado = context.user_data["estado"]
        municipios = obtener_opciones("municipio", estado=estado)
        await update.message.reply_text("Selecciona tu municipio nuevamente:", reply_markup=teclado_dinamico(municipios))
        return MUNICIPIO

    context.user_data["parroquia"] = texto

    resumen = f"""
        📋 *Resumen de registro:*

        👤 *Nombre:* {context.user_data.get('nombre')}
        👥 *Apellido:* {context.user_data.get('apellido')}
        🪪 *Cédula:* {context.user_data.get('cedula')}
        📧 *Correo:* {context.user_data.get('correo')}
        📱 *Teléfono:* {context.user_data.get('telefono')}
        📅 *Fecha de nacimiento:* {context.user_data.get('fecha_nac')}
        ⚧ *Sexo:* {context.user_data.get('sexo')}
        🗺️ *Estado:* {context.user_data.get('estado')}
        🏘️ *Municipio:* {context.user_data.get('municipio')}
        📍 *Parroquia:* {context.user_data.get('parroquia')}

        ¿Deseas confirmar este registro?
    """

    teclado = ReplyKeyboardMarkup([["Nombre", "Apellido", "Cédula"],
    ["Correo", "Teléfono", "Fecha de nacimiento"],
    ["Sexo", "Estado", "Municipio"],
    ["Parroquia"],
    ["✅ Confirmar", "↩️ Corregir anterior"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(resumen, reply_markup=teclado, parse_mode="Markdown")
    return RESUMEN

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if texto == "↩️ Corregir anterior":
        estado = context.user_data["estado"]
        municipio = context.user_data["municipio"]
        parroquias = obtener_opciones("parroquia", estado=estado, municipio=municipio)
        await update.message.reply_text("Selecciona tu parroquia nuevamente:", reply_markup=teclado_dinamico(parroquias))
        return PARROQUIA

    if texto == "✅ Confirmar":
        datos = context.user_data.copy()
        datos["id_participante"] = update.effective_user.id
        try:
            respuesta = requests.post("http://localhost:5000/registrar", json=datos)
            if respuesta.status_code in [200, 201]:
                await update.message.reply_text("✅ ¡Registro completado con éxito!")
            else:
                await update.message.reply_text("⚠️ Hubo un error al guardar tus datos.")
        except:
            await update.message.reply_text("❌ No se pudo conectar con el servidor.")
        return ConversationHandler.END
    
    correcciones = {
        "nombre": NOMBRE,
        "apellido": APELLIDO,
        "cédula": CEDULA,
        "correo": CORREO,
        "teléfono": TELEFONO,
        "fecha de nacimiento": FECHA_NAC,
        "sexo": SEXO,
        "estado": ESTADO,
        "municipio": MUNICIPIO,
        "parroquia": PARROQUIA
    }

    if texto in correcciones:
        await update.message.reply_text(f"🔁 Corrigiendo campo: *{texto}*.\nPor favor, ingresa el nuevo valor:", parse_mode="Markdown")
        return correcciones[texto]


    await update.message.reply_text("❌ Opción inválida. Usa los botones.")
    return RESUMEN

# Flujo del bot
registro_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nombre)],
        APELLIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, apellido)],
        CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, cedula)],
        CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, correo)],
        TELEFONO: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), telefono)],
        FECHA_NAC: [MessageHandler(filters.TEXT & ~filters.COMMAND, fecha_nac)],
        SEXO: [MessageHandler(filters.TEXT & ~filters.COMMAND, sexo)],
        ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, estado)],
        MUNICIPIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, municipio)],
        PARROQUIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, parroquia)],
        RESUMEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, resumen)],
    },
    fallbacks=[],
)

# Iniciar aplicación
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(registro_handler)
    app.run_polling()