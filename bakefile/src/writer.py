#
#  This file is part of Bakefile (http://bakefile.sourceforge.net)
#
#  Copyright (C) 2003,2004 Vaclav Slavik
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 2 as
#  published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  $Id$
#
#  Writes parsed bakefile to a makefile
#

import types, copy, sys, os, os.path, string
import mk, config, errors, dependencies
import outmethods, portautils
from types import StringType

mergeBlocks = outmethods.mergeBlocks
insertBetweenMarkers = outmethods.insertBetweenMarkers

class Struct: pass

class Container:
    def __init__(self):
        self.dict = {}
        self.list = []
    def append(self, key, value):
        self.dict[key] = value
        self.list.append(value)
    def __iter__(self):
        return iter(self.list)
    def __getitem__(self, key):
        return self.dict[key]
    def __delitem__(self, key):
        del self.dict[key]
    def __len__(self):
        return len(self.list)

def __stringify(x):
    if x == None: return ''
    return str(x)

__preparedMkVars = None

def __copyMkToVars():
    dict = {}

    # Copy variables:
    for v in mk.vars:
        if v == 'targets': continue
        if type(mk.vars[v]) is StringType:
            dict[v] = mk.vars[v].strip()
        else:
            dict[v] = mk.vars[v]

    # Copy targets information:
    targets = Container()

    for tar in mk.targets.values():
        t = Struct()
        for v in tar.vars:
            if v == 'configs':
                t.configs = {}
                for x in tar.vars[v]:
                    st = Struct()
                    t.configs[x] = st
                    for y in tar.vars[v][x]:
                        setattr(st, y, tar.vars[v][x][y].strip())
            elif v == 'distinctConfigs':
                t.distinctConfigs = tar.vars['distinctConfigs']
            else:
                if type(tar.vars[v]) is StringType:
                    setattr(t, v, tar.vars[v].strip())
                else:
                    setattr(t, v, tar.vars[v])
        t.cond = tar.cond
        targets.append(t.id, t)
    dict['targets'] = targets

    # Copy options:
    options = Container()
    for opt in mk.options.values():
        o = Struct()
        o.name = opt.name
        o.default = opt.default
        o.defaultStr = __stringify(o.default)
        o.desc = opt.desc
        o.descStr = __stringify(o.desc)
        o.values = opt.values
        if o.values != None: o.valuesStr = '[%s]' % ','.join(o.values)
        else: o.valuesStr = ''
        options.append(o.name, o)
    dict['options'] = options
    
    # Copy conditions:
    conditions = Container()
    for cond in mk.conditions.values():
        c = Struct()
        c.name = cond.name
        c.exprs = cond.exprs
        conditions.append(c.name, c)
        setattr(conditions, c.name, c)
    dict['conditions'] = conditions

    # Copy conditional variables:
    cond_vars = Container()
    for cv in mk.cond_vars.values():
        c = Struct()
        c.name = cv.name
        c.values = []
        for v in cv.values:
            vv = Struct()
            vv.value = v.value
            vv.cond = conditions[v.cond.name]
            c.values.append(vv)
        cond_vars.append(c.name, c)
        setattr(cond_vars, c.name, c)
    dict['cond_vars'] = cond_vars
    
    # Copy "make variables":
    make_vars = Container()
    for mv in mk.make_vars:
        mvv = Struct()
        mvv.name = mv
        mvv.value = mk.make_vars[mv]
        make_vars.append(mv, mvv)
    dict['make_vars'] = make_vars

    # Copy fragments:
    dict['fragments'] = mk.fragments
 
    return dict


def __openFile(filename):
    """Opens (or creates) file for read/write access, lock it."""
    try:
        f = open(filename, 'r+t')
    except IOError:
        f = open(filename, 'w+t')
    portautils.lock(f)
    return f

def __closeFile(f):
    """Closes file, releases lock."""
    # NB: don't unlock, close() does it and win32 won't let us close file by
    #     another process
    #portautils.unlock(f)
    f.close()


def __readFile(filename):
    try:
        f = open(filename, 'rt')
        txt = f.readlines()
        f.close()
    except IOError:
        txt = []
    return txt

def __findWriter(writer):
    found = 0
    for p in config.searchPath:
        template = os.path.join(p, writer)
        if os.path.isfile(template):
            found = 1
            rulesdir = p
            if config.track_deps:
                dependencies.addDependency(
                    mk.vars['INPUT_FILE'], config.format,
                    os.path.abspath(template))
            break
    if not found:        
        raise errors.Error("can't find output writer '%s'" % writer)
    return (rulesdir, template)

def invoke_em(writer, file, method):
    import empy.em
    rulesdir, template = __findWriter(writer)
    
    filename = portautils.mktemp('bakefile')
    
    empy.em.invoke(['-I','mk',
                    '-I','writer',
                    '-I','utils',
                    '-I','os,os.path',
                    '-B',
                    '-o',filename,
                    '-E','globals().update(writer.__preparedMkVars)',
                    '-D','RULESDIR="%s"' % rulesdir.replace('\\','\\\\'),
                    template])
    txt = __readFile(filename)
    os.remove(filename)
    writeFile(file, txt, method)


def invoke_py(writer, file, method):
    rulesdir, program = __findWriter(writer)
    code = """
import mk, writer, utils, os, os.path
globals().update(writer.__preparedMkVars)
RULESDIR="%s"
FILE="%s"

execfile("%s")
""" % (rulesdir.replace('\\','\\\\'), file.replace('\\','\\\\'),
       program.replace('\\','\\\\'))
    global __files
    __files = []
    vars = {}
    exec code in vars

def invoke(writer, file, method):
    if writer.endswith('.empy'):
        return invoke_em(writer, file, method)
    elif writer.endswith('.py'):
        return invoke_py(writer, file, method)
    else:
        raise errors.Error("unknown type of writer: '%s'" % writer)


__output_files = {}
__output_methods = {}
def writeFile(filename, data, method = 'replace'):
    if isinstance(data, types.StringType):
        data = [x+'\n' for x in data.split('\n')]
    __output_methods[filename] = method
    __output_files[filename] = data

def write():
    if config.verbose: print 'preparing generator...'

    global __preparedMkVars, __output_files
    __preparedMkVars = __copyMkToVars()
    __output_files = {}
    
    for file, writer, method in config.to_output:
        try:
            if config.verbose: print 'generating %s...' % file
            invoke(writer, file, method)
        except errors.Error, e:
            sys.stderr.write(str(e))
            return 0
   
    if config.changes_file != None:
        changes_f = open(config.changes_file, 'wt')
    else:
        changes_f = None
   
    for file in __output_files:
        # open (or create) file for R/W and lock it:
        f = __openFile(file)
        txt = f.readlines()
        # if old and new content should be combined, do it:
        if __output_methods[file] != 'replace':
            __output_files[file] = \
                eval('%s(txt, __output_files[file])' % method)
        # write the file out only if changed:
        if __output_files[file] != txt:
            f.seek(0)
            f.writelines(__output_files[file])
            if changes_f != None:
                changes_f.write('%s\n' % os.path.abspath(file))
            print 'writing %s' % file
        else:
            print 'no changes in %s' % file
        __closeFile(f)
        
        if config.track_deps:
            dependencies.addOutput(mk.vars['INPUT_FILE'], config.format,
                                   os.path.abspath(file),
                                   __output_methods[file])
    if changes_f != None:
        changes_f.close()

    return 1
