class cross_tuple(tuple):
    pass


class cross_set(set):
    def __mul__(self, other):
        """Cartesian product of two sets."""
        ret = cross_set()
        for elemself in self:
            if type(elemself) == cross_tuple:
                elemself = list(elemself)
            else:
                elemself = [elemself]
                
            for elemother in other:
                if type(elemother) == cross_tuple:
                    elemother = list(elemother)
                else:
                    elemother = [elemother]

                ret.add(cross_tuple(elemself+elemother))

                            
        return ret
