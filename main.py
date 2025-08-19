from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from datetime import datetime
import re
import os
import aiohttp
from dotenv import load_dotenv

# Importa los handler
from asistencia import evento_handler

# Cargar token desde archivo .env
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Estados del flujo de conversación
NOMBRE, APELLIDO, CEDULA, ORGANIZACION, CORREO, TELEFONO, FECHA_NAC, SEXO, ESTADO, MUNICIPIO, PARROQUIA, RESUMEN = range(12)

# 🟢 Comando /start con verificación previa
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    nombre = user.first_name or user.username or "Participante"

    try:
        #respuesta = requests.get(f"http://localhost:5000/verificar/{user_id}")
        #resultado = respuesta.json()
        #registrado = resultado.get("registrado", False)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:5000/verificar/{user_id}") as response:
                resultado = await response.json()
                registrado = resultado.get("registrado", False)
    except:
        registrado = False


    if registrado:
        mensaje = f"""👋 ¡Hola de nuevo, {nombre}!\n 
🟢 *Ya estás registrado en nuestro sistema.* \n
Puedes usar los siguientes comandos para interactuar con el bot:\n
/asistencia - Registrar tu asistencia.
        """
        await update.message.reply_text(mensaje, parse_mode="Markdown")
        return ConversationHandler.END
    else:
        await update.message.reply_text(f"""👋 ¡Hola, {nombre}!\n 
Estás usando *Checkeado*, un bot para gestionar tu asistencia en eventos sociales.\n""", parse_mode="Markdown")
        await update.message.reply_text("📝 Antes de comenzar, por favor, escribe tu *primer* y *segundo* nombre.", parse_mode="Markdown")
        return NOMBRE

# ***Cancelar operación***
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Detecta si viene desde texto o desde botón inline
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("🚫 Registro cancelado. Puedes volver a empezar cuando lo desees.")
    else:
        await update.message.reply_text("🚫 Registro cancelado. Puedes volver a empezar cuando lo desees.")

    context.user_data.clear()  # Limpieza de datos de sesión
    return ConversationHandler.END
# ***Botones inline del registro***
def resumen_botones_edicion():
    botones = [
        [InlineKeyboardButton("Nombre", callback_data="corregir_nombre"),
         InlineKeyboardButton("Apellido", callback_data="corregir_apellido")],

        [InlineKeyboardButton("Cédula", callback_data="corregir_cedula"),
         InlineKeyboardButton("Correo", callback_data="corregir_correo")],
        [InlineKeyboardButton("Organización", callback_data="corregir_organizacion")],

        [InlineKeyboardButton("Teléfono", callback_data="corregir_telefono"),
         InlineKeyboardButton("Fecha de nacimiento", callback_data="corregir_fecha")],

        [InlineKeyboardButton("Sexo", callback_data="corregir_sexo"),
         InlineKeyboardButton("Estado", callback_data="corregir_estado")],

        [InlineKeyboardButton("Municipio", callback_data="corregir_municipio"),
         InlineKeyboardButton("Parroquia", callback_data="corregir_parroquia")],

        [InlineKeyboardButton("✅ Confirmar registro", callback_data="confirmar"),
        InlineKeyboardButton("🚫 Cancelar", callback_data="cancelar")]
    ]
    return InlineKeyboardMarkup(botones)

# ***Botones ReplyKeyboardMarkup del registro***
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
    opciones = [
        ["Mujer", "Hombre"],
        ["Prefiero no decirlo"],
        ["↩️ Corregir anterior"]
    ]
    return ReplyKeyboardMarkup(opciones, one_time_keyboard=True, resize_keyboard=True)

# *** Funciones para obtener opciones de estados, municipios y parroquias **
async def obtener_opciones(tipo: str, estado=None, municipio=None):
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
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                opciones = await response.json()
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

    #restricción para evitar nombres con menos de dos palabras
    # if not texto or len(texto.split()) < 2:
        # await update.message.reply_text("⚠️ tu nombre debe tener al menos dos palabras. Por favor, inténtalo de nuevo.")
        # return NOMBRE

    context.user_data['nombre'] = texto  
    
    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False
        return await mostrar_resumen(update, context)

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
    
    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False  
        return await mostrar_resumen(update, context)

    await update.message.reply_text("Introduce tu número de cédula, sin agregar puntos ni \"V-\". ej: 12345678", reply_markup=teclado_corregir())
    return CEDULA

