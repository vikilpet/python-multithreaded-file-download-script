import pyperclip
import requests
from time import strftime
import os, errno
import re
from time import sleep
from multiprocessing import dummy
from itertools import repeat
import ctypes

MessageBox = ctypes.windll.user32.MessageBoxW

try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    from settings import *
except ImportError as e:
    DOWNLOAD_FOLDER = r'd:\YOUR FOLDER'

    # Do not use more than one group in regexp because
    # re.findall make tuples from them or
    # use non-matching groups with (?:)
    MY_COOKIES = {
        'www.example.com': {
            'regexp': r'"([^"]+\.(?:jpg|jpeg|png|gif))"',
            'cookies': {
                'parameter1': 'value1',
                'parameter2': 'value2'
            }
        }
    }

DEFAULT_RE = r'"([^"]+\.(?:jpg|jpeg|png|gif))"'
THREADS_NUMBER = 8


def get_domain(url):
    n = url.find('//')
    d = url[n + 2:url.find('/', n + 2)]
    return d


class GetFiles:
    ''' All methods returns status (boolean) and data (error description
		in case of error) '''

    def __init__(self, url, folder, THREADS_NUMBER):
        self.msg_title = 'Get Files'
        self.page = ''
        self.THREADS_NUMBER = THREADS_NUMBER
        self.url = url
        self.domain = get_domain(self.url)
        self.count = 0
        if url.find('https') == -1:
            self.schema = 'https://'
        else:
            self.schema = 'http://'
        self.regexp, self.cookies = self.get_cookies_re()
        self.folder = folder

    def get_urls(self):
        urls = re.findall(self.regexp, self.page)
        d = self.domain
        s = self.schema
        # add domain:
        urls = [f'{s}{d}{u}' if u.find('/') == 0 else u for u in urls]
        # remove duplicates:
        urls = list(set(urls))
        return urls

    def get_cookies_re(self):
        d = MY_COOKIES.get(self.domain)
        if d == None:
            r = DEFAULT_RE
            c = {}
        else:
            r = d.get('regexp')
            c = d.get('cookies')
        return r, c

    def make_path(self):
        # if url ends just with a slash:
        if self.url.rfind('/') + 1 == len(self.url):
            u = self.url[:-1]
        else:
            u = self.url
        u = u[u.rfind('/') + 1:]
        # remove '#' anchor:
        if u.find('#') > 0:
            u = u[:u.find('#')]
        u = u.replace('.html', '').replace('.htm', '').replace('.php', '')
        path = self.folder + '\\' + u + '_' + strftime('%Y-%m-%d_%H-%M-%S')
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                return False, f'folder: {path} makedirs error: {e.errno}'
        self.path = path
        return True, None

    def get_page(self):
        r = requests.get(self.url, cookies=self.cookies)
        if r.status_code == 200:
            return True, r.content
        else:
            return False, f'status_code: {r.status_code}'

    def get_number(self):
        #print(f'Get files: {self.url} -> {self.path}')
        status, data = self.get_page()
        if status:
            self.page = str(data)
        else:
            self.page = 'None'
            return False, data
        self.urls = self.get_urls()
        self.count = len(self.urls)
        return True, None

    def get_file(self, furl):
        ''' Inside thread you cannot return values or print to stdout '''

        filename = '{}\\{}'.format(self.path, furl[furl.rfind('/') + 1:])
        i = 0
        # make three attempts with pause:
        while i < 3:
            sleep(i * 5)
            i += 1
            r = requests.get(furl, cookies=self.cookies)
            if r.status_code == 200 or r.status_code // 100 == 4: break
        if r.status_code == 200:
            try:
                # check if we downloaded bigger version of file:
                if os.path.isfile(filename):
                    if os.stat(filename).st_size < len(r.content):
                        with open(filename, 'bw') as f:
                            f.write(r.content)
                else:
                    with open(filename, 'bw') as f:
                        f.write(r.content)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    # we already checked existance of file and
                    # we are in multithread pool so no console output:
                    pass
                    # raise
                    # return f'error file write: {e.errno}'
        else:
            # we can't see output in multithreading so use MsgBox:
            # MessageBox(None, f'Cannot download file:\r\n{furl}\r\n' +
            # f'Status code: {r.status_code}', self.msg_title, 64 + 4096)
            pass

    def download_files(self):
        with dummy.Pool(self.THREADS_NUMBER) as pool:
            pool.map(self.get_file, self.urls)


def main():
    url = str(pyperclip.paste())
    # url = 'https://www.instagram.com/thisset/'
    if url.find('http') != 0:
        input(f'No URL found in clipboard: {url[:200]}\n\n' +
              'Press Enter to exit')
        return
    gi = GetFiles(
        url=url, folder=DOWNLOAD_FOLDER, THREADS_NUMBER=THREADS_NUMBER)
    print(f'Destination: {DOWNLOAD_FOLDER}')
    print(f'URL: {url}')
    print(f'Domain: {gi.domain}')
    print(f'Cookies: {gi.cookies}')
    print(f'RegExp: {gi.regexp}')
    s, d = gi.get_number()
    if not gi.get_number():
        print(f'get_number error: {d}')
        input('Press Enter to exit')
        return
    print(f'Page size: {len(gi.page)}')
    i = input(f'Found {gi.count} files. ' +
              'Download/print/copy? (d/p/c): ').lower()
    if i == 'p':
        print(*gi.urls, sep='\n')
        input('\nPress Enter to exit')
        return
    elif i == 'c':
        pyperclip.copy('\r\n'.join(gi.urls))
        return
    elif i == 'd':
        pass
    else:
        return
    s, d = gi.make_path()
    if not s:
        input(f'make_path error: {d}\n\nPress Enter to exit')
        return
    print(f'Folder: {gi.path}\nDownload started with {THREADS_NUMBER} threads...')
    gi.download_files()
    MessageBox(None, f'Done:\r\n{gi.path}', gi.msg_title, 64 + 4096)


if __name__ == '__main__':
    main()
