
import mk, errors, config, sys
import os


def isoption(name):
    return name in mk.__vars_opt

def isdefined(name):
    try:
        exec('__foo__ = %s' % name, mk.__curNamespace)
    except NameError:
        return isoption(name)
    return 1


def ifthenelse(cond, iftrue, iffalse):
    if eval(str(cond)): return iftrue
    else: return iffalse


__refEval = 0
def ref(var, target=None):
    if __refEval:
        if target==None or var not in mk.targets[target].vars:
            return mk.vars[var]
        else:
            return mk.targets[target].vars[var]
    else:
        if mk.__trackUsage: mk.__usageTracker.refs += 1
        if target==None:
            return "$(ref('%s'))" % var
        else:
            return "$(ref('%s', '%s'))" % (var,target)


def makeUniqueCondVarName(name):
    """Creates name for cond. var."""
    n = nb = '__%s' % (name.replace('-','_').replace('.','_'))
    i = 1
    while n in mk.cond_vars:
        n = '%s_%i' % (nb, i)
        i += 1
    return n


substVarNameCounter = 0

__substituteCallbacks = {}

def addSubstituteCallback(varname, function):
    """Register callback for substitute() and substitute2() functions.
       This callback is used if (and _only_ if) other methods of substitution
       fail, in particular when an option is found during substitution.
       
       'function' takes two arguments: (callback, option)
       where 'callback' is the original callback function that was passed as
       substitute()'s argument and 'option' is mk.Option instance that was
       encountered and can't be evaluated.
    """
    __substituteCallbacks[varname] = function

def substitute2(str, callback, desc=None, cond=None):
    """Same as substitute, but the callbacks takes two arguments (text and
       condition object) instead of one."""

    if desc == None:
        global substVarNameCounter
        desc = '%i' % substVarNameCounter
        substVarNameCounter += 1
    
    def callbackVar(cnd, expr, use_options, target, add_dict):
        if expr not in mk.cond_vars:
            if expr in __substituteCallbacks:
                return __substituteCallbacks[expr](callback, mk.options[expr])
            else:
                raise errors.Error("'%s' can't be used in this context,"%expr +
                                   "not a conditional variable")
        cond = mk.cond_vars[expr]
        var = mk.CondVar(makeUniqueCondVarName('%s_%s' % (cond.name, desc)))
        mk.addCondVar(var)
        for v in cond.values:
            cond2 = mk.mergeConditions(cnd, v.cond)
            if '$' in v.value:
                var.add(v.cond, substitute2(v.value, callback, desc, cond2))
            else:
                if len(v.value) == 0 or v.value.isspace():
                    var.add(v.cond, v.value)
                else:
                    var.add(v.cond, callback(cond2, v.value))
        return '$(%s)' % var.name

    def callbackTxt(cond, expr):
        if len(expr) == 0 or expr.isspace(): return expr
        return callback(cond, expr)
    
    return mk.__doEvalExpr(str, callbackVar, callbackTxt, cond)


def substitute(str, callback, desc=None):
    """Calls callback to substitute text in str by something else. Works with
       conditional variables, too."""
    def callb(cond, s):
        return callback(s)
    return substitute2(str, callb, desc)


def substituteFromDict(str, dict, desc=None):
    """Like substitute(), but less generic: instead of calling callback, the
       text is looked up in a dictionary. This imposes the restriction that
       'str' may be only single word."""
    try:
        return substitute(str, lambda x: dict[x], desc)
    except KeyError:
        raise errors.Error('Invalid value')


def nativePaths(filenames):
    """Translates filenames from Unix to native filenames."""
    if mk.vars['TOOLSET'] == 'unix':
        return filenames
    else:
        return substitute(filenames,
                          lambda x: x.replace('/', mk.vars['DIRSEP']),
                          'FILENAMES')

def findSources(filenames):
    """Adds source filename prefix to files."""
    return substitute(filenames,
                      lambda x: '%s$(DIRSEP)%s' % (mk.vars['SRCDIR'], x),
                      'SOURCEFILES')


