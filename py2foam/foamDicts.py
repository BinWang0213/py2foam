"""
field_parser.py
parser for field data

"""
import os
import numpy as np

from collections import OrderedDict
from .parser import foam_comment, parseFoamDict, printdict

class foamField:
    """Openfoam dict class that support read/write openfoam dict file
       especially for the file in the "0" folder
    """

    def __init__(self, fname=None):
        self.fname = fname
        
        #openfoam file string
        self.header = ""
        self.unit = ""
        self.data = ""

        #Openfoam nested dict data
        self.foamData={}

        if fname:
            self.read(fname)
    
    def __repr__(self):
        printdict(self.foamData)
        return ""
    
    def __getitem__(self, key):
        return self.foamData[key]
    
    def read(self,fname):
        """Read openfoam file"""
        with open(fname, "r") as f:
            self.foamData=parseFoamDict(f.read())
        return self.foamData

    def _header_str(self):
        #Write header string
        info=""
        for k,p in self.foamData['FoamFile'].items():
            if(k=="location"): info+="\t" + f"{k:<10}\t\"{p}\";\n"
            else: info+="\t" + f"{k:<10}\t{p};\n"
        self.header=foam_comment+"FoamFile\n{\n%s}\n" %(info) + "\n"
        
        return self.header
    
    def _unit_str(self):
        #Write unit string
        self.unit="dimensions [%s];\n\n" %(" ".join([str(int(i)) for i in self.foamData['dimensions']]) )
        self.unit+="\n"
        return self.unit

    def _data_str(self):
        #Write internal and boundary field string

        string=""
        #internal field data
        name='internalField'
        string+= field2foam({name:self.foamData[name]}, level=0)
        string+="\n"

        #boundary field data
        name='boundaryField'
        string+= field2foam({name:self.foamData[name]}, level=0)
        string+="\n"

        self.data=string
        return self.data

    def write(self,fname):
        """Write dict fields into openfoam file"""
        file_str=self._header_str()+self._unit_str()+self._data_str()
        with open(fname, "w",newline='\n') as outf:
            outf.write(file_str)


def countDictLevels(d):
    #Count how many levels in a dict
    return max(countDictLevels(v) if isinstance(v,dict) else 0 for v in d.values()) + 1

def field2foam(dict,level=0):
    #convert foam dict data into foam string
    lines=_field2foam(dict,level=level)
    return "\n".join(lines) + "\n"

def _field2foam(foam_object,level=0, maxlength=50):
    #recursive nested dict to foam dict string
    #modified from https://github.com/napyk/foamfile
    lines = []
    if type(foam_object) in (list, tuple):
        #print('Cond1',level)
        for list_entry in foam_object:
            if type(list_entry) in (list, tuple):
                #print("\t 1l",list_entry)
                lines.append("\t" * level + "(" + " ".join(_field2foam(list_entry, 0)) + ")")
            elif type(list_entry) in (dict, OrderedDict):
                #print("\t 1d",list_entry)
                lines.append("\t" * level + "{")
                lines += _field2foam(list_entry, level + 1)
                lines.append("\t" * level + "}")
            else:
                #print("\t 1o",list_entry)
                lines.append("\t" * level + str(list_entry))
    elif type(foam_object) in (dict, OrderedDict):
        #print("Cond2",level)
        if len(foam_object) > 0:
            tab_expander = max([len(i) for i in foam_object if type(i) is str]) + 1
        for key, value in foam_object.items():
            if type(value) in (dict, OrderedDict):
                #print("\t 2d",key,value)
                lines += ["\t" * level + f"{key}", "\t" * level + "{"]
                lines += _field2foam(value, level + 1)
                lines.append("\t" * level + "}")
            elif type(value) in (list, tuple):
                #print("\t 2l",key,value)
                if (value[0] in ["uniform","nonuniform"]): #Special for field wrtier
                    lines += ["\t" * level + f"{key}"]
                    if(value[0] == "nonuniform"): 
                        lines[-1] += " "+" ".join(_field2foam(value[:-2], 0)) + f" {int(value[2])}"
                        lines += ["\t" * level + "("]
                        lines += _field2foam(value[-1], level)
                        lines.append("\t" * level + ");")
                    if(value[0] == "uniform"):
                        lines[-1] += " " + " ".join(_field2foam(value, 0)) + ";"
                else:
                    lines += ["\t" * level + f"{key}", "\t" * level + "("]
                    lines += _field2foam(value, level + 1)
                    lines.append("\t" * level + ");")
            else:
                if key in ["#include", "#includeIfPresent", "#includeEtc", "#includeFunc", "#remove"]:
                    lines.append("\t" * level + str(key).ljust(tab_expander) + str(value))
                else:
                    #print("\t 2o",key,value)
                    lines.append("\t" * level + str(key).ljust(tab_expander) + str(value) + ";")
    return lines