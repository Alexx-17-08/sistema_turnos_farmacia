from flask import Blueprint, render_template, request, redirect, url_for, session
from database import turnos_db

administrador_bp = Blueprint('administrador', __name__)

# Ruta para el login del farmacéutico
@administrador_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        
        # Credenciales de acceso
        if usuario == 'admin123' and password == 'admin123':
            session['admin_logueado'] = True
            return redirect(url_for('administrador.panel'))
        else:
            error = 'Usuario o contraseña incorrectos.'
            
    return render_template('acceso/login.html', error=error)

# Ruta protegida del panel de administración
@administrador_bp.route('/panel')
def panel():
    if not session.get('admin_logueado'):
        return redirect(url_for('administrador.login'))
        
    return render_template(
        'administrador/panel.html', 
        turno_actual=turnos_db["en_atencion"],
        turnos=turnos_db["cola"]
    )

@administrador_bp.route('/logout')
def logout():
    session.pop('admin_logueado', None)
    return redirect(url_for('administrador.login'))

@administrador_bp.route('/siguiente_turno', methods=['POST'])
def siguiente_turno():
    if not session.get('admin_logueado'):
        return redirect(url_for('administrador.login'))
        
    from app import socketio
    
    if turnos_db["cola"]:
        turnos_db["en_atencion"] = turnos_db["cola"].pop(0)
    else:
        turnos_db["en_atencion"] = "Ninguno"
        
    socketio.emit('actualizar_datos', {
        'turno_actual': turnos_db["en_atencion"],
        'pendientes': len(turnos_db["cola"])
    })
    
    return redirect(url_for('administrador.panel'))