from django.db import models

# Create your models here.


class Category(models.Model):
    class Admin:
        pass

class Subscription(models.Model):
    class Admin:
        pass

class DatatreeNodeData(models.Model):
    title = models.CharField(maxlength=256)
    text_data = models.TextField(blank=True)
    file_data = models.FileField(upload_to='/esp/uploaded_data/', blank=True)
    def __str__(self):
        return self.title

    class Admin:
        pass

class IllegalTreeRefactor(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Datatree(models.Model):
    rangestart = models.IntegerField(editable=False, default=0)
    rangeend = models.IntegerField(editable=False, default=1)
    parent = models.ForeignKey('self', null=True, blank=True)
    node_data = models.ForeignKey(DatatreeNodeData, null=True, blank=True)
    def children(self):
        return Datatree.objects.filter(parent__pk=self.id)

    def sizeof(self):
        return self.rangeend - self.rangestart
    def move(self, newstart):
        print "Moving..." + str(self)
        curr_size = self.sizeof()
        self.rangestart = newstart
        self.rangeend = self.rangestart + curr_size
        print str(self) + ' ' + str(newstart) + ' '
        super(Datatree, self).save()
        self.refactor()
        
    def __str__(self):
        try:
            return str(self.rangestart) + ' .. ' + str(self.rangeend) + ' <' + str(self.node_data) + '>'
        except Exception:
            return str(self.rangestart) + ' .. ' + str(self.rangeend)

    def total_size_of_children(self):
        total_size=0
        for child in self.children():
            total_size += child.sizeof()
        return total_size
    
    def refactor(self):
        print "refactor()"
        childsize = self.total_size_of_children()
        selfsize = self.sizeof()
        curr_children = self.children()
        numchildren = curr_children.count()


        if childsize > selfsize - 1:
            print "Autoresizing..." + str(childsize) + ' ' + str(selfsize - 1) + ' ' + str(self)
            self.resize(childsize + selfsize + 1)

        if numchildren == 0:
            print "No children: " + str(curr_children)
            return

        spacing = int( (selfsize - childsize) / numchildren )

        curr_location = self.rangestart + 1

        for child in curr_children:
            print "Moved child: " + str(child)
            child.move(curr_location)
            curr_location += child.sizeof() + spacing

    def resize(self, newsize):
        self.rangeend = self.rangestart + newsize
        super(Datatree, self).save()
        if self.parent != None and self.parent != self:
            self.parent.refactor()

    def autoenlarge(self):
        self.resize(sizeof()*2)

    def space_available_after(self, node):
        min_start = node.rangeend

        for child in self.children():
            if node.rangestart < child.rangestart:
                min_start = min(child.rangestart, min_start)

        return node.rangeend - min_start

    class Admin:
        pass

#    @transaction.commit_on_success
    def save(self):
        print "Saved"
        # Ugly hack to prevent loop trees
        if self.parent == self:
            self.parent = None
            
        super(Datatree, self).save()
        t = self.parent
        if t != None and t != self:
            if t.space_available_after(self) < self.sizeof():
                t.refactor()
        else:
            self.refactor()



class SubTree(Datatree):
    class Admin:
        pass
