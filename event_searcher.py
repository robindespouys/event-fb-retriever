import multiprocessing
import os
import errno
import logging
import location
import json
import urllib
import requests
import re
import fblogin as fb
import getpass
import base64
import time
import datetime
import math
import random

# import your_firestore as y_f

from bs4 import BeautifulSoup

MAX_MORE_RESULT_ITERATION = 4

E_OK = 0
E_ERR = 1

FB_URL = 'https://www.facebook.com/'
API_URL = 'https://www.facebook.com/api/graphql/'
MAIL_REGEX = re.compile(r'[\w\_\.\+\-]+@[\w\-]+\.[\w\-\.]+')
URL_REGEX = re.compile(
    r'[-a-zA-Z0-9@:%_\+.~#?&//=]{2,256}\.[a-z]{2,4}\b(\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?')

CITY_CODES = {
    'paris': '110774245616525',
    'london': '106078429431815'
}

TIMEOUT = 25
HEADERS = {
    'accept-language': 'en',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36',
}

FILTERS_PREFIX = '{"rp_events_date":"{\\"name\\":\\"filter_events_date\\",\\"args\\":\\"'
FILTERS_RADICAL = '\\"}","rp_events_location":"{\\"name\\":\\"filter_events_location\\",\\"args\\":\\"'
FILTERS_SUFFIX = '\\"}"}'

events_found = []


def fun_random(factor):
    # I am just fucking around in order to simulate some randomness. Shame on me
    x = 0
    for i in range(10):
        x += random.randint(1, 10)
    a = random.randint(50, 100)
    b = random.randint(10, 30) / 11
    y = (x / (10 + x/100) - a / 50) * b * factor
    print('sleep for  ', y, ' seconds')
    time.sleep(y)


def build_url_request(key_word='lgbt', city_code='paris', next_days=14):
    fromDate = datetime.date.today()
    toDate = fromDate + datetime.timedelta(days=next_days)
    fromDate = str(fromDate)
    toDate = str(toDate)
    city_code = '110774245616525'
    try :    
        city_code = CITY_CODES[city_code]
    except KeyError:
        print('city not referenced, you should fill-up the CITY_CODES with its key-value')
    filters_ = FILTERS_PREFIX + fromDate + '~' + toDate + \
        FILTERS_RADICAL + city_code + FILTERS_SUFFIX
    print('FILTERS BEFORE BASE64 ENCODING : ', filters_)
    b64Filters = base64.b64encode(filters_.encode())
    strb64Filters = b64Filters.decode()
    url_request_ = 'https://m.facebook.com/search/events/?q=' + \
        key_word+'&epa=FILTERS&filters='+strb64Filters
    return url_request_


def retrieve_query_events(url_request_, session, nb_iteration):
    if nb_iteration >= MAX_MORE_RESULT_ITERATION:
        print('!! maximum more result reached !!')
        return
    resp = session.get(url_request_, timeout=TIMEOUT)

    pattern = re.compile(r'\/?events\/([0-9]+)\?')
    events = re.findall(pattern, resp.text)
    for match in events:
        events_found.append(match)
        print('event found ID is : ', match)

    with open('outputs/event-query-result-raw.html', 'w', encoding='utf8') as f:
        print('writing the result to a file for debugging purpose... ')
        f.write(resp.text)

    pattern = re.compile(r'see_more_pager\",href:\"([^"]+)\"')
    see_more_pager = re.findall(pattern, resp.text)
    if see_more_pager.count == 0:
        print('no more resut')
        return
    for next_page in see_more_pager:
        print('we found a new page of result... : ')
        time.sleep(6.35)
        nb_iteration = nb_iteration + 1
        retrieve_query_events(url_request_, session, nb_iteration)


def dict_values(d, keys):
    return [deep_get(d, k) for k in keys]


def event_id(url):
    match = re.search(r'events\/(\d+)\/?', url)
    return match.group(1) if match else url


def deep_get(d, path, default=None):
    keys = path.split('.')
    acum = {} if d is None else d
    for k in keys:
        acum = acum.get(k, default)
        if acum is None:
            break
    return acum


def extract_hosts(data):
    hosts = deep_get(data, 'data.event.hosts.edges')
    keys = ['id', 'url', 'name', 'category', 'profilePicture.uri']
    result = []
    for x in hosts:
        host = x.get('node', None)
        info = dict_values(host, keys)
        result.append(info)
    return result


