
class Type():
    def __init__(self, name : str, length : int = None):
        self.name = name 
        self.length = length 

    def __str__(self):
        extra = ""
        if self.name == "varchar":
            extra = f"({self.length})"
        
        return f"{self.name}{extra}"

class OrderType(Type):
    pass

String = Type("string")
Int = Type("integer")
Timestamp = Type("timestamp")
Date = Type("date")
Float = Type("real")
Any = Type("")
Datetime = Timestamp

OrderAscending = OrderType("ASC")
OrderDescending = OrderType("DESC")
OrderRandom = OrderType("RANDOM()")

LIKE = "LIKE"
EQUALS = "EQUALS"

class VarChar(Type):
    def __init__(self, length : int):
        super().__init__("varchar", length)

def from_str(string : str) -> Type:
    if string.lower() == "integer":
        return Int 
    elif string.lower() == "string":
        return String 
    elif "varchar" in string.lower():
        _inside_parenthesis = string[string.index("(")+1:string.index(")")]
        return VarChar(int(_inside_parenthesis))
    else:
        return Any