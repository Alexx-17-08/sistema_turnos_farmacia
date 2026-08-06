from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_super_segura_farmacia'
socketio = SocketIO(app)

# Estructuras en memoria para el manejo de turnos
turnos_espera = []         # Cola de turnos pendientes
turnos_en_atencion = {}    # Registro por caja: {'1': {'ticket': 'G-001', 'estado': 'en_atencion', 'caja': '1'}, ...}
contador_general = 0
contador_prioritario = 0

@app.route('/')
def index():
    return redirect(url_for('sala_espera'))

@app.route('/solicitar')
def solicitar():
    return render_template('cliente/solicitar.html')

@app.route('/sala_espera')
def sala_espera():
    return render_template('cliente/sala_espera.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Capturamos de forma flexible cualquier nombre que use el formulario HTML
        username = request.form.get('username') or request.form.get('usuario') or request.form.get('user')
        password = request.form.get('password') or request.form.get('pass') or request.form.get('contrasena')
        
        # Credenciales temporales de acceso
        if username == 'admin123' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('acceso/login.html', error="Credenciales incorrectas")
            
    return render_template('acceso/login.html')

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return render_template('administrador/panel.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))


# --- EVENTOS DE TIEMPO REAL (SOCKET.IO) ---

@socketio.on('solicitar_turno')
def handle_solicitar_turno(data):
    global contador_general, contador_prioritario
    tipo = data.get('tipo')
    
    if tipo == 'general':
        contador_general += 1
        ticket_id = f"G-{contador_general:03d}"
    else:
        contador_prioritario += 1
        ticket_id = f"P-{contador_prioritario:03d}"
        
    nuevo_turno = {
        'ticket': ticket_id,
        'tipo': tipo,
        'estado': 'espera'
    }
    
    turnos_espera.append(nuevo_turno)
    
    # Responder únicamente al tótem que generó el ticket
    emit('ticket_creado', {'ticket': ticket_id})
    
    # Actualizar a todas las pantallas conectadas
    sincronizar_estados()


@socketio.on('llamar_siguiente')
def handle_llamar_siguiente(data):
    caja = data.get('caja')
    
    if turnos_espera:
        siguiente = turnos_espera.pop(0)
        siguiente['estado'] = 'en_atencion'
        siguiente['caja'] = caja
        turnos_en_atencion[caja] = siguiente
        
        sincronizar_estados()


@socketio.on('cambiar_estado')
def handle_cambiar_estado(data):
    caja = data.get('caja')
    estado = data.get('estado') # 'atendido' o 'ausente'
    
    if caja in turnos_en_atencion and turnos_en_atencion[caja]:
        if estado == 'atendido':
            turnos_en_atencion[caja]['estado'] = 'finalizado'
        elif estado == 'ausente':
            turnos_en_atencion[caja]['estado'] = 'ausente'
            
        # Liberar la caja
        turnos_en_atencion[caja] = None
        
        sincronizar_estados()


def sincronizar_estados():
    # Obtener el turno actual relevante para la sala de espera general
    turno_activo_general = None
    for caja, turno in turnos_en_atencion.items():
        if turno and turno.get('estado') == 'en_atencion':
            turno_activo_general = turno
            break

    # 1. Actualizar la Sala de Espera
    socketio.emit('actualizar_pantalla', {
        'en_espera': len(turnos_espera),
        'turno_actual': turno_activo_general
    })

    # 2. Actualizar los paneles de los operadores en cada caja
    for caja in ['1', '2', '3', '4', '5']:
        turno_caja = turnos_en_atencion.get(caja)
        socketio.emit('actualizar_panel_operador', {
            'en_espera': len(turnos_espera),
            'caja_actualizada': caja,
            'turno_actual': turno_caja
        })


if __name__ == '__main__':
    socketio.run(app, debug=True)