//     Copyright 2012, Kay Hayen, mailto:kayhayen@gmx.de
//
//     Part of "Nuitka", an optimizing Python compiler that is compatible and
//     integrates with CPython, but also works on its own.
//
//     If you submit Kay Hayen patches to this software in either form, you
//     automatically grant him a copyright assignment to the code, or in the
//     alternative a BSD license to the code, should your jurisdiction prevent
//     this. Obviously it won't affect code that comes to him indirectly or
//     code you don't submit to him.
//
//     This is to reserve my ability to re-license the code at a later time to
//     the PSF. With this version of Nuitka, using it for a Closed Source and
//     distributing the binary only is not allowed.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, version 3 of the License.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
//     Please leave the whole of this copyright notice intact.
//
#ifndef __NUITKA_VARIABLES_TEMPORARY_H__
#define __NUITKA_VARIABLES_TEMPORARY_H__

// Wraps a "PyObject *" you received or acquired from another container to simplify refcount
// handling when you're not going to use the object beyond the local scope. It will hold a
// reference to the wrapped object as long as the PyObjectTemporary is alive, and will
// release the reference when the wrapper is destroyed: this eliminates the need for
// manual DECREF calls on Python objects before returning from a method call.
//
// In effect, wrapping an object inside a PyObjectTemporary is equivalent to a deferred
// Py_DECREF() call on the wrapped object.

class PyObjectTemporary
{
    public:
        explicit PyObjectTemporary( PyObject *object )
        {
            assertObject( object );

            this->object = object;
        }

        ~PyObjectTemporary()
        {
            assertObject( this->object );

            Py_DECREF( this->object );
        }

        PyObject *asObject() const
        {
            assertObject( this->object );

            return this->object;
        }

        void assign( PyObject *object )
        {
            assertObject( this->object );

            Py_DECREF( this->object );

            assertObject( object );

            this->object = object;
        }

    private:
        PyObjectTemporary( const PyObjectTemporary &object ) = delete;

        PyObject *object;
};

class PyObjectTempHolder
{
    public:
        explicit PyObjectTempHolder( PyObject *object )
        {
            assertObject( object );

            this->object = object;
        }

        ~PyObjectTempHolder()
        {
            Py_XDECREF( this->object );
        }

        PyObject *asObject()
        {
            assertObject( this->object );

            PyObject *result = this->object;
            this->object = NULL;
            return result;
        }

    private:
        PyObjectTempHolder( const PyObjectTempHolder &object ) = delete;

        PyObject *object;
};

#endif
