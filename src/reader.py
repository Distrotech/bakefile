# 
# Reading and _interpreting_ the makefiles
#
# $Id$
#

import string, sys, copy, os, os.path
import xmlparser
import mk
import utils
import errors
from errors import ReaderError
import config
import finalize

def evalConstExpr(e, str, target=None):
    try:
        return mk.evalExpr(str, use_options=0, target=target)
    except NameError, err:
        raise ReaderError(e, "can't use options or conditional variables in this context (%s)" % err)


def evalWeakCondition(e):
    """Evaluates e's 'cond' property, if present, and returns 0 or 1 if it
       can be evaluated to a constant. If it can't (i.e. it is a strong
       condition) do it, raises exception."""
    if 'cond' not in e.props:
        return 1
    condstr = e.props['cond']
    typ = mk.evalCondition(condstr)
    # Condition never met when generating this target:
    if typ == '0':
        return 0
    # Condition always met:
    elif typ == '1':
        return 1
    else:
        raise ReaderError(e,
                "'%s': only weak condition allowed in this context" % condstr)


def handleSet(e, target=None, add_dict=None):
    errors.pushCtx(e)
    name = evalConstExpr(e, e.props['var'], target)
    if (name in mk.override_vars) and target == None:
        errors.popCtx()
        return # can't change value of variable overriden with -D=xxx
    
    doEval = not ('eval' in e.props and e.props['eval'] == '0')
    overwrite = not ('overwrite' in e.props and e.props['overwrite'] == '0')
    isCond = (len(e.children) > 0)
    isMakeVar = 'make_var' in e.props and e.props['make_var'] == '1'
    value = e.value
    if 'hints' in e.props:
        hints = e.props['hints']
    else:
        hints = ''

    # Handle conditions:
    if isCond:
        noValueSet = 1
        for e_if in e.children:
            if e_if.name != 'if':
                raise ReaderError(e_if, "malformed <set> command")
        
            # Preprocess always true or always false conditions:
            condstr = e_if.props['cond']
            if condstr == 'target':
                if target == None:
                    raise ReaderError(e_if, "'target' condition can't be used at global scope")
                cond = target.cond
                if cond == None:
                    noValueSet = 0
                    isCond = 0
                    value = e_if.value
                    break
            else:
                typ = mk.evalCondition(condstr)
                # Condition never met when generating this target:
                if typ == '0':
                    continue
                # Condition always met:
                elif typ == '1':
                    noValueSet = 0
                    isCond = 0
                    value = e_if.value
                    break
                elif typ != None:
                    raise ReaderError(e, "malformed condition: '%s'" % condstr)
                cond = mk.makeCondition(condstr)

            noValueSet = 0
            
            # Real conditions:
            if 'scope' in e.props:
                raise ReaderError(e, "conditional variable can't have nondefault scope ('%s')" % e.props['scope'])

            name = e.props['var']
            if target != None:
                if (not overwrite) and (name in target.vars):
                    errors.popCtx()
                    return
                name = '__%s_%s' % (target.id.replace('-','_').replace('.','_'),
                                    name)
                mk.setVar(e.props['var'], '$(%s)' % name,
                             eval=0, target=target,
                             add_dict=add_dict, hints=hints)
            if cond == None:
                raise ReaderError(e, "malformed condition: '%s'" % condstr)
            if name in mk.cond_vars:
                if not overwrite:
                    errors.popCtx()
                    return
                var = mk.cond_vars[name]
            else:
                var = mk.CondVar(name, target)
                mk.addCondVar(var, hints)
            if doEval:
                value = mk.evalExpr(e_if.value,target=target,add_dict=add_dict)
            else:
                value = e_if.value
            var.add(cond, value)
        
        if noValueSet:
            isCond = 0
            value = ''
        
        if isCond: 
            errors.popCtx()
            return

    # Non-conditional variables:
    if value == None: value = ''
    if 'append' in e.props and e.props['append'] == '1':
        doAppend = 1
    else:
        doAppend = 0
    store_in = None
    if 'scope' in e.props:
        sc = evalConstExpr(e, e.props['scope'], target=target)
        if sc == 'local':
            pass
        elif sc == 'global':
            store_in = mk.vars
        else:
            if sc in mk.targets:
                store_in = mk.targets[sc].vars
            else:
                raise ReaderError(e, "invalid scope '%s': must be 'global', 'local' or target name" % sc)

    if isMakeVar:
        if doAppend or store_in != None or not doEval:
            raise ReaderError(e, "make variable (%s) can't be appended or stored in nondefault scope or not evaluated" % name)
 
    mk.setVar(name, value, eval=doEval, target=target,
              add_dict=add_dict, store_in=store_in,
              append=doAppend, overwrite=overwrite,
              makevar=isMakeVar, hints=hints)
    errors.popCtx()


