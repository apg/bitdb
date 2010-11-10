import httplib
import urllib
import json
import base64

from contextlib import closing

BASE_URL = 'http://sigusr2.net/bitdb/?data='

class BitlyDB(object):

    def __init__(self, api_user, api_key, base_url=BASE_URL):
        self._api_user = api_user
        self._api_key = api_key
        self._base_url = base_url

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

    def shorten(self, url):
        qs = self._encode({'longUrl': url,
                           'format': 'json'})
        resource = '/v3/shorten?%s' % qs
        return self._bit_get(resource)

    def expand(self, hash):
        param = 'shortUrl' if hash.startswith('http://') else 'hash'
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
            return info['data']['global_hash']
        return None

    def get(self, key):
        """Returns the value stored at the key, or None if failure
        """
        info = self.expand(key)
        if info:
            return self._db_load_resource_data(info['data']['expand'][0]['long_url'])
        return None

if __name__ == '__main__':
    import sys

    if len(sys.argv) == 3:
        db = BitlyDB(sys.argv[1], sys.argv[2])
        
        key = db.put({'Andrew Gwozdziewycz': {'twitter': 'apgwoz'}})
        print db.get(key)
    else:
        print 'usage: bitdb.py username apikey'
