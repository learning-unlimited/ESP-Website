dojo.provide("Markdown.Markdown");
Markdown.Markdown.markdown = (new Showdown.converter()).makeHtml;
dojox.dtl.register.filters("Markdown", {"Markdown": ["markdown"]});