def handleUnset(e):
    name = e.props['var']
    if not mk.unsetVar(name):
        raise ReaderError(e, "'%s' is not a variable" % name)


def handleOption(e):
    name = e.props['name']
    if name in mk.options:
        raise ReaderError(e, "option '%s' already defined" % name)

    if name in mk.override_vars:
        return # user hardcoded the value with -D=xxx

    default = None
    desc = None
    values = None
    values_desc = None
    for c in e.children:
        if c.name == 'default-value':
            default = evalConstExpr(e, c.value)
        elif c.name == 'description':
            desc = c.value
        elif c.name == 'values':
            values = evalConstExpr(e, c.value).split()
        elif c.name == 'values-description':
            values_desc = evalConstExpr(e, c.value).split()
    o = mk.Option(name, default, desc, values, values_desc)
    mk.addOption(o)
    if 'never_empty' in e.props and e.props['never_empty'] == '1':
        o.neverEmpty = 1


def extractTemplates(e, post):
    ch = []
    if post: propname = 'template_append'
    else: propname = 'template'

    if propname in e.props:
        derives = e.props[propname].split(',')
        for d2 in derives:
            d = evalConstExpr(e, d2)
            if d == '': continue
            try:
                ch2 = mk.templates[d]
                ch = ch + ch2
            except KeyError:
                raise ReaderError(e, "unknown template '%s'" % d)
    return ch

def applyTemplates(e, templPre, templPost):
    if len(templPre) == 0 and len(templPost) == 0:
        return e
    e = copy.copy(e)
    e.children = templPre + e.children + templPost
    return e


def handleTemplate(e):
    id = e.props['id']
    if id in mk.templates:
        raise ReaderError(e, "template ID '%s' already used" % id)
    mk.templates[id] = applyTemplates(e,
                                      extractTemplates(e, post=0),
                                      extractTemplates(e, post=1)).children


tagInfos = {}
class TagInfo:
    def __init__(self):
        self.exclusive = 0
        self.before = []

rules = {}
class Rule:
    def __init__(self, name):
        self.name = name
        self.pseudo = 0
        self.baserules = []
        self.tags = {}
        self.template = []
        self.cacheTagsDict = None

    def getTemplates(self):
        t = []
        for b in self.baserules:
            t = t + b.getTemplates()
        t = t + self.template
        return t

    def getTagsDict(self):
        if self.cacheTagsDict == None:
            d = {}
            for b in self.baserules:
                d2 = b.getTagsDict()
                for key in d2:
                    if key in d: d[key] += d2[key]
                    else: d[key] = copy.copy(d2[key])
            for key in self.tags:
                if key in d: d[key] += self.tags[key]
                else: d[key] = copy.copy(self.tags[key])
            self.cacheTagsDict = d
            return d
        else:
            return self.cacheTagsDict

    

def handleModifyTarget(e, dict):
    tg = mk.evalExpr(e.props['target'], use_options=0, add_dict=dict)
    if tg not in mk.targets:
        raise ReaderError(e, "unknown target '%s'" % tg)
    target = mk.targets[tg]
    tags = rules[target.type].getTagsDict()
    _processTargetNodes(e.children, target, tags, dict)


COMMANDS = ['set', 'modify-target', 'add-target']

class ValueRecord:
    def __init__(self, parent, value):
        self.value = value
        self.evaluated = None
        self.parent = parent
    def evalValue(self, target, dict):
        if self.evaluated == None:
            if self.parent == None:
                d = dict
            else:
                d = {}
                if dict != None:
                    d.update(dict)
                d['value'] = self.parent.evalValue(target, d)                
            self.evaluated = mk.evalExpr(self.value,
                                         target=target, add_dict=d)
        return self.evaluated


class CmdListEntry:
    def __init__(self, node, value, parents):
        self.node = node
        self.value = value
        self.parents = parents
        self.mustProcessBefore = 0
        self.mustProcessAfter = []
        self.executionDelayed = 0

