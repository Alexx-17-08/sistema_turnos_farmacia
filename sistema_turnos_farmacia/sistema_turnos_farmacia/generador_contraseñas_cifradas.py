from werkzeug.security import generate_password_hash

def generar_hash(password):
    return generate_password_hash(password)

if __name__ == "__main__":
    print("Hash para tu BD:", generar_hash("admcd cin123"))
    