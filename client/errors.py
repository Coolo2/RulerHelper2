

class MildError(Exception):
    
    def __init__(self, description, title = "Oops!"):
        self.description = description 
        self.title = title