async def cedula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu apellido completo nuevamente:", reply_markup=teclado_corregir())
        return APELLIDO
    
    texto = update.message.text.strip()

    if not texto.isdigit() or len(texto) < 8:
        await update.message.reply_text("⚠️ Por favor, introduce un número de cédula válido. Recuerda que solo debe contener números y tener al menos 8 dígitos.")
        return CEDULA
    context.user_data['cedula'] = texto  # Guardamos la cédula en user_data

    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False  
        return await mostrar_resumen(update, context)

    await update.message.reply_text("Introduce la organización a la que perteneces:", reply_markup=teclado_corregir())
    return ORGANIZACION

async def organizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu cédula nuevamente:")
        return CEDULA
    
    context.user_data['organizacion'] = texto  # Guardamos la organización en user_data

    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False  
        return await mostrar_resumen(update, context)

    await update.message.reply_text("Escribe tu correo electrónico:", reply_markup=teclado_corregir())
    return CORREO

def validar_correo(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$" # Expresión regular para validar correos
    return re.match(patron, correo) is not None

async def correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto == "↩️ Corregir anterior":
        await update.message.reply_text("Escribe tu organización nuevamente:", reply_markup=teclado_corregir())
        return ORGANIZACION

    if not validar_correo(texto):
        await update.message.reply_text("⚠️ Formato de correo electrónico inválido. Inténtalo de nuevo.")
        return CORREO
    
    context.user_data['correo'] = texto # Guardamos el correo en user_data

    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False  
        return await mostrar_resumen(update, context)

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

    context.user_data['telefono'] = telefono  # Guardamos el teléfono en user_data

    # Validar que comience con 04 y tenga 11 dígitos
    if not telefono.startswith("04") or len(telefono) != 11 or not telefono.isdigit():
        await update.message.reply_text("❌ Número inválido. Procura que comience con '04' y tener 11 dígitos.\nEjemplo: 04121234567")
        return TELEFONO

    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False  
        return await mostrar_resumen(update, context)

    await update.message.reply_text("📅 Escribe tu fecha de nacimiento en formato DD/MM/AAAA:", reply_markup=ReplyKeyboardRemove())
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

    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False  
        return await mostrar_resumen(update, context)

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

    if context.user_data.get("modificando_desde_resumen"):
        context.user_data["modificando_desde_resumen"] = False  
        return await mostrar_resumen(update, context)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:5000/estados") as response:
                estados = await response.json()

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
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:5000/municipios/{texto}") as response:
                municipios = await response.json()

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
        estados = await obtener_opciones("estado")
        await update.message.reply_text("Selecciona tu estado nuevamente:", reply_markup=teclado_dinamico(estados))
        return ESTADO

    context.user_data["municipio"] = texto

    estado = context.user_data["estado"]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:5000/parroquias/{estado}/{texto}") as response:
                parroquias = await response.json()

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
        municipios = await obtener_opciones("municipio", estado=estado)
        await update.message.reply_text("Selecciona tu municipio nuevamente:", reply_markup=teclado_dinamico(municipios))
        return MUNICIPIO

    context.user_data["parroquia"] = texto
    return await mostrar_resumen(update, context)

async def mostrar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resumen = f"""
        📋 *Resumen de registro:*

        👤 *Nombre:* {context.user_data.get('nombre')}
        👥 *Apellido:* {context.user_data.get('apellido')}
        🪪 *Cédula:* {context.user_data.get('cedula')}
        🏢 *Organización:* {context.user_data.get('organizacion')}
        📧 *Correo:* {context.user_data.get('correo')}
        📱 *Teléfono:* {context.user_data.get('telefono')}
        📅 *Fecha de nacimiento:* {context.user_data.get('fecha_nac')}
        ⚧ *Sexo:* {context.user_data.get('sexo')}
        🗺️ *Estado:* {context.user_data.get('estado')}
        🏘️ *Municipio:* {context.user_data.get('municipio')}
        📍 *Parroquia:* {context.user_data.get('parroquia')}

        ¿Deseas confirmar este registro?
    """
    await update.message.reply_text("Información completada ✅. Confirma si los datos son correctos.", reply_markup=ReplyKeyboardRemove())

    await update.message.reply_text(resumen, reply_markup=resumen_botones_edicion(), parse_mode="Markdown")
    return RESUMEN

# ***Botones para estado, municipio y parroquia cuando se modifican***
async def mostrar_teclado_dinamico(update: Update, context: ContextTypes.DEFAULT_TYPE, campo: str):
    query = update.callback_query
    await query.answer()

    textos_introductorios = {
        "estado": "🔁 Corrigiendo campo: *Estado*.",
        "municipio": "🔁 Corrigiendo campo: *Municipio*.",
        "parroquia": "🔁 Corrigiendo campo: *Parroquia*."
    }

    await query.edit_message_text(textos_introductorios.get(campo, "⚠️ Campo no soportado."), parse_mode="Markdown")

    # Carga de opciones según campo
    if campo == "estado":
        opciones = await obtener_opciones("estado")
    elif campo == "municipio":
        estado = context.user_data.get("estado")
        opciones = await obtener_opciones("municipio", estado=estado)
    elif campo == "parroquia":
        estado = context.user_data.get("estado")
        municipio = context.user_data.get("municipio")
        opciones = await obtener_opciones("parroquia", estado=estado, municipio=municipio)
    else:
        await query.edit_message_text("❌ Error: campo no reconocido.")
        return RESUMEN

    # Envío de teclado dinámico
    await query.message.reply_text(f"Elige tu {campo}:", reply_markup=teclado_dinamico(opciones))

    # Retorno al estado correspondiente del flujo
    return {
        "estado": ESTADO,
        "municipio": MUNICIPIO,
        "parroquia": PARROQUIA
    }[campo]

async def manejar_callback_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion = query.data

    redireccion = {
        "corregir_nombre": NOMBRE,
        "corregir_apellido": APELLIDO,
        "corregir_cedula": CEDULA,
        "corregir_organizacion": ORGANIZACION,
        "corregir_correo": CORREO,
        "corregir_telefono": TELEFONO,
        "corregir_fecha": FECHA_NAC,
        "corregir_sexo": SEXO,
        "corregir_estado": ESTADO,
        "corregir_municipio": MUNICIPIO,
        "corregir_parroquia": PARROQUIA
    }

    if accion == "confirmar":
        datos = context.user_data.copy()
        datos["id_usuario"] = update.effective_user.id
        print(f"Datos a enviar: {datos}")  # Debugging
        print(f"id_usuario: {datos['id_usuario']}")  # Debugging
        try:
            # respuesta = requests.post("http://localhost:5000/registrar", json=datos)
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:5000/registrar", json=datos) as respuesta:
                    if respuesta.status in [200, 201]:
                        await query.edit_message_text("✅ ¡Registro completado con éxito!")
                    else:
                        await query.edit_message_text("⚠️ Hubo un error al guardar tus datos.")
        except:
            await query.edit_message_text("❌ No se pudo conectar con el servidor.")
        return ConversationHandler.END

    if accion == "cancelar":
        return await cancelar(update, context)
    
    if accion in ["corregir_estado", "corregir_municipio", "corregir_parroquia"]:
        campo = accion.replace("corregir_", "")
        return await mostrar_teclado_dinamico(update, context, campo)

    if accion in redireccion:
        context.user_data["modificando_desde_resumen"] = True
        campo_legible = accion.replace("corregir_", "").replace("_", " ").capitalize()
        await query.edit_message_text(f"🔁 Corrigiendo campo: *{campo_legible}*.\nPor favor, ingresa el nuevo dato:", parse_mode="Markdown")
        return redireccion[accion]

    await query.edit_message_text("❌ Opción inválida. Usa los botones.")
    return RESUMEN


# Flujo del bot
registro_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nombre)],
        APELLIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, apellido)],
        CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, cedula)],
        ORGANIZACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, organizacion)],
        CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, correo)],
        TELEFONO: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), telefono)],
        FECHA_NAC: [MessageHandler(filters.TEXT & ~filters.COMMAND, fecha_nac)],
        SEXO: [MessageHandler(filters.TEXT & ~filters.COMMAND, sexo)],
        ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, estado)],
        MUNICIPIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, municipio)],
        PARROQUIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, parroquia)],
        RESUMEN: [CallbackQueryHandler(manejar_callback_resumen)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar),
               CallbackQueryHandler(cancelar, pattern="^cancelar$")],
    per_message=False
)

# Iniciar aplicación
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(registro_handler)
    app.add_handler(evento_handler)
    app.run_polling()