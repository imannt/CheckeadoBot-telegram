from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

# 🔌 Conexión a base principal: fundacion_eventos
conexion_main = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # Reemplaza si tienes contraseña
    database="fundacion_eventos"
)

# 🔌 Conexión a base territorial: geo_venezuela
conexion_geo = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="geo_venezuela"
)

# 🧠 Ruta: verificar si participante existe
@app.route("/verificar/<int:id_usuario>", methods=["GET"])
def verificar_usuario(id_usuario):
    cursor = conexion_main.cursor(dictionary=True)
    cursor.execute("SELECT nombre FROM participante WHERE id_participante = %s", (id_usuario,))
    resultado = cursor.fetchone()

    if resultado:
        return jsonify({"registrado": True, "nombre": resultado["nombre"]})
    else:
        return jsonify({"registrado": False})

# Ruta: registrar nuevo participante
from mysql.connector import Error

@app.route("/registrar", methods=["POST"])
def registrar_participante():
    try:
        datos = request.json
        print("📦 Datos recibidos:", datos)

        # Aquí va tu lógica de inserción, por ejemplo:
        cursor = conexion_main.cursor()
        cursor.execute("""
            INSERT INTO participante 
            (id_participante, nombre, apellido, cedula, correo, telefono, fecha_nac, sexo, estado, municipio, parroquia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datos["id_participante"],
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
        conexion_geo.commit()
        cursor.close()
        return jsonify({"mensaje": "Registro exitoso"}), 201

    except Error as err:
        print(f"❌ Error MySQL: {err}")
        return jsonify({"error": str(err)}), 500

    except Exception as e:
        print(f"⚠️ Error general: {e}")
        return jsonify({"error": str(e)}), 500

# Ruta: obtener todos los estados
@app.route("/estados", methods=["GET"])
def obtener_estados():
    cursor = conexion_geo.cursor(dictionary=True)
    cursor.execute("SELECT estado FROM estados ORDER BY estado")
    resultados = [r["estado"] for r in cursor.fetchall()]
    return jsonify(resultados)

# Ruta: obtener municipios según estado
@app.route("/municipios/<estado>", methods=["GET"])
def obtener_municipios(estado):
    cursor = conexion_geo.cursor(dictionary=True)
    cursor.execute("SELECT id_estado FROM estados WHERE estado = %s", (estado,))
    estado_data = cursor.fetchone()

    if not estado_data:
        return jsonify({"error": "Estado no encontrado"}), 404

    id_estado = estado_data["id_estado"]
    cursor.execute("SELECT municipio FROM municipios WHERE id_estado = %s ORDER BY municipio", (id_estado,))
    municipios = [m["municipio"] for m in cursor.fetchall()]
    return jsonify(municipios)

# Ruta: obtener parroquias según municipio
@app.route("/parroquias/<estado>/<municipio>", methods=["GET"])
def obtener_parroquias(estado, municipio):
    cursor = conexion_geo.cursor(dictionary=True)

    # 1. Buscar id del estado
    cursor.execute("SELECT id_estado FROM estados WHERE estado = %s", (estado,))
    estado_data = cursor.fetchone()

    if not estado_data:
        cursor.close()
        return jsonify({"error": "Estado no encontrado"}), 404

    id_estado = estado_data["id_estado"]
    cursor.fetchall()  # Limpia el buffer antes de ejecutar otra consulta

    # 2. Buscar municipio exacto dentro del estado
    cursor.execute("""
        SELECT id_municipio FROM municipios 
        WHERE municipio = %s AND id_estado = %s
    """, (municipio, id_estado))
    municipio_data = cursor.fetchone()

    if not municipio_data:
        cursor.close()
        return jsonify({"error": "Municipio no encontrado en ese estado"}), 404

    id_municipio = municipio_data["id_municipio"]
    cursor.fetchall()  # Limpia el buffer antes de ejecutar otra consulta

    # 3. Buscar parroquias que pertenecen a ese municipio
    cursor.execute("""
        SELECT parroquia FROM parroquias 
        WHERE id_municipio = %s 
        ORDER BY parroquia
    """, (id_municipio,))
    parroquias = [p["parroquia"] for p in cursor.fetchall()]

    cursor.close()
    return jsonify(parroquias)


# Ejecutar el servidor
if __name__ == "__main__":
    app.run(debug=True, port=5000)