def sources2objects(sources, target, ext, objSuffix=''):
    """Adds rules to compile object files from source files listed in
       'sources', when compiling target 'target', with object files extension
       being 'ext'. Optional 'objSuffix' argument is used to change the name
       of object file (e.g. to compile foo.c to foo_rc.o instead of foo.o).

       Returns object files list."""
    import os.path
    import reader, xmlparser

    # It's a bit faster (about 10% on wxWindows makefiles) to not parse XML
    # but construct the elements tree by hand. We construc the tree for this
    # code:
    #
    #code = """
    #<makefile>
    #<%s id="%s">
    #    <parent-target>%s</parent-target>
    #    <dst>%s</dst>
    #    <src>%s</src>
    #</%s>
    #</makefile>"""
    cRoot = xmlparser.Element()
    cTarget = xmlparser.Element()
    cSrc = xmlparser.Element()
    cDst = xmlparser.Element()
    cParent = xmlparser.Element()
    cRoot.name = 'makefile'
    cRoot.children = [cTarget]
    cRoot.value = ''
    cTarget.children = [cParent,cSrc,cDst]
    cParent.name = 'parent-target'
    cTarget.value = ''
    cSrc.name = 'src'
    cDst.name = 'dst'
    cParent.value = target

    files = {}

    def callback(cond, sources):
        prefix = suffix = ''
        if sources[0].isspace(): prefix=' '
        if sources[-1].isspace(): suffix=' '
        retval = []
        for s in sources.split():
            base, srcext = os.path.splitext(s)
            base = os.path.basename(base)
            objdir = mkPathPrefix(mk.vars['BUILDDIR'])
            objname = '%s%s_%s%s%s' % (objdir, mk.targets[target].id, base,
                                       objSuffix, ext)
            if objname in files:
                files[objname].append((s,cond))
            else:
                files[objname] = [(s,cond)]
            retval.append(objname)
        return '%s%s%s' % (prefix, ' '.join(retval), suffix)
            
    def addRule(id, obj, src, cond):
        base, srcext = os.path.splitext(src)
        rule = '__%s-to-%s' % (srcext[1:], ext[1:])
        cTarget.name = rule
        cTarget.props['id'] = id
        cSrc.value = src
        cDst.value = obj
        reader.processXML(cRoot)
        # CAUTION! A hack to disable creating unneeded variables:
        #          We don't pass condition as part of target's XML
        #          specification because that would create __depname
        #          conditional variable and we don't need it
        mk.targets[id].cond = cond

    def reduceConditions(cond1, cond2):
        """Reduces conditions:
             1) A & B, A & notB  |- A
             2) A, A & B         |- A
        """

        all = {}
        values = {}
        for e in cond1.exprs:
            all[e.option] = e
        for e in cond2.exprs:
            if e.option in all:
                if e.value == all[e.option].value:
                    values[e.option] = all[e.option].value
                    all[e.option] = 1
                elif e.value != all[e.option].value and \
                     e.option.values != None and len(e.option.values) == 2:
                    all[e.option] = 0
                else:
                    return None
            else:
                return None
        ret = []
        for e in all:
            if all[e] == 0:
                pass
            elif all[e] == 1:
                ret.append("%s=='%s'" % (e.name, values[e]))
            else:
                return None                
        if len(ret) == 0:
            return '1'
        else:
            return mk.makeCondition(' and '.join(ret))
 
    sources2 = nativePaths(sources)
    retval = substitute2(sources2, callback, 'OBJECTS')

    if mk.vars['FORMAT_HAS_VARIABLES'] != '0':
        tg = mk.targets[target]
        mk.setVar('%s_CFLAGS' % target.upper(),
                  "$(ref('__cppflags','%s')) $(ref('__cflags','%s'))" % \
                  (target, target), target=tg, makevar=1)
        mk.setVar('%s_CXXFLAGS' % target.upper(),
                  "$(ref('__cppflags','%s')) $(ref('__cxxflags','%s'))" % \
                  (target, target), target=tg, makevar=1)
    
    easyFiles = []
    hardFiles = []
    for f in files:
        if len(files[f]) == 1:
            easyFiles.append(f)
        else:
            hardFiles.append(f)
    if config.verbose:
        print '  making object rules (%i of %i hard)' % \
                  (len(hardFiles), len(hardFiles)+len(easyFiles))
    
    # there's only one rule for this object file, therefore we don't care
    # about its condition, if any:
    for f in easyFiles:
        src, cond = files[f][0]
        addRule(f, f, src, None)

    # these files are compiled from multiple sources, so we must create
    # conditional compilation rules:
    for f in hardFiles:
        srcfiles = {}
        for x in files[f]:
            src, cond = x
            if src not in srcfiles:
                srcfiles[src] = [cond]
            else:
                srcfiles[src].append(cond)
        i = 1
        for s in srcfiles:
            conds = srcfiles[s]
            if len(conds) > 1:
                changes = 0
                #print s, len(conds)
                #print [ x.name for x in conds ]
                lng = len(conds)
                for c1 in range(0,lng):
                    for c2 in range(c1+1,lng):
                        if conds[c1] == None: continue
                        #print conds[c1].name, conds[c2].name
                        r = reduceConditions(conds[c1], conds[c2])
                        #print 'reduction:',r
                        if r != None:
                            conds[c1] = 0
                            if r == '1':
                                conds[c2] = None
                            else:
                                conds[c2] = r
                            changes = 1
                            break
                #if changes:
                #    for c in [ x for x in conds if x != 0 ]:
                #        if c == None:
                #            print 'no cond'
                #        else:
                #            print 'cond: ',c.name
            for cond in conds:
                if cond == 0: continue
                addRule('%s%i' % (f,i), f, s, cond)
                i += 1
            

    return retval


