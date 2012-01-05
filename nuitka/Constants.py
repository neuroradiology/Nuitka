#     Copyright 2012, Kay Hayen, mailto:kayhayen@gmx.de
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     If you submit Kay Hayen patches to this software in either form, you
#     automatically grant him a copyright assignment to the code, or in the
#     alternative a BSD license to the code, should your jurisdiction prevent
#     this. Obviously it won't affect code that comes to him indirectly or
#     code you don't submit to him.
#
#     This is to reserve my ability to re-license the code at a later time to
#     the PSF. With this version of Nuitka, using it for a Closed Source and
#     distributing the binary only is not allowed.
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, version 3 of the License.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#     Please leave the whole of this copyright notice intact.
#
""" Module for constants in Nuitka.

This contains means to compare, classify and test constants.
"""

import math

# pylint: disable=W0622
from .__past__ import long, unicode, iterItems
# pylint: enable=W0622

NoneType = type( None )

def compareConstants( a, b ):
    # Many many cases to deal with, pylint: disable=R0911,R0912

    # Supposed fast path for comparison.
    if type( a ) is not type( b ):
        return False

    # Now it's either not the same, or it is a container that contains NaN or it is a
    # complex or float that is NaN, the other cases can use == at the end.
    if type( a ) is complex:
        return compareConstants( a.imag, b.imag ) and compareConstants( a.real, b.real )

    if type( a ) is float:
        if math.isnan( a ) and math.isnan( b ):
            return True

        # For float, -0.0 is not 0.0, it has a different sign for a start.
        if math.copysign( 1.0, a ) != math.copysign( 1.0, b ):
            return False

        return a == b

    if type( a ) in ( tuple, list ):
        if len( a ) != len( b ):
            return False

        for ea, eb in zip( a, b ):
            if not compareConstants( ea, eb ):
                return False
        else:
            return True

    if type( a ) is dict:
        if len( a ) != len( b ):
            return False

        for ea1, ea2 in iterItems( a ):
            for eb1, eb2 in iterItems( b ):
                if compareConstants( ea1, eb1 ) and compareConstants( ea2, eb2 ):
                    break
            else:
                return False
        else:
            return True

    if type( a ) in ( frozenset, set ):
        if len( a ) != len( b ):
            return False

        for ea in a:
            if ea not in b:
                # Due to NaN values, we need to compare each set element with all the
                # other set to be really sure.
                for eb in b:
                    if compareConstants( ea, eb ):
                        break
                else:
                    return False
        else:
            return True

    if type( a ) is range:
        return str( a ) == str( b )

    # The NaN values of float and complex may let this fail, even if the constants are
    # built in the same way.
    return a == b

def isMutable( constant ):
    constant_type = type( constant )

    if constant_type in ( str, unicode, complex, int, long, bool, float, NoneType, range ):
        return False
    elif constant_type in ( dict, list ):
        return True
    elif constant_type is tuple:
        for value in constant:
            if isMutable( value ):
                return True
        else:
            return False
    elif constant is Ellipsis:
        # Note: Workaround for Ellipsis not being handled by the pickle module,
        # pretend it would be mutable, then it doesn't get pickled as part of lists or
        # tuples. This is a loss of efficiency, but usage of Ellipsis will be very
        # limited normally anyway.
        return True
    else:
        assert False, constant_type

def isIterableConstant( constant ):
    return type( constant ) in ( str, unicode, list, tuple, set, frozenset, dict, range )

def isNumberConstant( constant ):
    return type( constant ) in ( int, long, float, bool )

def isIndexConstant( constant ):
    return type( constant ) in ( int, long, bool )

class HashableConstant:
    def __init__( self, constant ):
        self.constant = constant

        try:
            # For Python3: range objects with same ranges give different hash
            # values. It's not even funny, is it.
            if type( constant ) is range:
                raise TypeError

            self.hash = hash( constant )
        except TypeError:
            self.hash = 55

    def getConstant( self ):
        return self.constant

    def __hash__( self ):
        return self.hash

    def __eq__( self, other ):
        assert isinstance( other, self.__class__ )

        return compareConstants( self.constant, other.constant )
