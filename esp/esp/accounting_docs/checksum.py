
class BadChecksumException(Exception):
    pass

def _checksum(code, rotors):
    def rotor_iter():
        r_set = [[] for i in range(rotors)]
        yield r_set
        while True:
            r_copy = [r for r in r_set]
            r = r_set.pop(0)
            r_set.append(r)
            for r in r_copy: yield r
    r_iter = rotor_iter()
    r_set = r_iter.next()
    for x in code:
        r = r_iter.next()
        r.append(int(x))
    sums = [-sum(r) % 10 for r in r_set]
    cksum = ''.join([str(i) for i in sums])
    good = sum(sums) == 0
    return good, cksum

class Checksum(object):
    def __init__(self, rotors=2, base_length=8, pad_with='0'):
        self.base_length = base_length
        self.rotors = rotors
        self.pad_with = pad_with

    def __call__(self, code):
        return _checksum(code, self.rotors)

    def verify(self, code):
        if len(code) != (self.base_length + self.rotors): return False
        return _checksum(code, self.rotors)[0]

    def calculate(self, code):
        padding = ''
        for i in range(0, self.base_length - len(code)):
            padding += pad_with
        cks = padding + code
        return cks + _checksum(code, self.rotors)[1]

    def assert_code(self, code):
        if not self.verify(code): raise BadChecksumException
