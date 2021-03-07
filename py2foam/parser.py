import os
import re
from collections import OrderedDict

from lark import Lark, Transformer, v_args

_foam_comment= [
            "/*--------------------------------*- C++ -*----------------------------------*\\",
            "  ==========                |",
            "  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox",
            "   \\\\    /   O peration     | Website:  https://openfoam.org",
            "    \\\\  /    A nd           | Version:  6",
            "     \\\\/     M anipulation  |",
            "\*---------------------------------------------------------------------------*/",
            "/*         Created by py2foam:  https://github.com/BinWang0213/py2foam       */",
            "/*---------------------------------------------------------------------------*/\n\n"
        ]
foam_comment="\n".join(_foam_comment)

def parseFoamDict(string):
    #parser openfoam dict format using lark
    ### Create the openfoam parser with Lark, using the LALR algorithm
    #TODO the grammar currently only support field dict
    parser = Lark(field_grammar, parser='lalr',
                    lexer='standard',
                    propagate_positions=False,
                    maybe_placeholders=False,
                    transformer=TreeToDict())
    #print(_removeComments(string))
    return parser.parse(_removeComments(string))

def printdict(d, indent=0):
    #Print nested dict in a nice format
    for key, value in d.items():
        print('\t' * indent + str(key))
        if isinstance(value, dict):
            printdict(value, indent+1)
        else:
            print('\t' * (indent+1) + str(value))

def _removeComments(string):
    # /* COMMENT */
    # pp.cStyleComment
    string = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "", string)
    # // COMMENT
    # pp.dblSlashComment
    string = re.sub(re.compile("//.*?\n"), "", string)
    return string

field_grammar = r"""
    start: value+

    value: pair
         | object
    object : var "{" [value (value)*] "}"

    pair   : var itemvals ";"
    itemvals: number
             | var
             | string
             | field_uniform
             | field_nonuniform
             | array
    
    array  : "[" [number (number)*] "]" 
    
    
    number : SIGNED_NUMBER
    var : CNAME
    string : ESCAPED_STRING
    
    fieldvalue : number | "(" [number (number)*] ")"
    field_uniform : var fieldvalue
    field_nonuniform : var var number fieldvalue

    CNAME : /[a-zA-Z0-9._<>]+/
    %import common.ESCAPED_STRING
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""

class TreeToDict(Transformer):
    @v_args(inline=True)
    def string(self, s):
        return s[1:-1]

    @v_args(inline=True)
    def var(self, s):
        return str(s)
    number = v_args(inline=True)(float)

    #avoid unnecessary list
    def fieldvalue(self, f):  
        if(len(f)==1): return f[-1]
        else: return f
    field_nonuniform = list
    field_uniform = list
    def itemvals(self,f): return f[-1]
    
    array = list
    pair = tuple
    def object(self,f): 
        return (f[0],f[1:])
    def value(self,f):
        name,data=f[-1]
        if isinstance(data, list) and isinstance(data[0],tuple):
            return (name,OrderedDict(data))
        else:
            return f[-1]
    
    start=OrderedDict


##------------------Old parsers from openfoamparser---------------
def parse_internal_field(fn):
    """
    parse internal field, extract data to numpy.array
    :param fn: file name
    :return: numpy array of internal field
    """
    if not os.path.exists(fn):
        print("Can not open file " + fn)
        return None
    with open(fn, "rb") as f:
        content = f.readlines()
        return parse_internal_field_content(content)

def parse_internal_field_content(content):
    """
    parse internal field from content
    :param content: contents of lines
    :return: numpy array of internal field
    """
    is_binary = is_binary_format(content)
    for ln, lc in enumerate(content):
        if lc.startswith(b'internalField'):
            if b'nonuniform' in lc:
                return parse_data_nonuniform(content, ln, len(content), is_binary)
            elif b'uniform' in lc:
                return parse_data_uniform(content[ln])
            break
    return None

def parse_data_uniform(line):
    """
    parse uniform data from a line
    :param line: a line include uniform data, eg. "value           uniform (0 0 0);"
    :return: data
    """
    if b'(' in line:
        return np.array([float(x) for x in line.split(b'(')[1].split(b')')[0].split()])
    return float(line.split(b'uniform')[1].split(b';')[0])


def parse_data_nonuniform(content, n, n2, is_binary):
    """
    parse nonuniform data from lines
    :param content: data content
    :param n: line number
    :param n2: last line number
    :param is_binary: binary format or not
    :return: data
    """
    num = int(content[n + 1])
    if not is_binary:
        if b'scalar' in content[n]:
            data = np.array([float(x) for x in content[n + 3:n + 3 + num]])
        else:
            data = np.array([ln[1:-2].split() for ln in content[n + 3:n + 3 + num]], dtype=float)
    else:
        nn = 1
        if b'vector' in content[n]:
            nn = 3
        elif b'symmTensor' in content[n]:
            nn = 6
        elif b'tensor' in content[n]:
            nn = 9
        buf = b''.join(content[n+2:n2+1])
        vv = np.array(struct.unpack('{}d'.format(num*nn),
                                    buf[struct.calcsize('c'):num*nn*struct.calcsize('d')+struct.calcsize('c')]))
        if nn > 1:
            data = vv.reshape((num, nn))
        else:
            data = vv
    return data

def is_binary_format(content, maxline=20):
    """
    parse file header to judge the format is binary or not
    :param content: file content in line list
    :param maxline: maximum lines to parse
    :return: binary format or not
    """
    for lc in content[:maxline]:
        if b'format' in lc:
            if b'binary' in lc:
                return True
            return False
    return False