def extract_place(data):
    place = deep_get(data, 'data.event.place')
    keys = ['id', 'url', 'name', 'category', 'profilePicture.uri']
    info = dict_values(place, keys)
    return info


def dict_by_keys(data, keys):
    return {k: v for k, v in zip(keys, data)}


def scrap_event(url, session=requests.Session()):
    session.headers.update(HEADERS)  # not sure if really needed...
    _id = event_id(url)

    print('id IS : ', _id)

    payload = {
        'variables': '{{"eventID": {}}}'.format(_id),
        'doc_id': 1634531006589990
        # mandatory code that correspond to the type of document in Facebook Graph API. this might change in the future
        # in order to retrieve it you need to use the developper console in your browser and look for graph api calls headers
    }

    resp = session.post(API_URL, data=payload, timeout=TIMEOUT)
    if resp.status_code != 200:
        return None

    data = resp.json()
    hosts = extract_hosts(data)
    place = extract_place(data)

    # extract from html: title, date, start, end, address, phone
    # title -> #seo_h1_tag
    # date  -> #event_time_info ._2ycp
    event_url = '{}events/{}'.format(FB_URL, _id)
    resp = session.get(event_url, timeout=TIMEOUT)
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')

    # Title
    ttag = soup.find(id='seo_h1_tag')
    title = ttag.get_text().strip() if ttag else ''

    dtag = soup.find('code')
    text = str(dtag)
    text = re.sub(r'(?:<!--)|(?:-->)', '', text)
    summary_soup = BeautifulSoup(text, 'html.parser')

    # Date
    dtag = summary_soup.select_one('#event_time_info ._2ycp')
    date = dtag['content'] if dtag else None

    # Address
    atag = summary_soup.select_one('li._3xd0 div._5xhp')
    addr = atag.get_text().strip() if atag else None

    # Venue
    vtag = summary_soup.select('li._3xd0 div._4bl9 > div > *')
    vtag = [t for t in vtag if not 'ptm' in t.get('class', '')]
    desc = ' '.join([t.get_text() for t in vtag])

    # Email
    match = MAIL_REGEX.search(desc)
    email = match.group() if match else None
    desc = MAIL_REGEX.sub('', desc)

    # Website
    match = URL_REGEX.search(desc)
    page = match.group() if match else None
    desc = URL_REGEX.sub('', desc)

    # Phone
    desc = re.sub(r'[^\+\d]', '', desc)
    match = re.search(r'\+?\d{4,}', desc)
    phone = match.group() if match else None

    # Extract tags
    scripts = soup('script')
    keyword_regex = re.compile(r'\{\s*name\:\s*\"([^\"]*)\"\s*\,\s*token')
    for script in scripts:
        text = script.get_text()
        match = keyword_regex.findall(text)
        if match:
            break
    tags = match

    # Request details
    payload['doc_id'] = 1640160956043533
    # mandatory code that correspond to the type of document in Facebook Graph API. this might change in the future
    # in order to retrieve it you need to use the developper console in your browser and look for graph api calls headers
    details = None

    resp = session.post(API_URL, data=payload, timeout=TIMEOUT)
    if resp.status_code == 200:
        details = deep_get(resp.json(), 'data.event.details.text')

    # Map Url
    map_url = None
    CC = None
    map_anchor = summary_soup.find("a", class_='_42ft')
    if map_anchor:
        map_url = map_anchor["href"]
        map_url = urllib.parse.unquote(map_url)
        match = re.search(r'u\=(.+)', map_url)
        if match:
            map_url = match.group(1)
            CC = location.country_location(map_url)

    # Extract video
    media = None
    match = re.search(r'"hd_src":"([^"]*)"', html)
    media = match.group(1).replace('\\', '') if match else media

    # Extract img
    if media is None:
        images = soup.select("#event_header_primary img")
        if images:
            media = images[0]["src"]

    # Privacy
    privacy = 'Private'
    spans = soup.select("span[data-testid='event_permalink_privacy']")
    if spans:
        privacy = spans[0].get_text()

    # I should probably change this to use only dict...
    keys = ['id', 'url', 'name', 'category', 'profilePicture']
    hosts = [dict_by_keys(d, keys) for d in hosts]

    position = ''
    if map_url:
        patternPosition = re.compile(r'Epos\.([^_]+)_([^_]+)_')
    match = re.search(patternPosition, map_url)
    if match:
        position = 'latitude : ' + \
            match.group(1) + ', longitude : ' + match.group(2)
        # documentEvent['location'] = y_f.firestore.GeoPoint(
        #     float(match.group(1)), float(match.group(2)))
    else:
        print(
            'lets try an other pattern where they encode location in base64... lets decode')
        match = re.search(r'mylocation\/e-([^?]+)\?', map_url)
        if match:
            b64decodedLocation = base64.b64decode(match.group(1)).decode()
            latitude = re.search(
                r'\"latitude\"\:([^,|^}]+)', b64decodedLocation).group(1)
            longitude = re.search(
                r'\"longitude\"\:([^,|^}]+)', b64decodedLocation).group(1)
            position = 'latitude : ' + latitude + ', longitude : ' + longitude

    keys = ['id', 'title', 'date', 'address', 'position', 'email', 'page', 'phone',
            'hosts', 'details', 'tags', 'media', 'privacy', 'map_url', "CC"]

    data = dict_by_keys([_id, title,  date, addr, position, email, page, phone,
                         hosts, details, tags, media, privacy, map_url, CC], keys)

    return data

