from telegram.ext import ApplicationBuilder
from Controladores.registro import *
from Controladores.asistencia import *
from config import TOKEN

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(registro_handler)
    app.add_handler(evento_handler)
    app.run_polling()