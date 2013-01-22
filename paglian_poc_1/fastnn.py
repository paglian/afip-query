# -*- coding: utf-8 -*-
from math import tanh
from pysqlite2 import dbapi2 as sqlite


def dtanh(y):
    return 1.0 - y * y


class FastNeuralNet:
    """A much faster implementation of the NeuralNet class

    This implementation tries to minimize DB access keeping the data in RAM
    """

    def __init__(self, dbname='nn.db'):
        self.con = sqlite.connect(dbname)
        self.maketables()
        self.load_strength_matrixes()
        self.dirty = False

    def __del__(self):
        self.updatedatabase()
        self.con.close()

    def maketables(self):
        self.con.execute('create table if not exists hiddennode(create_key)')
        self.con.execute('create table if not exists wordhidden(fromid,toid,strength)')
        self.con.execute('create table if not exists hiddenurl(fromid,toid,strength)')
        self.con.execute('create index if not exists hiddennodeidx on hiddennode(create_key)')
        self.con.execute('create index if not exists wordhiddenfromididx on wordhidden(fromid)')
        self.con.execute('create index if not exists wordhiddentoididx on wordhidden(toid)')
        self.con.execute('create index if not exists wordhiddenstrengthidx on wordhidden(strength)')
        self.con.execute('create index if not exists hiddenurlfromididx on hiddenurl(fromid)')
        self.con.execute('create index if not exists hiddenurltoididx on hiddenurl(toid)')
        self.con.execute('create index if not exists hiddenurlstrengthidx on hiddenurl(strength)')
        self.con.commit()

    def load_strength_matrixes(self):
        print "Loading strengths matrix from database..."
        self.strength = {0: {}, 1: {}}

        res = self.con.execute('select * from wordhidden')
        for row in res:
            self.setstrength(row[0], row[1], 0, row[2])

        res = self.con.execute('select * from hiddenurl')
        for row in res:
            self.setstrength(row[0], row[1], 1, row[2])

    def getstrength(self, fromid, toid, layer):
        try:
            return self.strength[layer][fromid][toid]
        except KeyError:
            if layer == 0:
                return -0.2
            if layer == 1:
                return 0

        # ORIGINAL IMPL: VERY SLOW!
        #if layer == 0:
            #table = 'wordhidden'
        #else:
            #table = 'hiddenurl'
        #res = self.con.execute(
            #'select strength from %s where fromid=%d and toid=%d'
            #% (table, fromid, toid)).fetchone()
        #if res is None:
            #if layer == 0:
                #return -0.2  # TUNE !!! Old: -0.2
            #if layer == 1:
                #return 0
        #return res[0]

    def setstrength(self, fromid, toid, layer, strength):
        if fromid not in self.strength[layer]:
            self.strength[layer][fromid] = {}

        self.strength[layer][fromid][toid] = strength

        self.dirty = True

        # ORIGINAL IMPL: VERY SLOW!
        #if layer == 0:
            #table = 'wordhidden'
        #else:
            #table = 'hiddenurl'
        ##res = self.con.execute(
            #'select rowid from %s where fromid=%d and toid=%d'
            #% (table, fromid, toid)).fetchone()
        #if res is None:
            #self.con.execute(
                #'insert into %s (fromid,toid,strength) values (%d,%d,%f)'
                #% (table, fromid, toid, strength))
        #else:
            #rowid = res[0]
            #self.con.execute(
                #'update %s set strength=%f where rowid=%d'
                #% (table, strength, rowid))

    def generatehiddennode(self, wordids, urls):
        # TUNE !!! commented out:
        #if len(wordids) > 3:
        #    return None

        # Check if we already created a node for this set of words
        createkey = '_'.join(sorted([str(wi) for wi in wordids]))
        res = self.con.execute(
            "select rowid from hiddennode where create_key='%s'"
            % createkey).fetchone()

        # If not, create it
        if res is None:
            cur = self.con.execute(
                "insert into hiddennode (create_key) values ('%s')"
                % createkey)
            hiddenid = cur.lastrowid

            # Put in some default weights
            for wordid in wordids:
                self.setstrength(wordid, hiddenid, 0, 1.0 / len(wordids))
            for urlid in urls:
                self.setstrength(hiddenid, urlid, 1, 0.1)
            self.con.commit()

    def getallhiddenids(self, wordids, urlids):
        l1 = {}

        for wordid in wordids:
            if wordid not in self.strength[0]:
                continue
            for h in self.strength[0][wordid].iterkeys():
                l1[h] = 1

        for h, urls in self.strength[1].iteritems():
            for u in urls.keys():
                if u in urlids:
                    l1[h] = 1
                    break

        return list(l1.keys())

        # ORIGINAL IMPL: VERY SLOW!
        #l1 = {}
        #for wordid in wordids:
            #cur = self.con.execute(
                #'select toid from wordhidden where fromid=%d' % wordid)
            #for row in cur:
                    #l1[row[0]] = 1
        #for urlid in urlids:
            #cur = self.con.execute(
                #'select fromid from hiddenurl where toid=%d' % urlid)
            #for row in cur:
                #l1[row[0]] = 1
        #return list(l1.keys())

    def setupnetwork(self, wordids, urlids):
        # value lists
        self.wordids = wordids
        self.hiddenids = self.getallhiddenids(wordids, urlids)
        self.urlids = urlids

        # node outputs
        self.ai = [1.0] * len(self.wordids)
        self.ah = [1.0] * len(self.hiddenids)
        self.ao = [1.0] * len(self.urlids)

        # create weights matrix
        self.wi = [[self.getstrength(wordid, hiddenid, 0) for hiddenid in
            self.hiddenids] for wordid in self.wordids]
        self.wo = [[self.getstrength(hiddenid, urlid, 1) for urlid in
            self.urlids] for hiddenid in self.hiddenids]

    def feedforward(self):
        # the only inputs are the query words
        for i in range(len(self.wordids)):
            self.ai[i] = 1.0

        # hidden activations
        for j in range(len(self.hiddenids)):
            s = 0.0
            for i in range(len(self.wordids)):
                #print 'ai[%d]=%f wi[%d][%d]=%f'
                #% (i,self.ai[i],i,j,self.wi[i][j])
                s = s + self.ai[i] * self.wi[i][j]
            self.ah[j] = tanh(s)

        # output activations
        for k in range(len(self.urlids)):
            s = 0.0
            for j in range(len(self.hiddenids)):
                s = s + self.ah[j] * self.wo[j][k]
            self.ao[k] = tanh(s)

        return self.ao[:]

    def getresult(self, wordids, urlids):
        self.setupnetwork(wordids, urlids)
        return self.feedforward()

    def backPropagate(self, targets, N=0.5):
        # calculate errors for output
        output_deltas = [0.0] * len(self.urlids)
        for k in range(len(self.urlids)):
            error = targets[k] - self.ao[k]
            output_deltas[k] = dtanh(self.ao[k]) * error

        # calculate errors for hidden layer
        hidden_deltas = [0.0] * len(self.hiddenids)
        for j in range(len(self.hiddenids)):
            error = 0.0
            for k in range(len(self.urlids)):
                error = error + output_deltas[k] * self.wo[j][k]
            hidden_deltas[j] = dtanh(self.ah[j]) * error

        # update output weights
        for j in range(len(self.hiddenids)):
            for k in range(len(self.urlids)):
                change = output_deltas[k] * self.ah[j]
                w = self.wo[j][k] + N * change
                self.wo[j][k] = w
                self.setstrength(self.hiddenids[j], self.urlids[k], 1, w)

        # update input weights
        for i in range(len(self.wordids)):
            for j in range(len(self.hiddenids)):
                change = hidden_deltas[j] * self.ai[i]
                w = self.wi[i][j] + N * change
                self.wi[i][j] = w
                self.setstrength(self.wordids[i], self.hiddenids[j], 0, w)

    def trainquery(self, wordids, urlids, selectedurl):
        # generate a hidden node if necessary
        self.generatehiddennode(wordids, urlids)
        self.setupnetwork(wordids, urlids)
        self.feedforward()
        targets = [0.0] * len(urlids)
        targets[urlids.index(selectedurl)] = 1.0
        self.backPropagate(targets)

    def updatedatabase(self):
        if not self.dirty:
            return

        print "Saving strengths into database. Please wait..."

        for layer in [0, 1]:
            for fromid, toids in self.strength[layer].iteritems():
                for toid, strength in toids.iteritems():
                    #print fromid, toid
                    self.set_strength_db(fromid, toid, layer, strength)

        self.con.commit()
        self.dirty = False

        # ORIGINAL IMPL: VERY SLOW!
        # set them to database values
        #for i in range(len(self.wordids)):
            #for j in range(len(self.hiddenids)):
                #self.setstrength(self.wordids[i], self.hiddenids[j], 0,
                    #self.wi[i][j])
        #for j in range(len(self.hiddenids)):
            #for k in range(len(self.urlids)):
                #self.setstrength(self.hiddenids[j], self.urlids[k], 1,
                    #self.wo[j][k])
        #self.con.commit()

    def set_strength_db(self, fromid, toid, layer, strength):
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'

        res = self.con.execute(
            'select rowid from %s where fromid=%d and toid=%d'
            % (table, fromid, toid)).fetchone()

        if res is None:
            self.con.execute(
                'insert into %s (fromid,toid,strength) values (%d,%d,%f)'
                % (table, fromid, toid, strength))
        else:
            rowid = res[0]
            self.con.execute(
                'update %s set strength=%f where rowid=%d'
                % (table, strength, rowid))