# def store_event_to_firebase(data):
#     documentEvent = {}
#     if data['map_url']:
#         patternPosition = re.compile(r'Epos\.([^_]+)_([^_]+)_')
#         match = re.search(patternPosition, data['map_url'])
#         if match:
#             documentEvent['location'] = y_f.firestore.GeoPoint(
#                 float(match.group(1)), float(match.group(2)))
#         else:
#             print(
#                 'lets try an other pattern where they encode location in base64... lets decode')
#             match = re.search(r'mylocation\/e-([^?]+)\?', data['map_url'])
#             if match:
#                 b64decodedLocation = base64.b64decode(match.group(1)).decode()
#                 latitude = re.search(
#                     r'\"latitude\"\:([^,|^}]+)', b64decodedLocation).group(1)
#                 longitude = re.search(
#                     r'\"longitude\"\:([^,|^}]+)', b64decodedLocation).group(1)
#                 documentEvent['location'] = y_f.firestore.GeoPoint(
#                     float(latitude), float(longitude))
#     dateStart = data['date']
#     matchDateStart = re.search(r'([^to]+)to', data['date'])
#     if matchDateStart:
#         dateStart = matchDateStart.group(1)

#     dateStart = dateStart.replace(" ", "").rstrip()[:-6]
#     dateStart = datetime.datetime.strptime(dateStart, '%Y-%m-%dT%H:%M:%S')
#     documentEvent['dateStart'] = dateStart
#     matchDateEnd = re.search(r'to([^to]+)', data['date'])

#     if matchDateEnd:
#         dateEnd = re.search(r'to([^to]+)', data['date']).group(1)
#         dateEnd = dateEnd.replace(" ", "").rstrip()[:-6]
#         dateEnd = datetime.datetime.strptime(dateEnd, '%Y-%m-%dT%H:%M:%S')
#         documentEvent['dateEnd'] = dateEnd

#     documentEvent['description'] = data['details'].encode(
#         'utf-16', 'surrogatepass').decode('utf-16')
#     documentEvent['name'] = data['title'].encode(
#         'utf-16', 'surrogatepass').decode('utf-16')
#     documentEvent['pic'] = data['media']

#     try:
#         y_f.your_collection_ref.document(data['id']).set(documentEvent)
#     except Exception as e:
#         print('Exception occured : ', e)


def retrieve_events(session=requests.Session()):
    for event in events_found:
        data = scrap_event(
            'https://www.facebook.com/events/{}/'.format(event), session)
        if data:
            with open('outputs/events.json', 'a', encoding='utf8') as f:
                json.dump(data, f, indent=4)
                f.write(',\n')
            # store_event_to_firebase(data)
        fun_random(2)


def extract_place_id(url, session=requests.Session()):
    session.headers.update(HEADERS)
    resp = session.get(url, timeout=TIMEOUT)
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.find('head')
    match = re.search(r'fb:\/\/page\/(\d+)', str(head))
    if match:
        return match.group(1)
    else:
        match = re.search(r'facebook\.com\/([^\/]+)\/', url)
        return match.group(1) if match else None


