from datetime import datetime
from flask import jsonify, request

# Llamar al siguiente turno de forma independiente por caja
@administrador_bp.route('/llamar-siguiente/<int:caja_id>', methods=['POST'])
def llamar_siguiente(caja_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Busca el turno pendiente más antiguo sin importar lo que hagan las otras cajas
    cursor.execute("SELECT id, numero FROM turnos WHERE estado = 'pendiente' ORDER BY fecha_creacion ASC LIMIT 1")
    turno = cursor.fetchone()
    
    if turno:
        turno_id, numero = turno
        caja_nombre = f"Caja {caja_id}"
        
        cursor.execute(
            "UPDATE turnos SET estado = 'llamando', caja = ? WHERE id = ?",
            (caja_nombre, turno_id)
        )
        conexion.commit()
        conexion.close()
        return jsonify({"status": "success", "numero": numero, "caja": caja_nombre})
    
    conexion.close()
    return jsonify({"status": "empty", "message": "No hay turnos pendientes"})

# Finalizar la atención de la caja actual para liberar su estado
@administrador_bp.route('/finalizar-turno/<int:caja_id>', methods=['POST'])
def finalizar_turno(caja_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    caja_nombre = f"Caja {caja_id}"
    
    cursor.execute(
        "UPDATE turnos SET estado = 'atendido' WHERE caja = ? AND estado = 'llamando'",
        (caja_nombre,)
    )
    conexion.commit()
    conexion.close()
    return jsonify({"status": "success"})

# Botón de limpieza: reinicia los registros y el conteo vuelve a empezar en 1
@administrador_bp.route('/reiniciar-turnos', methods=['POST'])
def reiniciar_turnos():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Vacía la tabla para reiniciar el ciclo diario
    cursor.execute("DELETE FROM turnos")
    conexion.commit()
    conexion.close()
    return jsonify({"status": "success", "message": "Turnos restablecidos a cero"})

# API que alimenta el tiempo real en todas las ventanas
@administrador_bp.route('/api/estado-actual', methods=['GET'])
def api_estado_actual():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Conteo de pacientes en espera
    cursor.execute("SELECT COUNT(*) FROM turnos WHERE estado = 'pendiente'")
    pendientes = cursor.fetchone()[0]
    
    # Turnos activos que están llamando las cajas simultáneamente
    cursor.execute("SELECT caja, numero FROM turnos WHERE estado = 'llamando'")
    llamando_raw = cursor.fetchall()
    cajas_llamando = [{"caja": row[0], "numero": row[1]} for row in llamando_raw]
    
    conexion.close()
    return jsonify({
        "pacientes_en_espera": pendientes,
        "cajas_llamando": cajas_llamando
    })

# Creación de turnos asegurando que inicie en 1 cada día
@cliente_bp.route('/crear-turno', methods=['POST'])
def crear_turno():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    
    # Obtiene el número máximo creado hoy para sumar 1, o inicia en 1 si está vacío
    cursor.execute("SELECT MAX(numero) FROM turnos WHERE DATE(fecha_creacion) = ?", (fecha_hoy,))
    ultimo = cursor.fetchone()
    siguiente_numero = 1 if not ultimo or ultimo[0] is None else ultimo[0] + 1
    
    cursor.execute(
        "INSERT INTO turnos (numero, estado, fecha_creacion) VALUES (?, 'pendiente', ?)",
        (siguiente_numero, datetime.now())
    )
    conexion.commit()
    conexion.close()
    
    return jsonify({"status": "success", "numero": siguiente_numero})