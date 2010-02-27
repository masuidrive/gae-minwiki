import os, re
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class Page(db.Model):
    name = db.StringProperty
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now=True)
    links = db.StringListProperty()
    
    def html(self):
    	link = re.compile("(([A-Z][a-z]+){2,})")
        return link.sub(r'<a href="/show?page=\1">\1</a>', self.content.replace("\n", "<br/>"))
    
    def create_links(self):
        link = re.compile("((?:[A-Z][a-z]+){2,})")
        self.links = link.findall(self.content)
    
    def backlinks(self):
        query = db.Query(Page)
        return query.filter("links =", self.key().name()).fetch(1000)

class CreatePage(webapp.RequestHandler):
    def post(self):
        page = Page(key_name = self.request.get('page'))
        page.content = self.request.get('content')
        page.create_links()
        page.put()
        self.redirect("/show?page="+page.key().name())

    def get(self):
        page = self.request.get('page')
        path = os.path.join(os.path.dirname(__file__), 'new.html')
        self.response.out.write(template.render(path, {'page': page}))

class ShowPage(webapp.RequestHandler):
    def get(self):
        page = Page.get_by_key_name(self.request.get('page'))
        if page==None:
            self.redirect("/create?page="+self.request.get('page'))
            return
        backlinks = []
        for link in page.backlinks():
            backlinks.append(link.key().name())
        path = os.path.join(os.path.dirname(__file__), 'show.html')
        self.response.out.write(template.render(path, {
          "page_name": page.key().name(),
          "content": page.html(),
          "backlinks": backlinks,
          "date": page.date}))

class EditPage(webapp.RequestHandler):
    def get(self):
        page = Page.get_by_key_name(self.request.get('page'))
        if page==None:
            self.redirect("/create?page="+self.request.get('page'))
            return
        path = os.path.join(os.path.dirname(__file__), 'edit.html')
        self.response.out.write(template.render(path, {
          "page_name": page.key().name(),
          "content": page.content}))
    
    def post(self):
        page = Page.get_by_key_name(self.request.get('page'))
        if page==None:
        	page = Page(key_name = self.request.get('page'))
        if self.request.get('content')=="":
            page.delete()
            self.redirect("/show?page=FrontPage")
            return
        page.content = self.request.get('content')
        page.create_links()
        page.put()
        self.redirect("/show?page="+page.key().name())

application = webapp.WSGIApplication(
  [('/create', CreatePage), ('/show', ShowPage), ('/edit', EditPage)],
  debug=True)
run_wsgi_app(application)
