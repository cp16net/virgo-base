import os
import sys
import zipfile
import hashlib
import subprocess

THIS_FILE = os.path.basename(__file__)

VIRGO_EXPORTS = """/*This file is generated by %s */
#include <string.h>
#include "virgo_exports.h"

const void *virgo_ugly_hack = NULL;
%s

const void *virgo__suck_in_symbols(void)
{
  virgo_ugly_hack = (const char*)

%s;

  return virgo_ugly_hack;
}
"""

LUA_MODULES_INIT = """--[[ This file is generated by %s ]]

return {
  version = "%s",
  lua_modules = {
%s
  },
  statics = {
%s
  }
}
"""


def bytecompile_lua(product_dir, lua, dot_c_file):
    """bytecompile lua to a c file.
    this function is necessary because luajit looks for the jit files in stupid places
    (including its cwd)"""
    os.chdir(product_dir)
    luajit = os.path.join(product_dir, 'luajit')

    ret = subprocess.check_call([luajit, '-bg', lua, dot_c_file])
    if ret != 0:
        raise Exception('failed call to luajit')


def virgo_exports(out, *luas):
    """auto gens a .c file to suck in virgo lua file symbols
    (so that the linker doesn't cast them away)"""
    casts = []
    declarations = []
    for lua in luas:
        name = os.path.basename(lua).split('.lua')[0]
        declarations.append("extern const char *luaJIT_BC_%s[];" % name)
        casts.append("  (size_t)(const char *)luaJIT_BC_%s" % name)

    header = VIRGO_EXPORTS % (THIS_FILE, "\n".join(declarations), " +\n".join(casts))

    with open(out, 'wb') as fp:
        fp.write(header)


def is_gyp_bundled(path):
    #TODO: make me for reals
    return int(False)


def _split_path(p):
    split = []
    while p:
        p, chunk = os.path.split(p)
        split.insert(0, chunk)
    return split


def stupid_find(root):
    file_list = []
    for base_path, _, files in os.walk(root):
        file_list += ["%s/%s" % (base_path, f) for f in files]
    return file_list


def bundle_list(root, exclude_dir):
    """list files to bundle at root
    ...minus those that start in exclusions
    ...minus anything not a .lua unless in static
    ...and minus the paths in static that are in exclusions"""
    file_list = []
    exclude_dir = os.path.normpath(exclude_dir) + os.path.sep
    # its easier to generate a list of stuff to ignore based on how os.walk works
    for base_path, _, files in os.walk(root):
        for f in files:
            file_path = os.path.join(base_path, f)
            #skip links
            if os.path.islink(f):
                continue
            rel_path = os.path.relpath(file_path, root)
            split_path = _split_path(rel_path)
            # skip if not in static and not a .lua
            name, extension = os.path.splitext(f)
            abs_path = os.path.abspath(file_path)
            if abs_path.startswith(exclude_dir):
                continue
            if split_path[0] != "static" and extension != ".lua":
                continue
            if name in [".git", ".gitignore", ".gitmodules"]:
                continue
            file_list.append("'%s'" % os.path.relpath(rel_path, 'HACK_DIRECTORY'))
    # raise Exception(file_list)
    return file_list


class VirgoZip(zipfile.ZipFile):
    def __init__(self, root, out):
        zipfile.ZipFile.__init__(self, out, 'w', zipfile.ZIP_DEFLATED)
        self.root = root
        self.lua_modules = set()
        self.statics = []

    def add(self, source):
        relPath = os.path.relpath(source, self.root)
        self.write(source, relPath)
        split = _split_path(relPath)

        #record lua modules we find
        if split[0] == "lua_modules":
            module = os.path.splitext(split[1])[0]
            self.lua_modules.add(module)
        elif split[0] == "static":
            self.statics.append(relPath)

    def insert_lua_modules_init(self, bundle_version):
        """make a lua importable file with some meta info about the bundle"""
        modules = ',\n'.join(['    "%s"' % x for x in self.lua_modules])
        statics = ',\n'.join(['    "%s"' % x for x in self.statics])
        init = LUA_MODULES_INIT % (THIS_FILE, bundle_version, modules, statics)
        self.writestr('lua_modules/init.lua', init)


def make_bundle(root, bundle_version, out, *files):
    z = VirgoZip(root, out)

    for lua in files:
        z.add(lua)

    z.insert_lua_modules_init(bundle_version)
    z.close()

    print('Wrote %d files to %s' % (len(files), out))


def hash(*args):
    m = hashlib.md5()
    for arg in args:
        m.update(arg)
    return m.hexdigest()

if __name__ == "__main__":
    args = sys.argv[2:]
    func = locals().get(sys.argv[1], None)
    if not func:
        raise AttributeError('you tried to call a function that doesn\'t exist %s' % (sys.argv[1]))
    response = func(*args)
    if isinstance(response, (list, tuple)):
        response = "\n".join(response)
    if response:
        print response
