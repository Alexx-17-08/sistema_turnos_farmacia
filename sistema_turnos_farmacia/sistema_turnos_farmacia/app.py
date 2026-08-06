from datetime import datetime
import sqlite3
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = 'clave_secreta_farmacia_turnos'


def obtener_conexion():
  conexion = sqlite3.connect('farmacia.db')
  conexion.row_factory = sqlite3.Row
  return conexion


def inicializar_base_de_datos():
  try:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS turnos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL,
                tipo TEXT NOT NULL,
                estado TEXT NOT NULL,
                caja TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_llamado TIMESTAMP
            )
        ''')
    # Intentar agregar la columna si la base de datos ya existía previamente
    try:
      cursor.execute('ALTER TABLE turnos ADD COLUMN fecha_llamado TIMESTAMP')
      conexion.commit()
    except sqlite3.OperationalError:
      pass  # La columna ya existe

    conexion.commit()
    conexion.close()
  except Exception as e:
    print(f'Error al inicializar la base de datos: {e}')


inicializar_base_de_datos()


# --- RUTAS DE NAVEGACIÓN Y LOGIN ---


@app.route('/')
@app.route('/solicitar')
def solicitar_turno():
  return render_template('cliente/solicitar.html')


@app.route('/sala-espera')
def sala_espera():
  return render_template('cliente/sala_espera.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
  if request.method == 'POST':
    usuario = request.form.get('usuario')
    password = request.form.get('password')

    if usuario == 'admin123' and password == 'admin123':
      session['admin_logged'] = True
      return redirect(url_for('admin_panel'))
    else:
      return render_template(
          'acceso/login.html', error='Credenciales incorrectas'
      )

  if not session.get('admin_logged'):
    return render_template('acceso/login.html')

  return render_template('administrador/panel.html')


@app.route('/admin/logout')
def admin_logout():
  session.pop('admin_logged', None)
  return redirect(url_for('admin_panel'))


# --- APIS Y LÓGICA DE TURNOS ---


@app.route('/api/estado-actual', methods=['GET'])
def api_estado_actual():
  try:
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM turnos WHERE estado = 'pendiente'")
    res_pendientes = cursor.fetchone()
    pendientes = res_pendientes[0] if res_pendientes else 0

    # Ordenar estrictamente por la hora en que fueron llamados (el más reciente al final)
    cursor.execute(
        "SELECT caja, numero FROM turnos WHERE estado = 'llamando' ORDER BY"
        ' fecha_llamado ASC'
    )
    llamando_raw = cursor.fetchall()
    cajas_llamando = [
        {'caja': row['caja'], 'numero': row['numero']} for row in llamando_raw
    ]

    conexion.close()
    return jsonify({
        'pacientes_en_espera': pendientes,
        'cajas_llamando': cajas_llamando,
    })
  except Exception as e:
    return jsonify(
        {'pacientes_en_espera': 0, 'cajas_llamando': [], 'error': str(e)}
    )


@app.route('/crear-turno/<tipo>', methods=['POST'])
def crear_turno(tipo):
  try:
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT numero FROM turnos WHERE tipo = ? ORDER BY id DESC LIMIT 1",
        (tipo,),
    )
    ultimo = cursor.fetchone()

    prefix = 'P' if tipo == 'prioritario' else 'G'
    if ultimo and ultimo['numero']:
      try:
        num_actual = int(ultimo['numero'].split('-')[1]) + 1
      except (IndexError, ValueError):
        num_actual = 1
    else:
      num_actual = 1

    nuevo_numero = f'{prefix}-{num_actual}'

    cursor.execute(
        'INSERT INTO turnos (numero, tipo, estado) VALUES (?, ?, ?)',
        (nuevo_numero, tipo, 'pendiente'),
    )
    conexion.commit()
    conexion.close()

    return jsonify({'status': 'success', 'numero': nuevo_numero})
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/llamar-siguiente/<int:caja_id>', methods=['POST'])
def llamar_siguiente(caja_id):
  try:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    caja_nombre = f'Caja {caja_id}'

    # Limpiar turnos anteriores de esta misma caja si quedaron colgados
    cursor.execute(
        "UPDATE turnos SET estado = 'atendido' WHERE caja = ? AND estado ="
        " 'llamando'",
        (caja_nombre,),
    )

    # Buscar el siguiente turno pendiente (prioritarios 'P' primero)
    cursor.execute(
        "SELECT id, numero FROM turnos WHERE estado = 'pendiente' ORDER BY"
        " CASE WHEN tipo = 'prioritario' THEN 1 ELSE 2 END ASC, fecha_creacion ASC"
        ' LIMIT 1'
    )
    turno = cursor.fetchone()

    if turno:
      turno_id, numero = turno['id'], turno['numero']

      # Asignar estado llamando y registrar la hora exacta del llamado
      cursor.execute(
          'UPDATE turnos SET estado = ?, caja = ?, fecha_llamado ='
          ' CURRENT_TIMESTAMP WHERE id = ?',
          ('llamando', caja_nombre, turno_id),
      )
      conexion.commit()
      conexion.close()
      return jsonify(
          {'status': 'success', 'numero': numero, 'caja': caja_nombre}
      )

    conexion.close()
    return jsonify({'status': 'empty', 'message': 'No hay turnos pendientes'})
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/finalizar-turno/<int:caja_id>', methods=['POST'])
def finalizar_turno(caja_id):
  conexion = obtener_conexion()
  cursor = conexion.cursor()
  caja_nombre = f'Caja {caja_id}'
  cursor.execute(
      "UPDATE turnos SET estado = 'atendido' WHERE caja = ? AND estado ="
      " 'llamando'",
      (caja_nombre,),
  )
  conexion.commit()
  conexion.close()
  return jsonify({'status': 'success'})


@app.route('/marcar-ausente/<int:caja_id>', methods=['POST'])
def marcar_ausente(caja_id):
  conexion = obtener_conexion()
  cursor = conexion.cursor()
  caja_nombre = f'Caja {caja_id}'
  cursor.execute(
      "UPDATE turnos SET estado = 'ausente' WHERE caja = ? AND estado ="
      " 'llamando'",
      (caja_nombre,),
  )
  conexion.commit()
  conexion.close()
  return jsonify({'status': 'success'})


@app.route('/reiniciar-turnos', methods=['POST'])
def reiniciar_turnos():
  conexion = obtener_conexion()
  cursor = conexion.cursor()
  cursor.execute('DELETE FROM turnos')
  conexion.commit()
  conexion.close()
  return jsonify({'status': 'success'})


if __name__ == '__main__':
  app.run(debug=True)