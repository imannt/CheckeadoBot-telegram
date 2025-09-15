from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

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

def teclado_dinamico(opciones):
    botones = [KeyboardButton(opcion) for opcion in opciones]
    agrupados = [botones[i:i+2] for i in range(0, len(botones), 2)]
    opciones = agrupados + [["↩️ Corregir anterior"]]
    return ReplyKeyboardMarkup(opciones, one_time_keyboard=True, resize_keyboard=True)