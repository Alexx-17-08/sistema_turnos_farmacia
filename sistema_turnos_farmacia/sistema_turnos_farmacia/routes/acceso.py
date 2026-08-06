from flask import Blueprint, render_template

acceso_bp = Blueprint('acceso', __name__)

@acceso_bp.route('/')
def inicio():
    return render_template('acceso/login.html') # O una vista principal con los botones de navegación