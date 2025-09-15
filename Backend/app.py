from flask import Flask, jsonify, request
import mysql.connector.pooling
from mysql.connector import Error
from datetime import datetime

from config import *

# from dotenv import load_dotenv
# import os

# Formatear la fecha y hora antes de devolver la respuesta
dias_semana = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

load_dotenv()
app = Flask(__name__)

# Conexión a base principal: fundacion_eventos
conexion_main = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME_MAIN
}

pool_main = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="pool_main",
    pool_size= 30,
    **conexion_main
)

# Conexión a base territorial: geo_venezuela
conexion_geo = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME_GEO")
}

pool_main_geo = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="pool_main_geo",
    pool_size= 30,
    **conexion_geo
)

# Ruta: verificar si usuario existe
@app.route("/verificar/<int:id_usuario>", methods=["GET"])
def verificar_usuario(id_usuario):
    cnx = pool_main.get_connection()
    cursor = cnx.cursor(dictionary=True)

    cursor.execute("SELECT nombre FROM usuario WHERE id_usuario = %s", (id_usuario,))
    resultado = cursor.fetchone()

    cursor.close()
    cnx.close()

     # Si el usuario existe, devuelve su nombre; si no, devuelve un mensaje de error
    if resultado:
        return jsonify({"registrado": True, "nombre": resultado["nombre"]})
    else:
        return jsonify({"registrado": False})

# Ruta: registrar nuevo participante

