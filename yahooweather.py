"""
Weather API Python sample code
Copyright 2019 Oath Inc. Licensed under the terms of the zLib license see https://opensource.org/licenses/Zlib for terms.
$ python --version
Python 3.7.3


### Original code modified by Marko Maljkovic ###
"""
import time
import uuid
import urllib.request
#from urllib.parse import quote, urlencode
import hmac
import hashlib
from base64 import b64encode
import json


def getweather(mesto):
    """
    Basic info
    """
    url = 'https://weather-ydn-yql.media.yahoo.com/forecastrss'
    method = 'GET'
    app_id = 'bUkmof5g'
    consumer_key = 'dj0yJmk9UmM5Rk01ajZBeElPJmQ9WVdrOVlsVnJiVzltTldjbWNHbzlNQS0tJnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTg3'
    consumer_secret = '490f222b7b8905afe2c9c93e3674ad4d092a33ed'
    concat = '&'
    query = {'location': mesto, 'format': 'json', 'u': 'c'}
    oauth = {
        'oauth_consumer_key': consumer_key,
        'oauth_nonce': uuid.uuid4().hex,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_version': '1.0'
    }

    """
	Prepare signature string (merge all params and SORT them)
        """

    merged_params = query.copy()
    merged_params.update(oauth)
    sorted_params = [
        k + '=' + urllib.parse.quote(merged_params[k], safe='') for k in sorted(merged_params.keys())]
#sorted_params = [k + '=' + urllib.quote(merged_params[k], safe='') for k in sorted(merged_params.keys())]
#signature_base_str =  method + concat + urllib.quote(url, safe='') + concat + urllib.quote(concat.join(sorted_params), safe='')
    signature_base_str = method + concat + urllib.parse.quote(
        url, safe='') + concat + urllib.parse.quote(concat.join(sorted_params), safe='')

    """
	Generate signature
	"""
    composite_key = urllib.parse.quote(consumer_secret, safe='') + concat
    oauth_signature = b64encode(hmac.new(composite_key.encode(
        'utf-8'), signature_base_str.encode('utf-8'), hashlib.sha1).digest())

    """
	Prepare Authorization header
	"""
    oauth['oauth_signature'] = oauth_signature.decode('utf-8')
    auth_header = 'OAuth ' + \
        ', '.join(['{}="{}"'.format(k, v) for k, v in oauth.items()])
    #auth_header = 'OAuth ' + ', '.join(['{}="{}"'.format(k,v) for k,v in oauth.iteritems()])

    """
	Send request
	"""
    #url = url + '?' + urllib.urlencode(query)
    url = url + '?' + urllib.parse.urlencode(query)
    #request = urllib.request.Request(url)
    #request.add_header('Authorization', auth_header)
    #request.add_header('X-Yahoo-App-Id', app_id)
    #response = urllib2.urlopen(request).read()
    request = urllib.request.Request(url)
    request.headers['Authorization'] = auth_header
    request.headers['X-Yahoo-App-Id'] = app_id
    response = urllib.request.urlopen(request).read()

    return response


def getCurrentTemp(mesto):
    response = json.loads(getweather(mesto))
    current_temp = response['current_observation']['condition']['temperature']
    return current_temp


def getTomorrowAvg(mesto):
    tomorrow_avg = json.loads(getweather(mesto))
    mintemp = tomorrow_avg['forecasts'][1]['low']
    maxtemp = tomorrow_avg['forecasts'][1]['high']
    return (mintemp+maxtemp)/2
