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
""" This is the main control actions of Nuitka, for use in several main programs.

This can do all the steps to translate one module to a target language using the Python
C/API, to compile it to either an executable or an extension module.

"""

from . import (
    TreeBuilding,
    Tracing,
    TreeXML,
    Options,
    Utils
)

from .build import SconsInterface

from .codegen import CodeGeneration

from .transform.optimizations import Optimization
from .transform.finalizations import Finalization

import sys, os

def createNodeTree( filename ):
    """ Create a node tree.

    Turn that source code into a node tree structure. If recursion into imported modules
    is available, more trees will be available during optimization.

    """

    # First build the raw node tree from the source code.
    result = TreeBuilding.buildModuleTree(
        filename = filename,
        package  = None,
        is_main  = not Options.shallMakeModule()
    )

    # Then optimize the tree and potentially recursed modules.
    result = Optimization.optimizeWhole( result )

    return result

def dumpTree( tree ):
    Tracing.printLine( "Analysis -> Tree Result" )

    Tracing.printSeparator()
    Tracing.printSeparator()
    Tracing.printSeparator()

    tree.dump()

    Tracing.printSeparator()
    Tracing.printSeparator()
    Tracing.printSeparator()

def dumpTreeXML( tree ):
    xml_root = tree.asXml()
    TreeXML.dump( xml_root )

def displayTree( tree ):
    # Import only locally so the Qt4 dependency doesn't normally come into play when it's
    # not strictly needed, pylint: disable=W0404
    from .gui import TreeDisplay

    TreeDisplay.displayTreeInspector( tree )

def _prepareCodeGeneration( tree ):
    Finalization.prepareCodeGeneration( tree )

def makeModuleSource( tree ):
    _prepareCodeGeneration( tree )

    source_code = CodeGeneration.generateModuleCode(
        module         = tree,
        module_name    = tree.getName(),
        global_context = CodeGeneration.makeGlobalContext()
    )

    return source_code

def getSourceDirectoryPath( main_module ):
    assert main_module.isModule()

    name = Utils.basename( main_module.getFilename() ).replace( ".py", "" )

    return Options.getOutputPath( name + ".build" )

def makeSourceDirectory( main_module ):
    assert main_module.isModule()

    source_dir = getSourceDirectoryPath( main_module )

    if os.path.exists( source_dir ):
        for filename in sorted( os.listdir( source_dir ) ):
            path = Utils.joinpath( source_dir, filename )

            if Utils.getExtension( path ) in ( ".cpp", ".hpp", ".o", ".os" ):
                os.unlink( path )
    else:
        os.makedirs( source_dir )

    static_source_dir = Utils.joinpath( source_dir, "static" )

    if os.path.exists( static_source_dir ):
        for filename in sorted( os.listdir( static_source_dir ) ):
            path = Utils.joinpath( static_source_dir, filename )

            if Utils.getExtension( path ) in ( ".o", ".os" ):
                os.unlink( path )

    global_context = CodeGeneration.makeGlobalContext()

    other_modules = Optimization.getOtherModules()

    if main_module in other_modules:
        other_modules.remove( main_module )

    for other_module in sorted( other_modules, key = lambda x : x.getFullName() ):
        _prepareCodeGeneration( other_module )

    module_hpps = []

    collision_filenames = set()
    seen_filenames = set()

    for other_module in sorted( other_modules, key = lambda x : x.getFullName() ):
        base_filename = Utils.joinpath( source_dir, other_module.getFullName() )

        collision_filename = os.path.normcase( base_filename )

        if collision_filename in seen_filenames:
            collision_filenames.add( collision_filename )

        seen_filenames.add( collision_filename )

    collision_count = {}

    for collision_filename in collision_filenames:
        collision_count[ collision_filename ] = 1

    for other_module in sorted( other_modules, key = lambda x : x.getFullName() ):
        base_filename = Utils.joinpath( source_dir, other_module.getFullName() )

        # TODO: Actually the case sensitivity of build dir should be detected.
        collision_filename = os.path.normcase( base_filename )

        if collision_filename in collision_filenames:
            hash_suffix = "@%d" % collision_count[ collision_filename ]
            collision_count[ collision_filename ] += 1
        else:
            hash_suffix = ""

        base_filename += hash_suffix

        cpp_filename = base_filename + ".cpp"
        hpp_filename = base_filename + ".hpp"

        other_module_code = CodeGeneration.generateModuleCode(
            global_context = global_context,
            module         = other_module,
            module_name    = other_module.getFullName()
        )

        module_hpps.append( hpp_filename )

        writeSourceCode(
            filename     = cpp_filename,
            source_code  = other_module_code
        )

        writeSourceCode(
            filename     = hpp_filename,
            source_code  = CodeGeneration.generateModuleDeclarationCode(
                module_name = other_module.getFullName()
            )
        )

    _prepareCodeGeneration( main_module )

    main_module_name = main_module.getName()

    cpp_filename = Utils.joinpath( source_dir, "__main__.cpp" )
    hpp_filename = Utils.joinpath( source_dir, "__main__.hpp" )

    # Create code for the main module.
    source_code = CodeGeneration.generateModuleCode(
        module         = main_module,
        module_name    = main_module_name,
        global_context = global_context
    )

    if not Options.shallMakeModule():
        source_code = CodeGeneration.generateMainCode(
            codes         = source_code,
            other_modules = other_modules
        )

    writeSourceCode(
        filename    = cpp_filename,
        source_code = source_code
    )

    writeSourceCode(
        filename    = hpp_filename,
        source_code = CodeGeneration.generateModuleDeclarationCode(
            module_name = main_module_name
        )
    )

    module_hpps.append( "__main__.hpp" )

    writeSourceCode(
        filename    = Utils.joinpath( source_dir, "__constants.cpp" ),
        source_code = CodeGeneration.generateConstantsDefinitionCode(
            context = global_context
        )
    )

    module_hpp_include = [
        '#include "%s"\n' % Utils.basename( module_hpp )
        for module_hpp in
        module_hpps
    ]

    writeSourceCode(
        filename    = Utils.joinpath( source_dir, "__constants.hpp" ),
        source_code = CodeGeneration.generateConstantsDeclarationCode(
            context = global_context
        )
    )

    writeSourceCode(
        filename    = Utils.joinpath( source_dir, "__reverses.hpp" ),
        source_code = CodeGeneration.generateReversionMacrosCode(
            context = global_context
        )
    )

    writeSourceCode(
        filename    = Utils.joinpath( source_dir, "__modules.hpp" ),
        source_code = "".join( module_hpp_include )
    )