def _extractTargetNodes(out_list, list, target, tags,
                        valueRecord, parentTags):
    """Expand all rules in list of target nodes and returns a list of
       elementary commands to be executed on the target. The list contains
       tuples (node, value_record, parent_tags)."""
    
    for node in list:
        if node.name == 'if':
            if evalWeakCondition(node):
                _extractTargetNodes(out_list, node.children, target,
                                    tags, valueRecord, parentTags)
        elif node.name in COMMANDS:
            out_list.append(CmdListEntry(node, valueRecord, parentTags))
        else:
            if node.name not in tags:
                raise ReaderError(node,
                                      "unknown target tag '%s'" % node.name)
            if evalWeakCondition(node) == 0:
                continue
            value = ValueRecord(valueRecord, node.value)
            _extractTargetNodes(out_list, tags[node.name], target,
                                tags, value, parentTags + [node])


def _filterTargetNodes(cmd_list):
    """Removes duplicate exclusive tags (e.g. <app-type>) and orders tags
       if they must have some specific order."""
    map = {}
    # cmd_list contains (node, valueR, parentTags)
    for entry in cmd_list:
        for tag in entry.parents:
            if tag.name not in map:
                map[tag.name] = [(tag, entry)]
            else:
                map[tag.name].append((tag, entry))
    
    for tagname in map:
        # remove all but the last exclusive tags if there are duplicates:
        if (tagname in tagInfos) and (tagInfos[tagname].exclusive):
            tagToPreserve = map[tagname][-1][0]
            for tag, entry in \
                    [x for x in map[tagname][:-1] if x[0] != tagToPreserve]:
                entry.node = None
    
        # reorder tags if neccessary:
        if tagname in tagInfos:
            for btag in tagInfos[tagname].before:
                if btag in map:
                    for tag, entry in map[btag]:
                        if entry.node == None: continue
                        for atag, aentry in map[tagname]:
                            if aentry.node != None:
                                aentry.mustProcessAfter.append(entry)
                                entry.mustProcessBefore += 1
        

            
def _processTargetNodes(list, target, tags, dict):

    def processCmd(e, target, dict):
        if e.name == 'set':
            handleSet(e, target=target, add_dict=dict)
        elif e.name == 'modify-target':
            if dict != None:
                v = {}
                v.update(target.vars)
                v.update(dict)
                handleModifyTarget(e, v)
            else:
                handleModifyTarget(e, target.vars)
        elif e.name == 'add-target':
            e2 = copy.deepcopy(e)
            e2.props['id'] = mk.evalExpr(e2.props['target'],
                                         target=target, add_dict=dict)
            del e2.props['target']
            e2.name = e2.props['type']
            if 'cond' in e2.props and e2.props['cond'] == 'target':
                if target.cond == None:
                    del e2.props['cond']
                else:
                    e2.props['cond'] = target.cond.tostr()
            handleTarget(e2)
        else:
            return 0
        return 1

    cmd_list = []
    _extractTargetNodes(cmd_list, list, target, tags, None, [])
    _filterTargetNodes(cmd_list)

    if config.debug:
        print '[dbg] -----------------------------------------'
        print '[dbg] * tag commands for target %s:' % target.id
        print '[dbg] -----------------------------------------'

    def _processEntry(entry, target, dict):
        if entry.mustProcessBefore > 0:
            entry.executionDelayed = 1
            return
        if entry.node == None: return
        for e in entry.mustProcessAfter:
            e.mustProcessBefore -= 1
            # only run it now if we already tried to run it but wasn't able
            # to do it because mustProcessBefore was >0:
            if e.executionDelayed:
                _processEntry(e, target, dict)
        
        if config.debug:
            parlist = [x.name for x in entry.parents]
            print '[dbg] %s || %s [%s] @%s:%s' % \
                  (parlist, entry.node.name, entry.node.props,
                   entry.node.filename, entry.node.lineno)
        
        if entry.value == None:
            dict2 = dict
        else:
            val = entry.value.evalValue(target, dict)
            dict2 = {'value':val}
        processCmd(entry.node, target, dict2)
        entry.node = None # mark it as processed

    for entry in cmd_list:
        _processEntry(entry, target, dict)


_pseudoTargetLastID = 0