def formatIfNotEmpty(fmt, value):
    """Return fmt % value (prefix: e.g. "%s"), unless value is empty string.
       Can handle following forms of 'value':
           - empty string
           - anything beginning with literal
           - $(cv) where cv is conditional variable
    """

    if fmt == '': return ''
    value = value.strip()
    if value == '' or value.isspace():
        return ''
    if value[0] != '$':
        return fmt % value
    if value[-1] != ')' and not value[-1].isspace():
        return fmt % value
    
    if value.startswith('$(') and value[-1] == ')':
        condname = value[2:-1]
        if condname in mk.options:
            if mk.options[condname].isNeverEmpty():
                return fmt % value
            else:
                raise errors.Error("formatIfNotEmpty failed: option '%s' may be empty" % condname)

        if condname in mk.cond_vars:
            cond = mk.cond_vars[condname]
            var = mk.CondVar(makeUniqueCondVarName('%s_p' % cond.name))
            mk.addCondVar(var)
            for v in cond.values:
                var.add(v.cond, formatIfNotEmpty(fmt, v.value))
            return '$(%s)' % var.name
    raise errors.Error("formatIfNotEmpty failed: '%s' too complicated" % value)

def addPrefixIfNotEmpty(prefix, value):
    """Prefixes value with prefix, unless value is empty. 
       See formatIfNotEmpty for more details."""
    return formatIfNotEmpty(prefix+'%s', value)


def mkPathPrefix(p):
    if p == '.':
        return ''
    else:
        return p + '$(DIRSEP)'


CONDSTR_UNIXTEST = 'unixtest' # syntax of 'test' program
CONDSTR_MSVC     = 'msvc'     # C++-like syntax used by Borland and VC++ make
def condition2string(cond, format):
    """Converts condition to string expression in given format. This is useful
       for Empy templates that need to output condition strings."""
    if cond == None:
        return ''
    if format == CONDSTR_MSVC:
        return' && '.join(['"$(%s)" == "%s"' % (x.option.name,x.value) \
                           for x in cond.exprs])
    if format == CONDSTR_UNIXTEST:
        return ' -a '.join(['"x$%s" = "x%s"' % (x.option.name,x.value) \
                           for x in cond.exprs])
    raise errors.Error('unknown format')
