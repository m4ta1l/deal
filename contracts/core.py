from functools import update_wrapper, partial
from types import MethodType


__all__ = ['ValidationError', 'Pre', 'Post', 'Invariant']


try:
    string_types = (str, unicode)
except NameError:
    string_types = (str, )


class ValidationError(Exception):
    pass


class _Base(object):
    def __init__(self, validator, exception=ValidationError):
        self.validator = validator
        self.exception = exception

    def _validate(self, *args, **kwargs):
        # Django Forms validation interface
        if hasattr(self.validator, 'is_valid'):
            validator = self.validator(*args, **kwargs)
            # is valid
            if validator.is_valid():
                return
            # is invalid
            if hasattr(validator, 'errors'):
                raise self.exception(validator.errors)
            if hasattr(validator, '_errors'):
                raise self.exception(validator.errors)
            raise self.exception

        validation_result = self.validator(*args, **kwargs)
        # is invalid (validator return error message)
        if isinstance(validation_result, string_types):
            raise self.exception(validation_result)
        # is valid (truely result)
        if validation_result:
            return
        # is invalid (falsy result)
        raise self.exception

    def __call__(self, function):
        self.function = function
        # return update_wrapper(self.patched_function, function)
        return self.patched_function


class Pre(_Base):
    def patched_function(self, *args, **kwargs):
        self._validate(*args, **kwargs)
        return self.function(*args, **kwargs)


class Post(_Base):
    def patched_function(self, *args, **kwargs):
        result = self.function(*args, **kwargs)
        self._validate(result)
        return result


class InvariantedClass(object):
    def _validate(self, *args, **kwargs):
        self._disable_patching = True
        super(InvariantedClass, self)._validate(self)
        self._disable_patching = False

    def _patched_method(self, method, *args, **kwargs):
        self._validate()
        result = method(*args, **kwargs)
        self._validate()
        return result

    def __getattribute__(self, name):
        attr = super(InvariantedClass, self).__getattribute__(name)
        # disable patching for InvariantedClass methods
        if name in ('_patched_method', '_validate'):
            return attr
        # disable patching for attributes (not methods)
        if not isinstance(attr, MethodType):
            return attr
        # disable patching by flag (if validation in progress)
        if self._disable_patching:
            return attr
        # patch
        patched_method = partial(self._patched_method, attr)
        return update_wrapper(patched_method, attr)


class Invariant(_Base):
    def __call__(self, _class):
        name = _class.__name__ + 'Invarianted'
        patched_class = type(name, (InvariantedClass, _class), {})
        # return update_wrapper(patched_class, _class)
        return patched_class
