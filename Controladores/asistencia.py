from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import aiohttp
import json

# ESTADOS para el flujo de registro de evento
EVENTO_CLAVE, EVENTO_CONFIRMAR = range(2)

# Flujo para registrarse en un evento por clave
async def registrar_evento_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia el flujo de conversación para registrarse en un evento.
    Primero, verifica si el usuario está registrado. Si no, le pide que use /start.
    """
    user_id = update.effective_user.id
    
    try:
        # Usamos aiohttp 
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:5000/verificar/{user_id}") as respuesta:
                resultado = await respuesta.json()
                registrado = resultado.get("registrado", False)
    except Exception as e:
        # Maneja cualquier error de conexión a la API
        print(f"Error al conectar con la API de verificación: {e}")
        registrado = False

    if registrado:
        # El usuario está registrado, continuamos con el flujo normal
        await update.message.reply_text("Por favor, ingresa la clave del evento:")
        return EVENTO_CLAVE
    else:
        # El usuario no está registrado, se lo notificamos y terminamos la conversación
        await update.message.reply_text("👋 *Parece que aún no estás registrado.*\nPor favor, usa el comando /start para iniciar el proceso de registro.", parse_mode="Markdown")
        return ConversationHandler.END

async def evento_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja la clave del evento ingresada por el usuario, busca el evento
    en la API y muestra los detalles para confirmación.
    """
    clave = update.message.text.strip()
    context.user_data["clave_evento"] = clave

    try:
        # Petición a la API para obtener los detalles del evento
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:5000/evento/{clave}") as response:
                evento_data = await response.json()

                if response.status == 200:
                    context.user_data["evento_info"] = evento_data
                    
                    # Mensaje con los detalles del evento
                    mensaje = f"""*Detalles del Evento:*\n
*Nombre del evento:* {evento_data.get('nombre')}
*Fecha:* {evento_data.get('fecha')}
*Hora:* {evento_data.get('hora_inicio')} - {evento_data.get('hora_fin')}
*Modalidad:* {evento_data.get('modalidad')}
*Descripción:* {evento_data.get('descripcion')}
*Ubicación:* {evento_data.get('ubicacion')}

¿Deseas registrarte como asistente a este evento?
"""

                    # Botones para confirmar o cancelar
                    keyboard = [[InlineKeyboardButton("Sí, registrarme", callback_data="asistir")],
                                [InlineKeyboardButton("No, cancelar", callback_data="cancelar_evento")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode="Markdown")
                    return EVENTO_CONFIRMAR
                else:
                    # Evento no encontrado
                    await update.message.reply_text(f"❌ No se encontró ningún evento con la clave '{clave}'. Por favor, intenta de nuevo.")
                    return EVENTO_CLAVE
    except Exception as e:
        # Manejo de errores de conexión o API
        await update.message.reply_text("❌ Ocurrió un error al buscar el evento. Por favor, intenta nuevamente.")
        return ConversationHandler.END

async def evento_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja la confirmación del usuario para registrarse en el evento.
    Envía la solicitud de registro a la API.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "asistir":
        evento_info = context.user_data.get("evento_info")
        id_evento = evento_info.get("id_evento")
        id_usuario = update.effective_user.id

        try:
            payload = {
                "id_usuario": id_usuario,
                "id_evento": id_evento
            }
            
            # Petición a la API para registrar al usuario
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:5000/asistencia", json=payload) as respuesta:
                    resultado = await respuesta.json()

                    print(f"resultado: {resultado}")  # Debugging

                    fecha_registro = resultado.get('fecha_registro')
                    hora_registro = resultado.get('hora_registro')
                    nombre_evento = evento_info.get('nombre')

                    if respuesta.status in [201, 200]:
                        await query.edit_message_text(f"""{resultado.get('mensaje')}\n 
*Detalles del registro:*\n
*Evento:* {nombre_evento}
*Fecha de registro:* {fecha_registro}
*Hora de registro:* {hora_registro}
""", parse_mode="Markdown")
                    else:
                        error = resultado.get("error", "Error desconocido.")
                        await query.edit_message_text(f"❌ Hubo un problema: {error}")

        except Exception as e:
            await query.edit_message_text(f"❌ Ocurrió un error inesperado al registrarte. Intente más tarde.")
            
        finally:
            return ConversationHandler.END
    else: # Opción "No, cancelar"
        await query.edit_message_text("Registro de evento cancelado.\nPuedes usar /asistencia para registrarte en un evento")
        return ConversationHandler.END

async def cancelar_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Función de fallback para cancelar el flujo de registro de evento.
    """
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operación cancelada. Puedes usar /asistencia para registrarte en un evento.")
    else:
        await update.message.reply_text("Operación cancelada. Puedes usar /asistencia para registrarte en un evento.")
    return ConversationHandler.END

# registro de eventos
evento_handler = ConversationHandler(
    entry_points=[CommandHandler("asistencia", registrar_evento_command)],
    states={
        EVENTO_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, evento_clave)],
        EVENTO_CONFIRMAR: [CallbackQueryHandler(evento_confirmar)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar_evento)],
    per_message=False
)
