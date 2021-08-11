import requests
from typing import List, Optional
from collections import defaultdict
import unicodedata

import pickle
import os
import csv

BASE_URL = 'https://developer.apple.com/tutorials/data/documentation/devicemanagement/restrictions.json'
CHANGES_URL = 'https://developer.apple.com/tutorials/data/diffs/documentation/devicemanagement/restrictions.json'

VERSIONS = ['latest_major', 'latest_minor']
CHANGE_FILTERS = ['added']

class RestrictionScraper:

    def __init__(self, base_url: str, changes_url: str, versions: List[str], change_filters: List[str], cache_pth: str = '.cache'):
        self.base_url = base_url
        self.changes_url = changes_url
        self.versions = versions
        self.change_filters = set(change_filters)
        self.cache_pth = cache_pth
        
        self.base_data = get_base_data(base_url)

    def get_base_data(self, url: str) -> dict:
        return requests.get(url).json()

    def get_changes(self) -> dict:
        changes = defaultdict(lambda: defaultdict(list))
        for v in self.versions:
            data = requests.get(self.changes_url, params={'changes': v}).json()
            data = data['doc://com.apple.documentation/documentation/devicemanagement/restrictions']['properties']

            for k in data.keys():
                change_type = data[k]['change']
                if change_type in self.change_filters:
                    changes[v][change_type].append(k)

        return changes
    
    def check_versions(self) -> Tuple[dict, List]:
        minor_version = '-'.join(self.base_data['diffAvailability']['minor']['versions'])
        major_version = '-'.join(self.base_data['diffAvailability']['major']['versions'])

        out = {'minor_version': minor_version, 'major_version': major_version}

        if os.path.exists(self.cache_pth):
            with open(self.cache_pth, 'wb') as cache:
                pickle.dump(out, cache)
        else:
            prev = None
            with open(self.cache_pth, 'rb') as cache:
                prev = pickle.load(cache)
            
            changes = []
            for k in out:
                if k not in prev:
                    raise NotImplementedError()
                if prev[k] != out[k]:
                    changes.append((k, prev[k], out[k]))
            
            with open(self.cache_pth, 'wb') as cache:
                pickle.dump(out, cache)

        return out, changes

    def get_desc(self, desc_queries: List[str]) -> dict:
        desc_queries = set(desc_queries)
        out = []
        all_restrictions = self.base_data['primaryContentSections'][0]['items']
        
        for res in all_restrictions:
            if res['name'] in desc_queries:
                text = res['content'][0]['inlineContent']
                joined_text = []
                for sub_text in text:
                    text_key = 'text' if 'text' in sub_text else 'code'
                    joined_text.append(sub_text[text_key])

                joined_text = ''.join(joined_text)
                joined_text = unicodedata.normalize("NFKD", joined_text)

                curr_data = [res['name'], joined_text, res['type'][0]['text']]
                out.append(curr_data)

        return out
    
    def generate_body(self, updates: List[Tuple[str]]) -> str:
        s = []

        for u in updates:
            s.append('{} updated to {} from {} see attachment for what was added.')
        
        return '\n'.join(s)

    def run(self):
        self.version_dict, self.changes = self.check_versions()

        if self.changes:
            changes = self.get_changes()
            
            for v in VERSIONS:
                restrictions = []
                for c in CHANGE_FILTERS:
                    restrictions.extend(changes[v][c])

                with open(v + '.csv') as writefile:
                    csv_w = csv.writer(writefile)
                    csv_w.writerow(['name', 'text', 'type'])
                    csv_w.writerows(self.get_desc(restrictions))

def main():
    rs = RestrictionScraper(BASE_URL, CHANGES_URL, VERSIONS, CHANGE_FILTERS)
    rs.run()

if __name__ == "__main__":
    main()