@app.route("/registrar", methods=["POST"])
def registrar_participante():
    datos = request.json
    id_usuario = datos.get("id_usuario")
    cnx = None

    try:
        cnx = pool_main.get_connection()
        cursor = cnx.cursor()
        cnx.start_transaction()

        # Paso 0: Verificar si el usuario ya existe para evitar duplicados
        cursor.execute("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (id_usuario,))
        usuario_existente = cursor.fetchone()

        if usuario_existente:
            cnx.rollback()
            return jsonify({"error": "El usuario ya está registrado."}), 400
        
        # Paso 1: Verificar y/o insertar la organización
        organizacion_nombre = datos.get("organizacion")
        id_organizacion = None
        
        # Buscar si la organización ya existe
        cursor.execute("SELECT id_organizacion FROM organizacion WHERE nombre = %s", (organizacion_nombre,))
        org_data = cursor.fetchone()

        if org_data:
            id_organizacion = org_data[0]
        else:
            # Si la organización no existe, la insertamos y obtenemos su ID
            cursor.execute("INSERT INTO organizacion (nombre) VALUES (%s)", (organizacion_nombre,))
            id_organizacion = cursor.lastrowid # Obtiene el último ID insertado

        # Paso 2: Insertar el usuario en la tabla `usuario`

        cursor.execute("""
            INSERT INTO usuario 
            (id_usuario, id_usertelegram, nombre, apellido, cedula, correo, telefono, fecha_nac, sexo, estado, municipio, parroquia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datos["id_usuario"],
            datos["id_usuario"],
            datos["nombre"],
            datos["apellido"],
            datos["cedula"],
            datos["correo"],
            datos["telefono"],
            datos["fecha_nac"],
            datos["sexo"],
            datos["estado"],
            datos["municipio"],
            datos["parroquia"]
        ))

        # Paso 3: Obtener el ID del rol de "Participante"
        cursor.execute("SELECT id_rol FROM rol WHERE nombre = 'Participante'")
        id_rol_participante = cursor.fetchone()
        
        if not id_rol_participante:
            raise Exception("Rol 'Participante' no encontrado en la base de datos.")
            
        id_rol = id_rol_participante[0]

        # Paso 4: Asociar al usuario con la organización y el rol
        cursor.execute("""
            INSERT INTO usuario_rol (id_usuario, id_organizacion, id_rol)
            VALUES (%s, %s, %s)
        """, (datos["id_usuario"], id_organizacion, id_rol))

        cnx.commit()
        cursor.close()

        return jsonify({"mensaje": "Registro exitoso"}), 201

    except Error as err:
        if cnx and cnx.is_connected():
            cnx.rollback()
        print(f"❌ Error MySQL: {err}")
        return jsonify({"error": str(err)}), 500

    except Exception as e:
        if cnx and cnx.is_connected():
            cnx.rollback()
        print(f"⚠️ Error general: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cnx and cnx.is_connected():
            cnx.close()


# Ruta: Buscar un evento por su clave de acceso
@app.route("/evento/<clave>", methods=["GET"])
def obtener_evento_por_clave(clave):
    cnx = None
    try:
        cnx = pool_main.get_connection()
        cursor = cnx.cursor(dictionary=True)

        cursor.execute("SELECT id_evento, nombre, fecha, hora_inicio, hora_fin, descripcion, modalidad, ubicacion FROM evento WHERE clave_acceso = %s", (clave,))
        evento = cursor.fetchone()

        if evento:
            # Convertir objetos de tiempo a cadenas de texto para que sean serializables por JSON
            if evento.get('hora_inicio') and evento.get('hora_fin') and evento.get('fecha'):
                fecha_obj = evento['fecha']
                hora_inicio = datetime.strptime(str(evento['hora_inicio']), "%H:%M:%S").time()
                hora_fin = datetime.strptime(str(evento['hora_fin']), "%H:%M:%S").time()

                # Día de la semana en español
                dia_semana = dias_semana[fecha_obj.strftime("%A")]
                # Formato: "Día, DD-MM-YYYY"
                evento['fecha'] = f"{dia_semana}, {fecha_obj.strftime('%d-%m-%Y')}"

                # Formato: "HH:MM AM/PM"
                evento['hora_inicio'] = hora_inicio.strftime("%I:%M %p").replace("AM", "a. m.").replace("PM", "p. m.")
                evento['hora_fin'] = hora_fin.strftime("%I:%M %p").replace("AM", "a. m.").replace("PM", "p. m.")

            return jsonify(evento), 200
        else:
            return jsonify({"error": "Evento no encontrado"}), 404
            
    except Error as err:
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if cnx and cnx.is_connected():
            cursor.close()
            cnx.close()

# Ruta: Registrar un usuario en un evento
@app.route("/asistencia", methods=["POST"])
def registrar_evento():
    cnx = None
    datos = request.json
    id_usuario = datos.get("id_usuario")
    id_evento = datos.get("id_evento")
    
    try:
        if not id_usuario or not id_evento:
            return jsonify({"error": "Faltan datos."}), 400

        cnx = pool_main.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cnx.start_transaction()

        # 1. Obtener la información del evento
        cursor.execute("SELECT fecha, hora_inicio, hora_fin FROM evento WHERE id_evento = %s", (id_evento,))
        evento_info = cursor.fetchone()

        if not evento_info:
            return jsonify({"error": "Evento no encontrado."}), 404

        # 2. Validar la fecha y hora de registro
        fecha_evento = evento_info['fecha']
        hora_inicio_evento = datetime.strptime(str(evento_info['hora_inicio']), "%H:%M:%S").time()
        hora_fin_evento = datetime.strptime(str(evento_info['hora_fin']), "%H:%M:%S").time()

        ahora = datetime.now()
        fecha_actual = ahora.date()
        hora_actual = ahora.time()

        # Validación 1: Fecha del evento
        if fecha_actual < fecha_evento:
            return jsonify({"error": "el registro aún no está disponible. Por favor, intente el día del evento."}), 400	
        if fecha_actual > fecha_evento:
            return jsonify({"error": "el registro para este evento ya ha finalizado."}), 400

        # Validación 2: Hora del evento (solo si la fecha es hoy)
        if not (hora_inicio_evento <= hora_actual <= hora_fin_evento):
            hora_inicio_evento = hora_inicio_evento.strftime("%I:%M %p").replace("AM", "a. m.").replace("PM", "p. m.")
            hora_fin_evento = hora_fin_evento.strftime("%I:%M %p").replace("AM", "a. m.").replace("PM", "p. m.")
            return jsonify({"error": f"se ha caducado el tiempo de registro. Solo está disponible de {hora_inicio_evento} a {hora_fin_evento}"}), 400

        # 3. Verifica si el usuario ya está registrado en este evento
        cursor.execute("SELECT fecha_registro, hora_registro FROM usuario_evento WHERE id_usuario = %s AND id_evento = %s", (id_usuario, id_evento))
        registro_existente = cursor.fetchone()

        if registro_existente:
            mensaje = "📝 Ya estás registrado en este evento."
            fecha_asistencia_str = datetime.strptime(str(registro_existente['fecha_registro']), "%Y-%m-%d").date()
            hora_asistencia_str = datetime.strptime(str(registro_existente['hora_registro']), "%H:%M:%S").time()
            status_code = 200

            print(f"jsonify: {mensaje}, {status_code}")
        else:

            # Si no existe, realiza el registro
            fecha_asistencia_str = fecha_actual
            hora_asistencia_str = hora_actual
            estatus_asistencia = 1
            
            cursor.execute("""
                INSERT INTO usuario_evento (id_usuario, id_evento, estatus_asistencia, fecha_registro, hora_registro )
                VALUES (%s, %s, %s, %s, %s)
            """, (id_usuario, id_evento, estatus_asistencia, fecha_asistencia_str, hora_asistencia_str))

            cnx.commit()
            
            mensaje = "✅ ¡Te has registrado en el evento con éxito!"
            status_code = 201

        dia_semana = dias_semana[fecha_asistencia_str.strftime("%A")]

        # Formatear la fecha y hora antes de devolver la respuesta
        fecha_asistencia_td = f"{dia_semana}, {fecha_asistencia_str.strftime('%d-%m-%Y')}  "
        hora_asistencia_td = hora_asistencia_str.strftime("%I:%M %p").replace("AM", "a. m.").replace("PM", "p. m.")
    
        return jsonify({
            "mensaje": mensaje,
            "fecha_registro": fecha_asistencia_td,
            "hora_registro": hora_asistencia_td
        }), status_code

    except Error as err:
        conexion_main.rollback()
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        conexion_main.rollback()
        return jsonify({"Exception": str(e)}), 500
    finally:
        if cnx and cnx.is_connected():
            cursor.close()
            cnx.close()


# Ruta: obtener todos los estados
@app.route("/estados", methods=["GET"])
def obtener_estados():
    cnx = None
    try:
        cnx = pool_main_geo.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT estado FROM estados ORDER BY estado")
        resultados = [r["estado"] for r in cursor.fetchall()]

        return jsonify(resultados), 200
    except Error as e:
        # Manejo de errores de la base de datos
        print(f"Error de base de datos: {e}")
        return jsonify({"error": "Ocurrió un error en el servidor."}), 500
    except Exception as e:
        # Manejo de cualquier otro error inesperado
        print(f"Error inesperado: {e}")
        return jsonify({"error": "Ocurrió un error inesperado."}), 500
    finally:
        # Asegura que la conexión se cierre y regrese al pool
        if cnx and cnx.is_connected():
            cursor.close()
            cnx.close()

# Ruta: obtener municipios según estado
@app.route("/municipios/<estado>", methods=["GET"])
def obtener_municipios(estado):
    cnx = None
    try:
        # Obtiene una conexión del pool
        cnx = pool_main_geo.get_connection()
        cursor = cnx.cursor(dictionary=True)
        
        # 1. Buscar el id del estado para evitar inyecciones SQL
        cursor.execute("SELECT id_estado FROM estados WHERE estado = %s", (estado,))
        estado_data = cursor.fetchone()

        if not estado_data:
            return jsonify({"error": "Estado no encontrado"}), 404

        id_estado = estado_data["id_estado"]
        
        # 2. Buscar municipios que pertenecen a ese estado
        cursor.execute("SELECT municipio FROM municipios WHERE id_estado = %s ORDER BY municipio", (id_estado,))
        municipios = [m["municipio"] for m in cursor.fetchall()]
        
        return jsonify(municipios), 200
    except Error as e:
        print(f"Error de base de datos: {e}")
        return jsonify({"error": "Ocurrió un error en el servidor."}), 500
    except Exception as e:
        print(f"Error inesperado: {e}")
        return jsonify({"error": "Ocurrió un error inesperado."}), 500
    finally:
        if cnx and cnx.is_connected():
            cursor.close()
            cnx.close()

# Ruta: obtener parroquias según municipio
@app.route("/parroquias/<estado>/<municipio>", methods=["GET"])
def obtener_parroquias(estado, municipio):
    cnx = None
    try:
        # Obtiene una conexión del pool
        cnx = pool_main_geo.get_connection()
        cursor = cnx.cursor(dictionary=True)

        # 1. Buscar id del estado
        cursor.execute("SELECT id_estado FROM estados WHERE estado = %s", (estado,))
        estado_data = cursor.fetchone()

        if not estado_data:
            return jsonify({"error": "Estado no encontrado"}), 404

        id_estado = estado_data["id_estado"]

        # 2. Buscar municipio exacto dentro del estado
        cursor.execute("""
            SELECT id_municipio FROM municipios 
            WHERE municipio = %s AND id_estado = %s
        """, (municipio, id_estado))
        municipio_data = cursor.fetchone()

        if not municipio_data:
            return jsonify({"error": "Municipio no encontrado en ese estado"}), 404

        id_municipio = municipio_data["id_municipio"]

        # 3. Buscar parroquias que pertenecen a ese municipio
        cursor.execute("""
            SELECT parroquia FROM parroquias 
            WHERE id_municipio = %s 
            ORDER BY parroquia
        """, (id_municipio,))
        parroquias = [p["parroquia"] for p in cursor.fetchall()]

        return jsonify(parroquias), 200

    except Error as e:
        print(f"Error de base de datos: {e}")
        return jsonify({"error": "Ocurrió un error en el servidor."}), 500
    except Exception as e:
        print(f"Error inesperado: {e}")
        return jsonify({"error": "Ocurrió un error inesperado."}), 500
    finally:
        if cnx and cnx.is_connected():
            cursor.close()
            cnx.close()

# Ejecutar el servidor
if __name__ == "__main__":
    app.run(debug=True, port=5000)