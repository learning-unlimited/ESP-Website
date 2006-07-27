from esp.lib.markdown import ImagePattern, LinkPattern, Markdown

class ESPImagePattern (ImagePattern):
    """ Track if detected images are known or unknown to media{} """
    media = { }

    def handleMatch(self, m, doc):
        el = super(self, ImagePattern).handleMatch(m, doc)

        src = el.getAttribute('src')

        if media.has_key(src):
            media[src] = True
        else:
            media[src] = False


class ESPLinkPattern (LinkPattern):
    """ Track if detected URLs are known or unknown to media{}, if they are under a relevant path """
    media = { }

    def handleMatch(self, m, doc):
        el = super(self, ImagePattern).handleMatch(m, doc)

        src = el.getAttribute('src')

        # Links can point to non- web media content;
        # only get ones that do point to media that we're managing
        if src[:6] == 'media/':
            if media.has_key(src):
                media[src] = True
            else:
                media[src] = False


class ESPMarkdown(Markdown):
    """ Markdown formatter class, with ESP-customized modifications """

    media = { }

    def BrokenLinks(self):
        """ Return a list of all media that this Markdown parser has encountered """
        broken_links = []

        for key in self.media.keys():
            if self.media[key] == False:
                broken_links.append(key)

        return broken_links

    def UnusedLinks(self):
        """ Return a list of all media that this Markdown parser knows about but has not encountered a reference to """
        unused_links = []

        for key in self.media.keys():
            if self.media[key] == None:
                unused_links.append(key)

        return unused_links

    def UsedLinks(self):
        """ Return a list of all existing media that Markdown-text encountered by this parser uses """
        used_links = []

        for key in self.media.keys():
            if self.media[key] == True:
                used_links.append(key)

        return used_links
        

    def __init__(self, source=None):
        """ Handle objects that have been overloaded to deal with the media dictionary """

        self.LINK_PATTERN = ESPLinkPattern(LINK_RE)
        self.LINK_ANGLED_PATTERN = ESPLinkPAttern(LINK_ANGLED_RE)
        self.IMAGE_LINK_PATTERN = ESPImagePattern(IMAGE_LINK_RE)

        super(self, Markdown).__init__(source)

        for i in [ IMAGE_LINK_PATTERN,
                   LINK_PATTERN,
                   LINK_ANGLED_PATTERN ]:
            i.media = media
        
