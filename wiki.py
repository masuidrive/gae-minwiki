# -*- coding: utf-8 -*-
import os, re, urllib, datetime
from xml.sax.saxutils import escape
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import search
from google.appengine.api import taskqueue
from igo.Tagger import Tagger


def db_retry(func):
    count = 0
    while count < 3:
        try:
            return func()
        except:
            count += 1
        else:
            raise datastore._ToDatastoreError()


tagger = Tagger('ipadic')
page_index = search.Index(name='pages')

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

    def truncated_content(self, size=128):
        body = re.sub(r'[ \t\r\n]+', ' ', self.content)
        return '%s...' % (body[:size]) if len(body) > size else body

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

    def remove_from_searcher(self):
        doc_id = self.wiki_name().encode('utf-8').encode("hex_codec")
        page_index.remove([doc_id])

    def update_searcher(self):
        body = self.content
        content = " ".join(map(lambda m: m.surface.encode('utf-8', 'ignore'), tagger.parse(body)))
        doc = search.Document(
            doc_id=self.wiki_name().encode('utf-8').encode("hex_codec"),
            fields=[search.TextField(name='name', value=self.wiki_name()),
                    search.TextField(name='content', value=content)])
        page_index.add(doc)

    def queue_update_searcher(self):
        taskqueue.add(url='/buildIndex', params={'page': self.wiki_name()})                
    
    @classmethod
    def is_exists(cls, wiki_name):
        return cls.get_by_wiki_name_with_retry(wiki_name)!=None
    
    @classmethod
    def new(cls, wiki_name):
        return cls(key_name = "-"+wiki_name)
    
    @classmethod
    def get_by_wiki_name_with_retry(cls, wiki_name):
        return db_retry(lambda: cls.get_by_key_name("-"+wiki_name))

    @classmethod
    def search(cls, query_):
        query = " ".join(map(lambda m: m.surface.encode('utf-8', 'ignore'), tagger.parse(query_)))
        query_options = search.QueryOptions(
            returned_fields=['name'],
            limit=25)
        query_obj = search.Query(query_string=query, options=query_options)
        results = page_index.search(query=query_obj)
        data = []
        for r in results.results:
            page = Page.get_by_wiki_name_with_retry(r.fields[0].value)
            data.append(page)
        return data


class CreatePage(webapp.RequestHandler):
    def post(self):
        page = Page.new(self.request.get('page'))
        page.content = self.request.get('content')
        page.create_links()
        page.put_with_retry()
        page.queue_update_searcher()
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


class SearchPage(webapp.RequestHandler):
    def get(self):
        query = self.request.get('q')
        if query:
            results = Page.search(query)
            path = os.path.join(os.path.dirname(__file__), 'search_result.html')
            self.response.out.write(template.render(path, {
              "results": results,
              "query": query}))
        else:
            path = os.path.join(os.path.dirname(__file__), 'search.html')
            self.response.out.write(template.render(path, {
              "query": query}))


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
        page = Page.get_by_wiki_name_with_retry(self.request.get('page'))
        if page==None:
        	page = Page.new(self.request.get('page'))
        if self.request.get('content')=="":
            page.remove_from_searcher()
            page.delete()
            return self.redirect("/FrontPage")
        page.content = self.request.get('content')
        page.create_links()
        page.put_with_retry()
        page.queue_update_searcher()
        self.redirect("/"+urllib.quote(page.wiki_name().encode('utf-8')))


class BuildIndexPage(webapp.RequestHandler):
    def get(self):
        document_ids = [document.doc_id
            for document in page_index.list_documents(ids_only=True)]
        page_index.remove(document_ids)
        for key in db.Query(Page, keys_only = True).order("-date").fetch(500):
            taskqueue.add(url='/buildIndex', params={'page': key.name()[1:]})                

    def post(self):
        key = self.request.get('page')
        page = Page.get_by_wiki_name_with_retry(self.request.get('page'))
        page.update_searcher()


application = webapp.WSGIApplication([
    ('/create', CreatePage),
    ('/edit', EditPage),
    ('/buildIndex', BuildIndexPage),
    ('/search', SearchPage),
    ('/.*', ShowPage),
], debug=True)
run_wsgi_app(application)
