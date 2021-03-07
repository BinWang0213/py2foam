"""
field_parser.py
parser for field data

"""
import os
import numpy as np

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
        
        info=""
        for k,p in self.foamData['FoamFile'].items():
            if(k=="location"): info+=f"{k:<10}\t\"{p}\";\n"
            else: info+=f"{k:<10}\t{p};\n"
        self.header=foam_comment+"FoamFile\n{\n%s}\n" %(info)
        
        return self.header
    
    def _unit_str(self):
        #currently only SI unit is support
        self.unit="dimensions [%s];\n\n" %(" ".join([str(int(i)) for i in self.foamData['dimensions']]) )
        return self.unit
    
    def _data_str(self):
        #collect data string from field data
        return "NA"

    def write(self,fname):
        """Write dict fields into openfoam file"""
        file_str=_header_str()+_unit_str+_data_str
        with open(fp, "wb") as outf:
            outf.write(file_str)
        return fp