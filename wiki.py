# -*- coding: utf-8 -*-
import os, re, urllib
from xml.sax.saxutils import escape
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
import dnsbl

def db_retry(func):
    count = 0
    while count < 3:
        try:
            return func()
        except:
            count += 1
        else:
            raise datastore._ToDatastoreError()

class Page(db.Model):
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now=True)
    links = db.StringListProperty()
    WikiName = re.compile("((?:[A-Z][a-z]+){2,}|\[\[(.*?)\]\])")
    
    def html(self):
        html = escape(self.content).replace("\n","<br/>")
        html = Page.WikiName.sub(lambda x: '<a title="'+(x.group(2) or x.group(1))+'" href="/'+(x.group(2) or x.group(1))+'"'+('' if Page.is_exists(x.group(2) or x.group(1)) else ' class="new-page"')+'>'+(x.group(1))+'</a>', html)
    	url = re.compile("((?:[a-z]+)://[-&;:?$#./0-9a-zA-Z]+)")
        html = url.sub(r'<a href="\1">\1</a>', html)
        return html
    
    def create_links(self):
        links = []
        for link in Page.WikiName.findall(self.content):
            links.append(link[1] or link[0])
        self.links = links

    def backlinks(self):
        query = db.Query(Page)
        return query.filter("links =", self.wiki_name()).fetch(1000)

    def put_with_retry(self):
        return db_retry(lambda: self.put())
        
    def wiki_name(self):
        return self.key().name()[1:]
    
    @classmethod
    def is_exists(cls, wiki_name):
        return cls.get_by_wiki_name_with_retry(wiki_name)!=None
    
    @classmethod
    def new(cls, wiki_name):
        return cls(key_name = "-"+wiki_name)
    
    @classmethod
    def get_by_wiki_name_with_retry(cls, wiki_name):
        return db_retry(lambda: cls.get_by_key_name("-"+wiki_name))


def checkSpam(self):
    if dnsbl.CheckSpamIP(self.request.remote_addr):
        path = os.path.join(os.path.dirname(__file__), 'block.html')
        self.response.out.write(template.render(path, {'ip': self.request.remote_addr}))
        return True
    return False

class CreatePage(webapp.RequestHandler):
    def post(self):
        if checkSpam(self): return
        page = Page.new(self.request.get('page'))
        page.content = self.request.get('content')
        page.create_links()
        page.put_with_retry()
        self.redirect("/"+urllib.quote(page.wiki_name().encode('utf-8')))

    def get(self):
        page = self.request.get('page')
        path = os.path.join(os.path.dirname(__file__), 'new.html')
        self.response.out.write(template.render(path, {'page': page}))

class ShowPage(webapp.RequestHandler):
    def get(self):
        name = self.request.get('page') or urllib.unquote(unicode(self.request.path[1:])).encode('raw_unicode_escape').decode('utf-8')
        if name=='':
            return self.redirect("/FrontPage")
        page = Page.get_by_wiki_name_with_retry(name)
        if page==None:
            return self.redirect("/create?page="+urllib.quote(name.encode('utf-8')))
        recent = db.Query(Page).order("-date").fetch(10)
        
        path = os.path.join(os.path.dirname(__file__), 'show.html')
        self.response.out.write(template.render(path, {
          "page_name": page.wiki_name(),
          "content": page.html(),
          "backlinks": page.backlinks(),
          "recent": recent,
          "date": page.date}))

class EditPage(webapp.RequestHandler):
    def get(self):
        page = Page.get_by_wiki_name_with_retry(self.request.get('page'))
        if page==None:
            return self.redirect("/create?page="+urllib.quote(self.request.get('page').encode('utf-8')))
        path = os.path.join(os.path.dirname(__file__), 'edit.html')
        self.response.out.write(template.render(path, {
          "page_name": page.wiki_name(),
          "content": page.content}))
    
    def post(self):
        if checkSpam(self): return
        page = Page.get_by_wiki_name_with_retry(self.request.get('page'))
        if page==None:
        	page = Page.new(self.request.get('page'))
        if self.request.get('content')=="":
            page.delete()
            return self.redirect("/FrontPage")
        page.content = self.request.get('content')
        page.create_links()
        page.put_with_retry()
        self.redirect("/"+urllib.quote(page.wiki_name().encode('utf-8')))

application = webapp.WSGIApplication(
  [('/create', CreatePage), ('/edit', EditPage), ('/show', ShowPage), ('/.*', ShowPage),],
  debug=True)
run_wsgi_app(application)
