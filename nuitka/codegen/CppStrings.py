#     Copyright 2012, Kay Hayen, mailto:kayhayen@gmx.de
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
""" C++ string encoding

This contains the code to create string literals for C++ to represent the given values and
little more.
"""

from nuitka.__past__ import unicode # pylint: disable=W0622

def encodeString( value ):
    """ Encode a string, so that it gives a C++ string literal.

    """
    assert type( value ) is bytes, type( value )

    result = ""

    for c in value:
        if str is not unicode:
            cv = ord( c )
        else:
            cv = c

        if c in b'\\\t\r\n"?':
            result += r'\%o" "' % cv
        elif cv >= 32 and cv <= 127:
            result += chr( cv )
        else:
            result += r'\%o" "' % cv

    result = result.replace( '" "\\', "\\" )

    return '"%s"' % result