import os, re, urllib
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class Page(db.Model):
    name = db.StringProperty
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now=True)
    links = db.StringListProperty()
    WikiName = re.compile("((?:[A-Z][a-z]+){2,})")
    BracketName = re.compile("(\[\[(.*?)\]\])")
    
    def html(self):
        html = self.content.replace("\n", "<br/>")
        html = Page.WikiName.sub(r'<a href="/show?page=\1">\1</a>', html)
        html = Page.BracketName.sub(r'<a href="/show?page=\2">\2</a>', html)
    	url = re.compile("((?:[a-z]+)://[-&;:?$#./0-9a-zA-Z]+)")
        html = url.sub(r'<a href="\1">\1</a>', html)
        return html
    
    def create_links(self):
        links = Page.WikiName.findall(self.content)
        for link in Page.BracketName.findall(self.content):
            links.append(link[1])
        self.links = links

    def backlinks(self):
        query = db.Query(Page)
        return query.filter("links =", self.wiki_name()).fetch(1000)

    def put_with_retry(self):
        count = 0
        while count < 3:
            try:
                return self.put()
            except:
                count += 1
        else:
            raise datastore._ToDatastoreError()

    def wiki_name(self):
        return self.key().name()[1:] # 頭の-を取る
    
    @classmethod
    def new(cls, wiki_name):
        return cls(key_name = "-"+wiki_name) # 頭に-を足す
    
    @classmethod
    def get_by_wiki_name_with_retry(cls, wiki_name):
        count = 0
        while count < 3:
            try:
                return cls.get_by_key_name("-"+wiki_name)
            except:
                count += 1
        else:
            raise datastore._ToDatastoreError()

class CreatePage(webapp.RequestHandler):
    def post(self):
        page = Page.new(self.request.get('page'))
        page.content = self.request.get('content')
        page.create_links()
        page.put()
        self.redirect("/show?page="+urllib.quote(page.wiki_name().encode('utf-8')))

    def get(self):
        page = self.request.get('page')
        path = os.path.join(os.path.dirname(__file__), 'new.html')
        self.response.out.write(template.render(path, {'page': page}))

class ShowPage(webapp.RequestHandler):
    def get(self):
        page = Page.get_by_wiki_name_with_retry(self.request.get('page'))
        if page==None:
            self.redirect("/create?page="+urllib.quote(self.request.get('page').encode('utf-8')))
            return
        path = os.path.join(os.path.dirname(__file__), 'show.html')
        self.response.out.write(template.render(path, {
          "page_name": page.wiki_name(),
          "content": page.html(),
          "backlinks": page.backlinks(),
          "date": page.date}))

class EditPage(webapp.RequestHandler):
    def get(self):
        page = Page.get_by_wiki_name_with_retry(self.request.get('page'))
        if page==None:
            self.redirect("/create?page="+urllib.quote(self.request.get('page').encode('utf-8')))
            return
        path = os.path.join(os.path.dirname(__file__), 'edit.html')
        self.response.out.write(template.render(path, {
          "page_name": page.wiki_name(),
          "content": page.content}))
    
    def post(self):
        page = Page.get_by_wiki_name_with_retry(self.request.get('page'))
        if page==None:
        	page = Page.new(self.request.get('page'))
        if self.request.get('content')=="":
            page.delete()
            self.redirect("/show?page=FrontPage")
            return
        page.content = self.request.get('content')
        page.create_links()
        page.put()
        self.redirect("/show?page="+urllib.quote(page.wiki_name().encode('utf-8')))

application = webapp.WSGIApplication(
  [('/create', CreatePage), ('/show', ShowPage), ('/edit', EditPage)],
  debug=True)
run_wsgi_app(application)