def handleTarget(e):
    if e.name not in rules:
        raise ReaderError(e, "unknown target type")

    cond = None
    if 'cond' in e.props:
        isCond = 1
        # Handle conditional targets:
        condstr = e.props['cond']
        typ = mk.evalCondition(condstr)
        # Condition never met, ignore the target:
        if typ == '0':
            utils.deadTargets.append(e.props['id'])
            return
        # Condition always met:
        elif typ == '1':
            isCond = 0
        elif typ != None:
            raise ReaderError(e, "malformed condition: '%s'" % condstr)

        if isCond:
            cond = mk.makeCondition(condstr)
            if cond == None:
                raise ReaderError(e, "malformed condition: '%s'" % condstr)
        
    rule = rules[e.name]
    tags = rule.getTagsDict()
    e = applyTemplates(e, rule.getTemplates() + extractTemplates(e, post=0),
                          extractTemplates(e, post=1))

    if rule.pseudo and 'id' not in e.props:
        global _pseudoTargetLastID
        id = 'pseudotgt%i' % _pseudoTargetLastID
        _pseudoTargetLastID += 1
    else:
        id = e.props['id']
    if id in mk.targets:
        raise ReaderError(e, "duplicate target name '%s'" % id)
    
    target = mk.Target(e.name, id, cond, rule.pseudo)
    mk.addTarget(target)

    errors.pushCtx("when processing target at %s" % e.location())
    _processTargetNodes(e.children, target, tags, None)
    errors.popCtx()


def handleDefineRule(e):
    rule = Rule(evalConstExpr(e, e.props['name']))
    rules[rule.name] = rule
    HANDLERS[rule.name] = handleTarget

    if 'pseudo' in e.props and e.props['pseudo'] == '1':
        rule.pseudo = 1

    if 'extends' in e.props:
        baserules = [evalConstExpr(e,x) for x in e.props['extends'].split(',')]
        rule.baserules = []
        for baserule in baserules:
            if baserule == '': continue
            if baserule not in rules:
                raise ReaderError(e, "unknown rule '%s'" % baserule)
            rule.baserules.append(rules[baserule])

    for node in e.children:
        if node.name == 'define-tag':
            handleDefineTag(node, rule=rule)
        elif node.name == 'template':
            rule.template += applyTemplates(node,
                                      extractTemplates(node, post=0),
                                      extractTemplates(node, post=1)).children
        else:
            raise ReaderError(node,
                       "unknown element '%s' in <define-rule>" % node.name)


def handleDefineTag(e, rule=None):
    name = e.props['name']
    if rule == None:
        if 'rules' in e.props:
            rs = e.props['rules'].split(',')
        else:
            raise ReaderError(e, "external <define-tag> must list rules")
    else:
        rs = [rule.name]
    
    for rn in rs:
        if not rn in rules:
            raise ReaderError(e, "unknown rule '%s'" % rn)
        r = rules[rn]
        if name in r.tags:
            r.tags[name] += e.children
        else:
            r.tags[name] = copy.copy(e.children)
        r.cacheTagsDict = None


def handleTagInfo(e):
    name = e.props['name']
    if name in tagInfos:
        info = tagInfos[name]
    else:
        info = TagInfo()

    if 'exclusive' in e.props:
        info.exclusive = e.props['exclusive'] == '1'
    if 'position' in e.props:
        tokens = e.props['position'].split(',')
        for token in tokens:
            pos = token.find(':')
            if pos == -1:
                keyword = token
            else:
                keyword = token[:pos]
                param = token[pos+1:]

            if keyword == 'before':
                if param not in info.before:
                    info.before.append(param)
            elif keyword == 'after':
                if param not in tagInfos:
                    tagInfos[param] = TagInfo()
                if name not in tagInfos[param].before:
                    tagInfos[param].before.append(name)
            else:
                raise ReaderError(e, "unrecognized position token '%s'" % token)
        
    tagInfos[name] = info


loadedModules = []
availableFiles = []

def buildModulesList():
    class ModuleInfo: pass
    def visit(basedir, dirname, names):
        dir = dirname[len(basedir)+1:]
        if dir != '':
            dircomp = dir.split(os.sep)
        else:
            dircomp = []
        for n in names:
            ext =os.path.splitext(n)[1]
            if ext != '.bakefile' and ext != '.bkl': continue
            i = ModuleInfo()
            i.file = os.path.join(dirname,n)
            i.modules = dircomp + os.path.splitext(n)[0].split('-')
            availableFiles.append(i)

    for p in config.searchPath:
        os.path.walk(p, visit, p)


