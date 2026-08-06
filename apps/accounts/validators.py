from datetime import date

from django.core.exceptions import ValidationError

MINIMUM_AGE = 18


def calculate_age(birth_date):
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def validate_age_of_majority(value):
    if not value:
        return
    if value > date.today():
        raise ValidationError('La fecha de nacimiento no puede estar en el futuro.')
    if calculate_age(value) < MINIMUM_AGE:
        raise ValidationError(f'Debes ser mayor de {MINIMUM_AGE} años para usar este sitio.')
