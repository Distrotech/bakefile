
import mk, errors
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
        if target==None:
            return mk.vars[var]
        else:
            return mk.targets[target].vars[var]
    else:
        if target==None:
            return "$(ref('%s'))" % var
        else:
            return "$(ref('%s', '%s'))" % (var,target)


def makeUniqueCondVarName(name):
    """Creates name for cond. var."""
    n = nb = '__%s' % (name)
    i = 1
    while n in mk.cond_vars:
        n = '%s_%i' % (nb, i)
        i += 1
    return n


substVarNameCounter = 0

def substitute(str, callback, desc=None):
    """Calls callback to substitute text in str by something else. Works with
       conditional variables, too."""

    if desc == None:
        global substVarNameCounter
        desc = '%i' % substVarNameCounter
        substVarNameCounter += 1
    
    def callbackVar(expr, use_options, target, add_dict):
        if expr not in mk.cond_vars:
            raise errors.Error("'%s' can't be used in this context, "%expr +
                               "not a conditional variable")
        cond = mk.cond_vars[expr]
        var = mk.CondVar(makeUniqueCondVarName('%s_%s' % (cond.name, desc)))
        mk.addCondVar(var)
        for v in cond.values:
            if '$' in v.value:
                var.add(v.cond, substitute(v.value, callback, desc))
            else:
                var.add(v.cond, callback(v.value))
        return '$(%s)' % var.name

    def callbackTxt(expr):
        if len(expr) == 0 or expr.isspace(): return expr
        return callback(expr)
    
    return mk.__doEvalExpr(str, callbackVar, callbackTxt)

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
                      lambda x: '%s$(DIRSEP)%s' % (mk.vars['srcprefix'], x),
                      'SOURCEFILES')


def sources2objects(sources, target, ext):
    import os.path
    import reader

    code = """
    <makefile>
    <%s id="%s">
        <parent-target>%s</parent-target>
        <src>%s</src>
    </%s>
    </makefile>
    """

    srcs = []

    def callback(sources):
        prefix = suffix = ''
        if sources[0].isspace(): prefix=' '
        if sources[-1].isspace(): suffix=' '
        retval = []
        for s in sources.split():
            base, srcext = os.path.splitext(s)
            base = os.path.basename(base)
            objdir = mkPathPrefix(mk.vars['BUILDDIR'])
            obj = '%s%s%s' % (objdir, base, ext)
            if s in srcs: continue
            srcs.append(s)
            if obj in mk.targets:
                obj = '%s%s-%s%s' % (objdir, mk.targets[target].id, base, ext)
                num=0
                while obj in mk.targets:
                    obj = '%s%s-%s%i%s' % (objdir, mk.targets[target].id, base, num, ext)
            rule = '__%s-to-%s' % (srcext[1:], ext[1:])
            code2 = code % (rule, obj, target, s, rule)
            reader.processString(code2)
            retval.append(obj)
        return '%s%s%s' % (prefix, ' '.join(retval), suffix)

    sources2 = nativePaths(sources)
    retval = substitute(sources2, callback, 'OBJECTS')
    return retval


def addPrefixIfNotEmpty(prefix, value):
    """Adds prefix before 'value', unless value is empty string. Can handle
       following forms of 'value':
           - empty string
           - anything beginning with literal
           - $(cv) where cv is conditional variable
    """

    if value == '':
        return ''
    if value[0] != '$':
        return '%s%s' % (prefix,value)
    if value.startswith('$(') and value[-1] == ')':
        condname = value[2:-1]
        if condname in mk.cond_vars:
            cond = mk.cond_vars[condname]
            var = mk.CondVar(makeUniqueCondVarName('%s_p' % cond.name))
            mk.addCondVar(var)
            for v in cond.values:
                var.add(v.cond, addPrefixIfNotEmpty(prefix, v.value))
            return '$(%s)' % var.name
    raise errors.Error("addPrefixIfNotEmpty failed: '%s' too complicated" % value)



def mkPathPrefix(p):
    if p == '.':
        return ''
    else:
        return p + '$(DIRSEP)'
