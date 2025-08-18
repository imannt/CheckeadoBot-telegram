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
import requests
import json

# NUEVOS ESTADOS para el flujo de registro de evento
EVENTO_CLAVE, EVENTO_CONFIRMAR = range(2)

# 🆕 Flujo para registrarse en un evento por clave
async def registrar_evento_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia el flujo de conversación para registrarse en un evento.
    Pide al usuario que ingrese la clave del evento.
    """
    await update.message.reply_text("Por favor, ingresa la clave del evento:")
    return EVENTO_CLAVE

async def evento_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja la clave del evento ingresada por el usuario, busca el evento
    en la API y muestra los detalles para confirmación.
    """
    clave = update.message.text.strip()
    context.user_data["clave_evento"] = clave

    try:
        # Petición a la API para obtener los detalles del evento
        respuesta = requests.get(f"http://localhost:5000/evento/{clave}")
        evento_data = respuesta.json()

        if respuesta.status_code == 200:
            context.user_data["evento_info"] = evento_data
            
            # Mensaje con los detalles del evento
            mensaje = f"""*Detalles del Evento:*\n
*Nombre del evento:* {evento_data.get('nombre')}.
*Fecha:* {evento_data.get('fecha')}.
*Hora:* {evento_data.get('hora_inicio')} - {evento_data.get('hora_fin')}
*Modalidad:* {evento_data.get('modalidad')}.
*Descripción:* {evento_data.get('descripcion')}.

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
            respuesta = requests.post("http://localhost:5000/asistencia", json=payload)
            resultado = respuesta.json()

            print(f"resultado: {resultado}")  # Debugging

            fecha_registro = resultado.get('fecha_registro')
            hora_registro = resultado.get('hora_registro')
            nombre_evento = evento_info.get('nombre')

            if respuesta.status_code in [201, 200]:
                await query.edit_message_text(f"""
                    {resultado.get('mensaje')}\n *Detalles del registro:*\n
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

# Nuevo handler para el registro de eventos
evento_handler = ConversationHandler(
    entry_points=[CommandHandler("asistencia", registrar_evento_command)],
    states={
        EVENTO_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, evento_clave)],
        EVENTO_CONFIRMAR: [CallbackQueryHandler(evento_confirmar)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar_evento)],
    per_message=False
)
