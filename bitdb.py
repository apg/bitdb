from __future__ import with_statement

import httplib
import urllib
import base64
import os

try:
    import json
except ImportError:
    import simplejson as json

from contextlib import closing

BASE_URL = 'http://sigusr2.net/bitdb/?data='

def iterp(t):
    try:
        return bool((x for x in t))
    except:
        return False

class BitlyDB(object):

    def __init__(self, api_user, api_key, base_url=BASE_URL,
                 cache="~/.bitdb"):
        self._api_user = api_user
        self._api_key = api_key
        self._base_url = base_url
        self._cache = None

        if cache:
            if cache.startswith("~"):
                self._cache = os.path.expanduser(cache)
            else:
                self._cache = cache
        
            self._init_cache()

    def _init_cache(self):
        """Create the cache directory if required"""
        if self._cache:
            exists = os.path.exists(self._cache)
            isdir = os.path.isdir(self._cache)
            if exists and not isdir:
                raise Exception("%s should be a directory, "
                                "found non-directory" % self._cache)
            if not exists:
                os.mkdir(self._cache)

    def _encode(self, data):
        default = {'login': self._api_user,
                   'apiKey': self._api_key}
        default.update(data or {})
        return urllib.urlencode(default)

    def _bit_get(self, resource):
        try:
            with closing(httplib.HTTPConnection('api.bit.ly', 80)) as conn:
                conn.request('GET', resource)
                response = conn.getresponse()
                return json.loads(response.read())
        except httplib.HTTPException:
            return None

    def _db_resource_url(self, data):
        """Creates a url which we'll use to shorten in order to store data
        """
        asjson = json.dumps(data)
        enc = base64.b64encode(asjson).replace('=', '-')
        return BASE_URL + enc
    
    def _db_load_resource_data(self, enc_resource):
        l = len(self._base_url)
        enc_resource = enc_resource[l:].replace('-', '=')
        data = base64.b64decode(enc_resource)
        return json.loads(data)

    def _write_cache(self, key, value):
        enc = json.dumps(value)
        try:
            with closing(open(os.path.join(self._cache, key), 'w')) as f:
                f.write(enc)
        except:
            pass

    def _read_cache(self, key):
        try:
            with closing(open(os.path.join(self._cache, key))) as f:
                unenc = json.loads(f.read())
                return unenc
        except:
            pass

    def shorten(self, url):
        qs = self._encode({'longUrl': url,
                           'format': 'json'})
        resource = '/v3/shorten?%s' % qs
        return self._bit_get(resource)

    def expand(self, hash):
        param = 'shortUrl' if hash.startswith('http://') else 'hash'
        if not isinstance(hash, str) and iterp(hash):
            qs = self._encode({'format': 'json'}) + '&'
            qs += '&'.join('%s=%s' (param, urllib.quote(val)) 
                           for val in hash)
        else:
            qs = self._encode({'format': 'json',
                               param: hash})
        resource = '/v3/expand?%s' % qs
        return self._bit_get(resource)

    def put(self, value):
        """Returns the key in which value was stored, or None if failure
        """
        resource_url = self._db_resource_url(value)
        info = self.shorten(resource_url)
        if info:
            key = info['data']['global_hash']
            if self._cache:
                self._write_cache(key, value)
            return key
        return None

    def get(self, key):
        """Returns the value stored at the key, or None if failure
        """
        cached = self._read_cache(key)
        if cached:
            return cached
        else:
            info = self.expand(key)
            if info:
                return self._db_load_resource_data(info['data']\
                                                       ['expand'][0]\
                                                       ['long_url'])

    def getmulti(self, keys):
        cached = {}
        need = []
        data = None

        for key in keys:
            r = self._read_cache(key)
            if r:
                cached[key] = r
            else:
                need.append(key)

        if len(need):
            info = self.expand(set(need))
            if info:
                dlrd = self._db_load_resource_data
                data = dict((i['hash'], dlrd(i['long_url']))
                        for i in info['data']['expand'])
        cached.update(data or {})
        return cached

if __name__ == '__main__':
    import sys

    if len(sys.argv) == 4:
        db = BitlyDB(sys.argv[1], sys.argv[2])
        print db.get(sys.argv[3])
    else:
        print 'usage: bitdb.py username apikey key'
