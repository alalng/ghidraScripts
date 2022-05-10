#creates a gdb command file containing debugging information for the current program being analyzed

from os.path import exists

#class to implement functions
class Func:
    def __init__(self, func):
        self.name = func.getName()
        self.entry = int(func.getEntryPoint().toString(), 16)
        self.locals = [Var(i) for i in func.getLocalVariables()]
        self.params = [Param(i) for i in func.getParameters()]
        self.ret = func.getReturn() if not func.hasNoReturn() else None
        self.sig = func.getSignature()
        self.frame = func.getStackFrame()
        self.calls = [i.getName() for i in func.getCalledFunctions(None)]
        self.callers = [i.getName() for i in func.getCallingFunctions(None)]

    def __str__(self):
        return "Name: {}, Entry Point: {}, Local Variables: {}, Parameters: {}, Return Value: {}, Func Signature: {}".format(self.name, self.entry, self.locals, self.params, self.ret, self.sig)

#class to implement variables
class Var:
    def __init__(self, variable):
        self.name = variable.getName()
        self.typ = variable.getDataType().toString()
        self.sz = variable.getLength()
        if "undefined" in self.typ:
            if self.typ[9:10] == "1":
                self.typ = "char"
            elif self.typ[9:10] == "2":
                self.typ = ""
            elif self.typ[9:10] == "4":
                self.typ = "int"
            elif self.typ[9:10] == "8":
                self.typ = "long"
        try:
            self.stackOff = variable.getStackOffset()
        except:
            self.stackOff = None

#class to implement parameters
class Param:
    def __init__(self, param):
        self.name = param.getName()
        self.idx = param.getOrdinal()
        self.typ = param.getAutoParameterType()
        registers = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        self.value = registers[self.idx]

#class to implement global variables
class GlobalVar:
    def __init__(self, globalSym):
        self.name = globalSym.getName()
        self.addr = int(globalSym.getAddress().toString(), 16)

    def __str__(self):
        return "Name: {}, Address: {}".format(self.name, hex(self.addr))

#Function definitions:

#get functions and data associated with them
def getFuncs():
    functions = []
    curFunc = getFirstFunction()
    while curFunc is not None:
        if curFunc.isThunk():
            curFunc = getFunctionAfter(curFunc)
            continue
        functions.append(Func(curFunc))
        curFunc = getFunctionAfter(curFunc)
    return functions

#get global variables and function addresses
def getGlobals(program):
    globalVars = []
    globalsyms = program.getSymbolTable().getSymbols(program.getGlobalNamespace())
    for i in globalsyms:
        if i.getSymbolType().toString() != "Function" and i.getAddress().toString() != "NO ADDRESS" and not "." in i.getName() and not i.isExternal():
            globalVars.append(GlobalVar(i))
    return globalVars

#create output file from extracted data
def buildOut(outFile, info):
    globalVars = info[0]
    funcs = info[1]
    contents = "start\n"
    contents += genGlobals(globalVars, funcs)
    contents += genFuncs(funcs)
    writeFile(outFile, contents)
    return 0

#automatically creates local variables when functions are entered
def genFuncs(funcs):
    out = ""
    #command to break on all functions
    funcBreakAll = "define breakAll\n"
    for i in funcs:
        funcBreakAll += "\tbreak *{}\n".format(hex(i.entry)[:-1])
    funcBreakAll += "end"

    for i in funcs:
        localVars = "break *{}\n".format(hex(i.entry)[:-1])
        localVars += "commands\n"
        localVars += "echo Function: {}\\n\n".format(i.sig)
        if i.params != []:
            localVars += "echo Parameters:\\n\n"
            for arg in i.params:
                localVars += "echo Name: {}\n".format(arg.name)
                localVars += "echo , Value: ${}\\n\n".format(arg.value)
        if i.locals != []:
            localVars += "echo local variables:\\n\n"
            for local in i.locals:
                if local.stackOff != None:
                    localVars += "set ${} = *(({} *) ($rbp{}+8))\n".format(local.name, local.typ, local.stackOff)
                localVars += "echo {} {}\\n\n".format(local.typ, local.name)
        localVars += "continue\n"
        localVars += "end\n\n"
        out += localVars
    out += funcBreakAll
    return out

#create variables for global symbols and addresses
def genGlobals(globalSyms, funcs):
    out = ""
    for i in globalSyms:
        out += "set ${} = *{}\n".format(i.name, hex(i.addr)[:-1])
    for i in funcs:
        out += "set ${} = *{}\n".format(i.name, hex(i.entry)[:-1])
    out += "\n"
    return out

#write output to file
def writeFile(fName, contents):
    with open(fName, "w") as f:
        f.write(contents)

def main():
    while True:
        fileName = askString("Hello", "Enter name of output file")
        fileName += "" if fileName[-4:] == ".gdb" else ".gdb"
        if exists(fileName):
            print("Sorry, this file already exists")
            print("Please enter a different file name.")
        else:
            break 
    program = getCurrentProgram()
    info = [getGlobals(program), getFuncs()]
    buildOut(fileName, info)

if __name__ == "__main__":
    main()