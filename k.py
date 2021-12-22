
#%%
class Node:
    """ A beautiful little thing
    """

    def __init__(self, description="") -> None:
        self.description=description or None


    @property
    def __doc__(self):
        if self.description:
            return self.description

        else:
            return super().__doc__


#%%
print(help(Node))

print(help(Node(description="Nanana")))