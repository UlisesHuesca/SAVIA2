from django.core.exceptions import ValidationError
import re

class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.search('[A-Z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula.")
    def get_help_text(self):
        return "La contraseña debe contener al menos una letra mayúscula."

class LowercaseValidator:
    def validate(self, password, user=None):
        if not re.search('[a-z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra minúscula.")
    def get_help_text(self):
        return "La contraseña debe contener al menos una letra minúscula."

class NumberValidator:
    def validate(self, password, user=None):
        if not re.search('[0-9]', password):
            raise ValidationError("La contraseña debe contener al menos un número.")
    def get_help_text(self):
        return "La contraseña debe contener al menos un número."

class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not re.search('[@$!%*#?&_]', password):
            raise ValidationError("La contraseña debe contener al menos un caracter especial: @ $ ! % * # ? & _")
    def get_help_text(self):
        return "La contraseña debe contener al menos un caracter especial: @ $ ! % * # ? & _"
