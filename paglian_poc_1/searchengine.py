# -*- coding: utf-8 -*-
import urllib3
from BeautifulSoup import *
from urlparse import urljoin
from pysqlite2 import dbapi2 as sqlite

# Create a list of words to ignore
ignorewords = set([])


class Crawler:
    """Crawler class provides a web crawler a.k.a web spider

    The implementation is took from the book 'Programming Collective
    Intelegence'
    """

    def __init__(self, dbname='searchindex.db'):
        self.con = sqlite.connect(dbname)
        self.createindextables()

    def __del__(self):
        self.con.close()

    def dbcommit(self):
        self.con.commit()

    # Auxilliary function for getting an entry id and adding
    # it if it's not present
    def getentryid(self, table, field, value, createnew=True):
        cur = self.con.execute("select rowid from %s where %s='%s'"
            % (table, field, value))
        res = cur.fetchone()
        if res is None:
            cur = self.con.execute("insert into %s (%s) values ('%s')"
            % (table, field, value))
            return cur.lastrowid
        else:
            return res[0]

    #
    def geturlid(self, url):
        return self.getentryid('urllist', 'url', url)

    #
    def geturlids(self):
        return [row[0] for row in
                self.con.execute("select rowid from urllist")]

    #
    def getwordid(self, word):
        return self.getentryid('wordlist', 'word', word)

    #
    def getwordids(self):
        return [row[0] for row in
                self.con.execute("select rowid from wordlist")]

    # Index an individual page
    def addtoindex(self, url, soup):
        if self.isindexed(url):
            return
        print(('Indexing ' + url))

        # Get the individual words
        text = self.gettextonly(soup)
        words = self.separatewords(text)

        # Get the URL id
        urlid = self.geturlid(url)

        # Link each word to this url
        for i in range(len(words)):
            word = words[i]
            if word in ignorewords:
                continue
            wordid = self.getwordid(word)
            self.con.execute("insert into wordlocation(urlid,wordid,location)"
                " values (%d,%d,%d)" % (urlid, wordid, i))

    # Extract the text from an HTML page (no tags)
    def gettextonly(self, soup):
        v = soup.string
        if v is None:
            c = soup.contents
            resulttext = ''
            for t in c:
                subtext = self.gettextonly(t)
                resulttext += subtext + '\n'
            return resulttext
        else:
            return v.strip()

    # Separate the words by any non-whitespace character
    def separatewords(self, text):
        splitter = re.compile('\\W*')
        return [s.lower() for s in splitter.split(text) if s != '']

    # Return true if this url is already indexed
    def isindexed(self, url):
        u = self.con.execute("select rowid from urllist where url='%s'"
            % url).fetchone()
        if u is not None:
            # Check if it has actually been crawled
            v = self.con.execute('select * from wordlocation where urlid=%d'
                % u[0]).fetchone()
            if v is not None:
                return True
        return False

    # Add a link between two pages
    def addlinkref(self, urlFrom, urlTo, linkText):
        pass

    # Starting with a list of pages, do a breadth
    # first search to the given depth, indexing pages
    # as we go
    def crawl(self, pages, depth=2):
        for i in range(depth):
            newpages = set()

            for page in pages:
                http = urllib3.PoolManager()
                r = http.request('GET', page)
                if r.status != 200:
                    continue

                soup = BeautifulSoup(r.data)
                self.addtoindex(page, soup)

                links = soup('a')
                for link in links:
                    if ('href' in dict(link.attrs)):
                        url = urljoin(page, link['href'])
                        if url.find("'") != -1:
                            continue
                        url = url.split('#')[0]
                        if url[0:4] == 'http' and not self.isindexed(url):
                            newpages.add(url)
                        linkText = self.gettextonly(link)
                        self.addlinkref(page, url, linkText)

                    self.dbcommit()

                pages = newpages

    # Create the database tables
    def createindextables(self):
        self.con.execute('create table if not exists urllist(url)')
        self.con.execute('create table if not exists wordlist(word)')
        self.con.execute('create table if not exists wordlocation(urlid,wordid,location)')
        self.con.execute('create table if not exists link(fromid integer,toid integer)')
        self.con.execute('create table if not exists linkwords(wordid,linkid)')
        self.con.execute('create index if not exists wordidx on wordlist(word)')
        self.con.execute('create index if not exists urlidx on urllist(url)')
        self.con.execute('create index if not exists wordurlidx on wordlocation(wordid)')
        self.con.execute('create index if not exists urltoidx on link(toid)')
        self.con.execute('create index if not exists urlfromidx on link(fromid)')
        self.dbcommit()


class Searcher:
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()

    def getmatchrows(self, q):
        # Strings to build the query
        fieldlist = 'w0.urlid'
        tablelist = ''
        clauselist = ''
        wordids = []

        # Split the words by spaces
        words = q.split(' ')
        tablenumber = 0

        for word in words:
            # Get the word ID
            wordrow = self.con.execute(
                "select rowid from wordlist where word='%s'" % word).fetchone()
            if wordrow is not None:
                wordid = wordrow[0]
                wordids.append(wordid)
                if tablenumber > 0:
                    tablelist += ','
                    clauselist += ' and '
                    clauselist += 'w%d.urlid=w%d.urlid and ' % (
                        tablenumber - 1, tablenumber)
                fieldlist += ',w%d.location' % tablenumber
                tablelist += 'wordlocation w%d' % tablenumber
                clauselist += 'w%d.wordid=%d' % (tablenumber, wordid)
                tablenumber += 1

        if tablenumber > 0:
            # Create the query from the separate parts
            fullquery = 'select %s from %s where %s' % (fieldlist, tablelist,
                clauselist)
            print(fullquery)
            cur = self.con.execute(fullquery)
            rows = [row for row in cur]

            return rows, wordids
        else:
            return None, None

