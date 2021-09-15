

class PackedList:
    members =  []

    def __class_getitem__(cls, params):
        cls.members.append(params)