def loadModule(m):
    if m in loadedModules:
        return
    if config.verbose: print "loading module '%s'..." % m
    loadedModules.append(m)
    
    # set USING_<MODULENAME> variable:
    mk.setVar('USING_%s' % m.upper(), '1')
    
    # import module's py utilities:
    mk.importPyModule(m)
    
    # include module-specific makefiles:
    global availableFiles
    for f in availableFiles:
        if m in f.modules:
            f.modules.remove(m)
            if len(f.modules) == 0:
                processFile(f.file)
    availableFiles = [f for f in availableFiles if len(f.modules)>0]


def handleUsing(e):
    modules = e.props['module'].split(',')
    for m in modules:
        loadModule(m)


def handleInclude(e):
    file = evalConstExpr(e, e.props['file'])
    canIgnore = 'ignore_missing' in e.props and e.props['ignore_missing'] == '1'
    lookup = [os.path.dirname(e.filename)] + config.searchPath
    errors.pushCtx("included from %s" % e.location())
    for dir in lookup:
        if processFileIfExists(os.path.join(dir, file)):
            errors.popCtx()
            return
    if not canIgnore:
        raise ReaderError(e, "can't find file '%s' in %s" % (file,
                              string.join(lookup, ':')))
    errors.popCtx()


def handleOutput(e):
    file = mk.evalExpr(e.props['file'], use_options=0)
    writer = mk.evalExpr(e.props['writer'], use_options=0)
    if 'method' in e.props:
        method = mk.evalExpr(e.props['method'], use_options=0)
    else:
        method = 'replace'
    config.to_output.append((file, writer, method))


def handleFragment(e):
    if e.props['format'] == config.format:
        if 'file' in e.props:
            f = open(e.props['file'])
            content = f.read()
            f.close()
        else:
            content = e.value
        mk.addFragment(mk.Fragment(content))


HANDLERS = {
    'set':           handleSet,
    'unset':         handleUnset,
    'option':        handleOption,
    'using':         handleUsing,
    'template':      handleTemplate,
    'include':       handleInclude,
    'define-rule':   handleDefineRule,
    'define-tag':    handleDefineTag,
    'tag-info':      handleTagInfo,
    'output':        handleOutput,
    'fragment':      handleFragment,
    }


def __doProcess(file=None, strdata=None, xmldata=None):
    if xmldata != None:
        m = xmldata
    else:
        # FIXME: validity checking
        try:
            if file != None:
                m = xmlparser.parseFile(file)
            else:
                m = xmlparser.parseString(strdata)
        except xmlparser.ParsingError:
            raise ReaderError(None, "file '%s' is invalid" % file)

    def processNodes(list):
        for e in list:
            if e.name == 'if':
                if evalWeakCondition(e):
                    processNodes(e.children)
            else:
                try:
                    h=HANDLERS[e.name]
                except(KeyError):
                    raise ReaderError(e, "unknown tag '%s'" % e.name)
                h(e)
    
    try:
        processNodes(m.children)
    except ReaderError, ex:
        raise ex
    # FIXME: enable this code when finished programming:
    #except Exception, ex:
    #    raise ReaderError(e, ex)

def processFile(filename):
    if not os.path.isfile(filename):
        raise ReaderError(None, "file '%s' doesn't exist" % filename)
    if config.verbose:
        print 'loading %s...' % filename
    newdir = os.path.dirname(os.path.abspath(filename))
    if newdir not in sys.path:
        sys.path.append(newdir)
    __doProcess(file=filename)

def processFileIfExists(filename):
    if os.path.isfile(filename):
        processFile(filename)
        return 1
    else:
        return 0

def processString(data):
    __doProcess(strdata=data)

def processXML(data):
    __doProcess(xmldata=data)


# -------------------------------------------------------------------------

def setStdVars():
    mk.setVar('LF', '\n')
    mk.setVar('SPACE', '$(" ")', eval=0)
    mk.setVar('DOLLAR', '&dollar;')
    mk.setVar('OUTPUT_FILE', config.output_file)
    mk.setVar('FORMAT', config.format)

def setOverrideVars():
    for v in config.defines:
        mk.setVar(v, config.defines[v])
        mk.override_vars[v] = config.defines[v]
    

def read(filename):
    try:
        setStdVars()
        setOverrideVars()
        buildModulesList()
        loadModule('common')
        loadModule(config.format)
        processFile(filename)
        finalize.finalize()
        return 1
    except errors.ErrorBase, e:
        sys.stderr.write(str(e))
        return 0
