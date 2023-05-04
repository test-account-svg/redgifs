"""
The MIT License (MIT)

Copyright (c) 2022-present scrazzz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

# TODO: Cleanup code, add typehints.
# TODO: Switch to using a CLI library like typer.
# TODO: Use rich for pretty console messages.

import re
import sys
import argparse
import platform
import importlib.metadata
from typing import Optional

import aiohttp
import requests
from yarl import URL

import redgifs

parser = argparse.ArgumentParser(prog='redgifs')
parser.add_argument('link', nargs='?', help='Enter a RedGifs URL to download it')
parser.add_argument('--folder', help='Folder to download the video(s) to.', metavar='')
parser.add_argument('-l', '--list', help='Download GIFs from a list of URLs', metavar='')
parser.add_argument('-v', '--version', help='Show redgifs version info.', action='store_true')
args = parser.parse_args()

session = requests.Session()
client = redgifs.API(session=session)

# TODO: Check allowed chars in usernames
USERNAME_RE = re.compile(r'https:\/\/(www\.)?redgifs\.com\/users\/(?P<username>\w+)')

def show_version() -> None:
    entries = []

    entries.append('- Python v{0.major}.{0.minor}.{0.micro}-{0.releaselevel}'.format(sys.version_info))
    version_info = redgifs.version_info
    entries.append('- redgifs v{0.major}.{0.minor}.{0.micro}-{0.releaselevel}'.format(version_info))
    if version_info.releaselevel != 'final':
        version = importlib.metadata.version('redgifs')
        if version:
            entries.append(f'    - redgifs metadata: v{version}')
    
    entries.append(f'- aiohttp v{aiohttp.__version__}')
    uname = platform.uname()
    entries.append('- system info: {0.system} {0.release} {0.version}'.format(uname))
    print('\n'.join(entries))

def save_to_file(mp4_link) -> None:
    headers = client.http.headers
    r = session.get(mp4_link, headers=headers, stream=True)
    file_name = mp4_link.split('/')[3].split('?')[0]
    with open(file_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    
    print(f'\nDownloaded: {file_name}')

def start_dl(url: str, *, folder: Optional[str]) -> None:
    yarl_url = URL(url)
    if 'redgifs' not in str(yarl_url.host):
        raise TypeError(f'"{url}" is not a valid redgifs URL')

    # Handle 'normal' URLs, i.e, a direct link from browser (eg: "https://redgifs.com/watch/deeznuts")
    if 'watch' in yarl_url.path:
        id = yarl_url.path.split('/')[-1]
        hd = client.get_gif(id).urls.hd
        print(f'Downloading {id}...')
        save_to_file(hd)
    
    # Handle /users/ URLs
    if '/users/' in yarl_url.path:
        match = re.match(USERNAME_RE, str(yarl_url))
        if not match:
            raise TypeError(f'Not a valid /users/ URL: {yarl_url}')
        user = match.groupdict()['username']
        data = client.search_creator(user)
        curr_page = data.page
        total_pages = data.pages
        total_gifs = data.gifs
        total = data.total
        done = 0

        # Case where there is only 1 page
        if curr_page == total_pages:
            for gif in total_gifs:
                try:
                    client.download(gif.urls.hd, f'{folder}/{gif.urls.hd.split("/")[3].split(".")[0]}.mp4')
                    done += 1
                    print(f'Downloaded {done}/{total} GIFs')
                except Exception as e:
                    if isinstance(e, FileNotFoundError):
                        print(f'[!] An error occured while downloading: {e}\nMake sure you have a folder called "{folder}" in the current working directory.')
                        exit(1)
                    else:
                        print(f'[!] Error occurred when downloading {url}:\n{e}. Continuing...')
                        continue
            
            print(f'\nDownloaded {done}/{total} videos of "{user}" to "{folder}" folder successfully!')
            exit(0)

        # If there's more than 1 page
        while curr_page != total_pages:
            for gif in total_gifs:
                try:
                    client.download(gif.urls.hd, f'{folder}/{gif.urls.hd.split("/")[3].split(".")[0]}.mp4')
                    done += 1
                    print(f'Downloaded {done}/{total} GIFs')
                except Exception as e:
                    if isinstance(e, FileNotFoundError):
                        print(f'[!] An error occured while downloading: {e}\nMake sure you have a folder called "{folder}" in the current working directory.')
                        exit(1)
                    else:
                        print(f'[!] Error occurred when downloading {url}:\n{e}. Continuing...')
                        continue
            curr_page += 1
            total_gifs.clear()
            data = client.search_creator(user, page=curr_page)
            total_gifs.extend(data.gifs)
            
        print(f'\nDownloaded {done}/{total} videos of "{user}" to "{folder}" folder successfully!')
        exit(0)


def main() -> None:
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.link:
        client.login()
        start_dl(args.link, folder=args.folder)

    if args.list:
        client.login()
        with open(args.list) as f:
            for url in f.readlines():
                start_dl(url, folder=args.folder)

    if args.version:
        show_version()

if __name__ == '__main__':
    main()