def login_flow(login, passwd):
    auth = login, \
        passwd
    fb_s = fb.login(*auth)
    if fb_s is None:
        print('Login fail!')
        exit(E_ERR)
    print('Success!')
    return fb_s


def scrape_host(_id, session=requests.Session()):

    session.headers.update(HEADERS)

    url = 'https://www.facebook.com/{}/'.format(_id)
    result = {'id': _id, 'url': url, 'events': []}
    variables = {'pageID': _id}
    payload = {'variables': json.dumps(variables), 'doc_id': 2784491161596946}

    # 'doc_id' : 2784491161596946 //upcoming events
    # 'doc_id' : 3270179606343275 //recuring events
    # 'doc_id': 1934177766626784

    next_page = True
    while next_page:
        resp = session.post(API_URL, data=payload, timeout=TIMEOUT)
        if resp.status_code != 200:
            break
        data = resp.json()
        with open('outputs/raw-event.json', 'a', encoding='utf8') as f:
            json.dump(data, f, indent=4)
            f.write(',\n')

        events = deep_get(data, 'data.page.upcoming_events')
        if events is None:
            break

        edges = events['edges']

        for e in edges:
            result['events'].append(deep_get(e, 'node.id'))

        page_info = events['page_info']
        end_cursor = page_info['end_cursor']
        print('page info : ', page_info)
        next_page = False
        # next_page = page_info.get('has_next_page', False)

        variables['count'] = 9
        variables['cursor'] = end_cursor

        payload['variables'] = json.dumps(variables)
        payload['doc_id'] = 2784491161596946

    print('events for this group: ', result['events'])
    return result


class EventSpider:

    def __init__(self, pending_host=[],
                 pending_events=[], fb_s=requests.Session()):

        self.pending_hosts = set(pending_host)
        self.pending_events = set(pending_events)

        self.fb_s = fb_s
        self.fb_s.headers.update(HEADERS)

    def try_scrape(self, limit=50):

        hosts = tuple(self.pending_hosts)
        count = len(hosts)
        for host in hosts:
            print('Extracting  host:', host)
            data = scrape_host(host, self.fb_s)
            events = []

            if data:
                events = data.get('events', [])

            self.pending_events |= set(events)

        fun_random(1)
        events = tuple(self.pending_events)
        print('EVENTS to scrape are : ', events)

        for event in events:
            data = scrap_event(
                'https://www.facebook.com/events/{}/'.format(event), self.fb_s)
            if data:
                with open('outputs/events.json', 'a', encoding='utf8') as f:
                    json.dump(data, f, indent=4)
                    f.write(',\n')
                # store_event_to_firebase(data)
            fun_random(2)


class GroupEventScrapper(multiprocessing.Process):
    def __init__(self, login, passwd):
        super(GroupEventScrapper, self).__init__()
        print('Initializing Event Searcher : ', self.__str__)
        self.login = login
        self.passwd = passwd

    def run(self):
        print('Activating logger with INFO level...')
        try:
            os.makedirs(os.path.dirname('./outputs/'))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
        multiprocessing.log_to_stderr()
        logger = multiprocessing.get_logger()

        groups = []
        with open("./inputs/list-of-groups.csv") as f:
            groups = f.readlines()
        fb_s = login_flow(self.login, self.passwd)
        for url in groups:
            print('Trying to scrap events from : ', url)
            _id = extract_place_id(url, fb_s)
            spider = EventSpider(pending_host=(_id,), fb_s=fb_s)
            spider.try_scrape()
        print('Terminating process....')


class EventSearcher(multiprocessing.Process):

    def __init__(self, login, passwd, keyword, location, next_days):
        super(EventSearcher, self).__init__()
        print('Initializing Event Searcher : ', self.__str__)
        self.login = login
        self.passwd = passwd
        self.keyword = keyword
        self.location = location
        self.next_days = next_days

    def run(self):
        print('Activating logger with INFO level...')
        try:
            os.makedirs(os.path.dirname('./outputs/'))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
        multiprocessing.log_to_stderr()
        logger = multiprocessing.get_logger()
        # logger.setLevel(logging.INFO)
        fb_s = login_flow(self.login, self.passwd)
        url_req_ = build_url_request(
            self.keyword, self.location, int(self.next_days))
        print('URL TO REQUEST : ', url_req_)
        retrieve_query_events(url_req_, fb_s, 0)
        retrieve_events(fb_s)
        print('Terminating process....')
