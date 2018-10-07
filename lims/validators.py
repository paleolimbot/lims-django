
import json
import re

import django.core.validators as django_validators
from django.utils.deconstruct import deconstructible
from django.core.exceptions import ValidationError

from .utils import geometry


class ValidatorError(Exception):
    pass


validators = {}


def register_validator(validator_class, name=None):
    global validators
    if name is None:
        name = re.sub(r'Validator$', '', validator_class.__name__)
    validators[name] = validator_class
    return validator_class


def resolve_validator_class(name):
    try:
        return validators[name]
    except KeyError:
        raise ValidatorError('Could not find validator: "%s"' % name)


def resolve_validator(name, **kwargs):
    try:
        return resolve_validator_class(name)(**kwargs)
    except Exception as e:
        raise ValidatorError('Could not instantiate validator: %s' % e)


register_validator(django_validators.RegexValidator)
register_validator(django_validators.MaxLengthValidator)
register_validator(django_validators.MaxValueValidator)
register_validator(django_validators.MinLengthValidator)
register_validator(django_validators.MinValueValidator)
register_validator(django_validators.DecimalValidator)
register_validator(django_validators.EmailValidator)
register_validator(django_validators.URLValidator)


@register_validator
@deconstructible
class IsARegexValidator:
    def __call__(self, value):
        try:
            re.compile(value)
        except Exception as e:
            raise ValidationError('Value is not a valid Python regex: %s' % e)


@register_validator
@deconstructible
class FloatValidator:
    def __call__(self, value):
        try:
            float(value)
        except ValueError:
            raise ValidationError('Value cannot be converted to float')


@register_validator
@deconstructible
class IntegerValidator:
    def __call__(self, value):
        try:
            int(value)
        except ValueError:
            raise ValidationError('Value cannot be converted to an integer')


@register_validator
@deconstructible
class WKTValidator:
    def __call__(self, value):
        geometry.validate_wkt(value)


@register_validator
@deconstructible
class JSONDictValidator:
    def __call__(self, value):
        if not value:
            return
        try:
            obj = json.loads(value)
            if not isinstance(obj, dict):
                raise ValidationError('Value is not a valid JSON object')

        except ValueError:
            raise ValidationError('Value is not valid JSON')


@register_validator
@deconstructible
class JSONListValidator:
    def __init__(self, item_type=None, max_length=None, min_length=None):
        self.item_type = item_type
        self.max_length = max_length
        self.min_length = min_length

    def __call__(self, value):
        if not value:
            return
        try:
            obj = json.loads(value)
            if not isinstance(obj, list):
                raise ValidationError('Value is not a valid JSON list')
            if self.max_length is not None and len(obj) > self.max_length:
                raise ValidationError('JSON list has length greater than %s' % self.max_length)
            if self.min_length is not None and len(obj) < self.min_length:
                raise ValidationError('JSON list has length less than %s' % self.min_length)

            type_mismatches = [str(i) for i, x in enumerate(obj) if type(x).__name__ == self.item_type]
            if type_mismatches:
                raise ValidationError(
                    'JSON list items do not inherit from "%s" at positions %s' %
                    (self.item_type, ', '.join(type_mismatches))
                )

        except ValueError:
            raise ValidationError('Value is not valid JSON')
