
from datetime import datetime

from bson.timestamp import Timestamp
from bson.objectid import ObjectId
from bson.min_key import MinKey
from bson.max_key import MaxKey
from bson.int64 import Int64
from bson.decimal128 import Decimal128
from bson.binary import Binary
from bson.regex import Regex
from bson.code import Code

from bson.py3compat import string_type, integer_types

from ..helpers import (
    is_array_type,
    is_mapping_type,
    RE_PATTERN_TYPE,
    re_int_flag_to_str,
)


_decimal128_NaN = Decimal128('NaN')
_decimal128_INF = Decimal128('Infinity')
_decimal128_NaN_ls = (_decimal128_NaN,
                      Decimal128('-NaN'),
                      Decimal128('sNaN'),
                      Decimal128('-sNaN'))


class _cmp_decimal(object):

    __slots__ = ["_dec"]

    def __init__(self, dec128):
        if isinstance(dec128, Decimal128):
            self._dec = dec128
        else:
            raise TypeError("Only accept an instance of 'Decimal128'.")

    def _is_numeric(self, other):
        number_type = (integer_types, float, Int64, Decimal128, _cmp_decimal)
        return isinstance(other, number_type)

    def _to_decimal128(self, other):
        if isinstance(other, _cmp_decimal):
            other = other._dec
        if not isinstance(other, Decimal128):
            other = Decimal128(str(other))
        return other

    def __repr__(self):
        return "Decimal128({!r})".format(str(self._dec))

    def __eq__(self, other):
        if self._is_numeric(other):
            other = self._to_decimal128(other)
            return self._dec.to_decimal() == other.to_decimal()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def _lt_gt(self, other, lt):
        if self._is_numeric(other):
            other = self._to_decimal128(other)
            if other == _decimal128_INF or self._dec == _decimal128_NaN:
                return lt
            if other == _decimal128_NaN or self._dec == _decimal128_INF:
                return not lt
            cmp_ = (self._dec, other) if lt else (other, self._dec)
            return cmp_[0].to_decimal() < cmp_[1].to_decimal()
        else:
            return NotImplemented

    def __gt__(self, other):
        return self._lt_gt(other, False)

    def __lt__(self, other):
        return self._lt_gt(other, True)

    def _le_ge(self, other, le):
        if self._is_numeric(other):
            attr = self.__gt__ if le else self.__lt__
            return self._dec == _decimal128_INF or not attr(other)
        else:
            return NotImplemented

    def __ge__(self, other):
        return self._le_ge(other, False)

    def __le__(self, other):
        return self._le_ge(other, True)


class Weighted(tuple):
    """
    """

    def __new__(cls, value):
        return super(Weighted, cls).__new__(cls, gravity(value))


def gravity(value, weight_only=None):
    """
    """
    # a short cut for getting weight number,
    # to get rid of lots `if` stetments.
    TYPE_WEIGHT = {
        MinKey: -1,
        # less than None: 0, this scenario handles in
        #                 ordering phase, not during weighting
        type(None): 1,
        int: 2,
        float: 2,
        Int64: 2,
        Decimal128: 2,
        _cmp_decimal: 2,
        # string: 3,
        # dict: 4,
        # list: 5,
        # tuple: 5,
        Binary: 6,
        # bytes: 6,
        ObjectId: 7,
        bool: 8,
        datetime: 9,
        Timestamp: 10,
        # Regex: 11
        # Code without scope: 12
        # Code with scope: 13
        MaxKey: 127
    }

    # get value type weight
    try:
        wgt = TYPE_WEIGHT[type(value)]

    except KeyError:
        if is_mapping_type(value):
            wgt = 4
        elif is_array_type(value):
            wgt = 5
        elif isinstance(value, (RE_PATTERN_TYPE, Regex)):
            wgt = 11
        elif isinstance(value, Code):  # also an instance of string_type
            wgt = 12 if value.scope is None else 13
        elif isinstance(value, string_type):
            wgt = 3
        elif isinstance(value, bytes):
            wgt = 6
        else:
            raise TypeError("Not weightable type: {!r}".format(type(value)))

    if weight_only:
        return wgt
    return _weighted(wgt, value)


def _weighted(weight, value):

    def __dict_parser(dict_doc):
        for key, val in dict_doc.items():
            wgt, val = gravity(val)
            yield (wgt, key, val)

    def __list_parser(list_doc):
        return (gravity(member) for member in list_doc)

    def numeric_type(wgt, val):
        if isinstance(value, (Decimal128, _cmp_decimal)):
            if isinstance(val, _cmp_decimal):
                val = val._dec
            if val in _decimal128_NaN_ls:
                val = Decimal128('NaN')  # MongoDB does not sort them
            return (wgt, _cmp_decimal(val))
        else:
            return (wgt, val)

    def mapping_type(wgt, val):
        return (wgt, tuple(__dict_parser(val)))

    def array_type(wgt, val):
        return (wgt, tuple(__list_parser(val)))

    def regex_type(wgt, val):
        return (wgt, val.pattern, re_int_flag_to_str(val.flags))

    def code_type(wgt, val):
        return (wgt, str(value), None)

    def code_scope_type(wgt, val):
        return (wgt, str(value), tuple(__dict_parser(val.scope)))

    weight_method = {
        2: numeric_type,
        4: mapping_type,
        5: array_type,
        11: regex_type,
        12: code_type,
        13: code_scope_type,
    }

    try:
        return weight_method[weight](weight, value)
    except KeyError:
        return (weight, value)