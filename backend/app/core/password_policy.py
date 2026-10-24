"""Política de contraseñas: longitud mínima, lista de contraseñas comunes y variedad básica."""
from typing import Optional

MIN_PASSWORD_LENGTH = 12

_COMMON_PASSWORDS = {
    "password1234", "password12345", "123456789012", "qwertyuiop12", "contrasena123",
    "contrasena1234", "administrador", "administrator1", "superdato1234", "mercadona1234",
    "superdatoadmin2026!", "superdato2026!", "admin12345678", "admin12345678!",
    "iloveyou1234", "welcome12345", "letmein12345", "passw0rd1234", "abcdefghijkl",
    "123456123456", "111111111111", "000000000000", "qwertyqwerty", "asdfghjkl123",
}


def validate_password_strength(password: str, email: Optional[str] = None) -> str:
    """Valida la fortaleza mínima de una contraseña; lanza ValueError con un mensaje claro."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if len(password) > 128:
        raise ValueError("La contraseña no puede superar los 128 caracteres.")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        raise ValueError("Esa contraseña es demasiado común o conocida. Elige otra.")
    if len(set(password)) < 5:
        raise ValueError("La contraseña es demasiado repetitiva.")
    if email and lowered == email.strip().lower():
        raise ValueError("La contraseña no puede ser igual a tu correo electrónico.")
    classes = sum([
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ])
    if classes < 2 and len(password) < 16:
        raise ValueError("Combina letras, números o símbolos (o usa una frase de 16+ caracteres).")
    return password

