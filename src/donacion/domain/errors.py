"""Errores del dominio. La capa de API los traduce a códigos HTTP."""


class DomainError(Exception):
    """Error base de las reglas de negocio."""


class ValidationError(DomainError):
    """Un dato no cumple las reglas del dominio."""


class NotFoundError(DomainError):
    """La entidad buscada no existe."""


class AuthenticationError(DomainError):
    """Correo o contraseña incorrectos."""


class ConflictError(DomainError):
    """La operación choca con el estado actual (p. ej. correo duplicado, solicitud cerrada)."""
