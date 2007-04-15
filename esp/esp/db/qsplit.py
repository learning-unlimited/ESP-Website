
from django.db.models.query import Q as DjangoQ
from django.utils.datastructures import SortedDict

 
def replaceDict(string, dict):
    " Will take a dictioary and an arbitrary string, and replace the string with the dictioary."
    if len(dict) == 0:
        return string
    
    curDict = dict.copy()
    keys = curDict.keys()
    keys.sort(lambda x,y: cmp(len(y), len(x)))
    key = keys[0]
    val = curDict[key]

    del curDict[key]

    offset  = 0
    strings = [string]

    
    while strings[-1].find(key) != -1:
        loc = strings[-1].find(key)
        
        strings.append(strings[-1][len(key) + loc:])

        strings[-2] = strings[-2][:loc]
        

    return val.join([replaceDict(s,curDict) for s in strings])
    

    

class QSplit(DjangoQ):
    " Encapsulates a single JOIN-type query into one object "

    def __init__(self, q):
        " Creates a single Q-ish object that separates itself from other Q objects. "
        self.q = q

    def get_sql(self, opts):
        " This will generate the correct (joins, where, params) tuple. "
        from django.conf import settings

        if 'mysql' in settings.DATABASE_ENGINE.lower():
            tick = '`'
        elif 'postgres' in settings.DATABASE_ENGINE.lower():
            tick = '"'
        else:
            tick = ''        
        joins, where, params = self.q.get_sql(opts)
        key_replace = {}
        joins2      = SortedDict()
        where2      = []
        

        for key, val in joins.items():
            cur_key = key.strip(tick)
            cur_val = '%s__%s' % (key.strip(tick), hash(self))
            
            key_replace[cur_key] = cur_val

            joins2['%s%s%s' % (tick, cur_val, tick)] = val

            

        for key, val in joins2.items():
            joins2[key] = (val[0],val[1],replaceDict(val[2],key_replace))


        where2 = [replaceDict(clause, key_replace) for clause in where]
        return joins2, where2, params
