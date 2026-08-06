from flask import Blueprint, render_template

cliente_bp = Blueprint('cliente', __name__)

@cliente_bp.route('/')
def sala_espera():  
    return render_template('cliente/sala_espera.html')