def runScons( tree, quiet ):
    name = Utils.basename( tree.getFilename() ).replace( ".py", "" )

    def asBoolStr( value ):
        return "true" if value else "false"

    result_file = Options.getOutputPath( name )
    source_dir = Options.getOutputPath( name + ".build" )

    if Options.options.python_version is not None:
        python_version = Options.options.python_version
    else:
        python_version = "%d.%d" % ( sys.version_info[0], sys.version_info[1] )

        if Utils.getPythonVersion() >= 320:
            python_version += sys.abiflags # pylint: disable=E1101

    if Options.options.python_debug is not None:
        python_debug = Options.options.python_debug
    else:
        python_debug = hasattr( sys, "getobjects" )

    options = {
        "name"           : name,
        "result_file"    : result_file,
        "source_dir"     : source_dir,
        "debug_mode"     : asBoolStr( Options.isDebug() ),
        "unstriped_mode" : asBoolStr( Options.isUnstriped() ),
        "module_mode"    : asBoolStr( Options.shallMakeModule() ),
        "optimize_mode"  : asBoolStr( Options.isOptimize() ),
        "python_version" : python_version,
        "python_debug"   : asBoolStr( python_debug ),
        "lto_mode"       : asBoolStr( Options.isLto() ),
    }

    if Options.isWindowsTarget():
        options[ "win_target" ] = "true"

    return SconsInterface.runScons( options, quiet ), options

def writeSourceCode( filename, source_code ):
    assert not os.path.exists( filename ), filename

    open( filename, "w" ).write( source_code )

def executeMain( binary_filename, tree, clean_path ):
    name = Utils.basename( tree.getFilename() ).replace( ".py", ".exe" )

    old_python_path = os.environ.get( "PYTHONPATH", None )

    try:
        if clean_path and old_python_path is not None:
            os.environ[ "PYTHONPATH" ] = ""

        if not Options.isWindowsTarget() or "win" in sys.platform:
            os.execl( binary_filename, name, *Options.getMainArgs() )
        else:
            os.execl( "/usr/bin/wine", name, binary_filename, *Options.getMainArgs() )
    finally:
        if old_python_path is not None:
            os.environ[ "PYTHONPATH" ] = old_python_path

def executeModule( tree ):
    __import__( tree.getName() )
