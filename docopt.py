from getopt import gnu_getopt, GetoptError
from ast import literal_eval
import sys
import re


class Argument(object):

    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        return 'Argument(%r, %r)' % (self.name, self.value)

    def __eq__(self, other):
        return repr(self) == repr(other)


class Option(object):

    def __init__(self, short=None, long=None, value=False, parse=None):
        is_flag = True
        if parse:
            split = parse.strip().split('  ')
            options = split[0].replace(',', ' ').replace('=', ' ')
            description = ''.join(split[1:])
            for s in options.split():
                if s.startswith('--'):
                    long = s.lstrip('-')
                elif s.startswith('-'):
                    short = s.lstrip('-')
                else:
                    is_flag = False
            if not is_flag:
                matched = re.findall('\[default: (.*)\]', description)
                value = argument_eval(matched[0]) if matched else False
                short = short + ':' if short else None
                long = long + '=' if long else None
        self.short = short
        self.long = long
        self.value = value

    @property
    def is_flag(self):
        if self.short:
            return not self.short.endswith(':')
        if self.long:
            return not self.long.endswith('=')

    @property
    def name(self):
        s = self.long or self.short
        s = s.rstrip(':').rstrip('=')
        ret = s[0] if s[0].isalpha() else '_'
        for ch in s[1:]:
            ret += ch if ch.isalpha() or ch.isdigit() else '_'
        return ret

    @property
    def forms(self):
        if self.short:
            yield '-' + self.short.rstrip(':')
        if self.long:
            yield '--' + self.long.rstrip('=')

    def __repr__(self):
        return 'Option(%s, %s, %s)' % (repr(self.short),
                                       repr(self.long),
                                       repr(self.value))

    def __eq__(self, other):
        return repr(self) == repr(other)


class Options(object):

    def __init__(self, **kw):
        self.__dict__ = kw

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        return 'Options(%s)' % ',\n    '.join(["%s=%s" % (kw, repr(a))
                                           for kw, a in self.__dict__.items()])


def argument_eval(s):
    try:
        return literal_eval(s)
    except (ValueError, SyntaxError):
        return s


def docopt(doc, args=sys.argv[1:], help=True, version=None):
    docopts = [Option(parse='-' + s) for s in re.split('^ *-|\n *-', doc)[1:]]
    try:
        getopts, args = gnu_getopt(args,
                            ''.join([d.short for d in docopts if d.short]),
                            [d.long for d in docopts if d.long])
    except GetoptError as e:
        exit(e.msg)
    for k, v in getopts:
        for o in docopts:
            if k in o.forms:
                o.value = True if o.is_flag else argument_eval(v)
            if help and k in ('-h', '--help'):
                exit(doc.strip())
            if version is not None and k == '--version':
                exit(version)
    return Options(**dict([(o.name, o.value) for o in docopts])), args


class Token(object):

    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return 'Token(%r)' % self.token

    def __eq__(self, other):
        return repr(self) == repr(other)


def do_longs(parsed, raw, options, parse):
    try:
        i = raw.index('=')
        raw, value = raw[:i], raw[i+1:]
    except ValueError:
        value = None
    option = [o for o in options if o.long and o.long.startswith(raw)]
    assert len(option) == 1
    option = option[0]
    if not option.is_flag:
        if value is None:
            if not parse:
                raise GetoptError('option --%s requires argument' % option)
            value, parse = parse[0], parse[1:]
    elif value is not None:
        raise GetoptError('option --%s must not have an argument' % option)
    option.value = value or True
    parsed += [option]
    return parsed, parse


def do_shorts(parsed, raw, options, parse):
    while raw != '':
        option = [o for o in options if o.short and o.short.startswith(raw[0])]
        assert len(option) == 1
        option = option[0]
        raw = raw[1:]
        if option.is_flag:
            value = True
        else:
            if raw == '':
                if not parse:
                    raise GetoptError('option -%s requires argument' % option)
                raw, parse = parse[0], parse[1:]
            value, raw = raw, ''
        option.value = value
        parsed += [option]
    return parsed, parse


class Pattern(object):

    def __init__(self, *arg, **kw):
        parse = kw['parse'] if 'parse' in kw else None
        options = kw['options'] if 'options' in kw else []
        arguments = kw['arguments'] if 'arguments' in kw else []
        if parse:
            parse = parse.split() if type(parse) == str else parse
            parsed = []
            while parse:
                if parse[0] == '--':
                    parsed += [Argument(None, v) for v in parsed[1:]]
                    break
                elif parse[0] in list('[](){}|'):
                    parsed += [Token(parse[0])]
                    parse = parse[1:]
                elif parse[0][:2] == '--':
                    parsed, parse = do_longs(parsed, parse[0][2:], options, parse[1:])
                elif parse[0][:1] == '-' and parse[0] != '-':
                    parsed, parse = do_shorts(parsed, parse[0][1:], options, parse[1:])
                else:
                    parsed += [Argument(None, parse[0])]
                    parse = parse[1:]
            arg = parsed
        self.arg = arg


    def __repr__(self):
        return 'Pattern(%s)' % ', '.join([repr(a) for a in self.arg])

    def __eq__(self, other):
        return repr(self) == repr(other)
