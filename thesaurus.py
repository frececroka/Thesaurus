import sublime, sublime_plugin
import json

from urllib.request import Request
from urllib.request import urlopen
from urllib.error import HTTPError

class NoResultError(Exception):
  pass

class ThesaurusCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    self.region = False

    word = self.selected_word()
    if word is None or len(word) == 0:
      self.view.set_status('Thesaurus', 'Please select a word first')
      return

    try:
      results = list(self.synonyms(word))
      options = [o['title'] for o in results]
      sublime.active_window().show_quick_panel(options, lambda i: self.senseSelected(results, i))
    except NoResultError:
      self.view.set_status('Thesaurus', 'No synonyms found')

  def senseSelected(self, results, index):
    if index != -1:
      synonyms = list(results[index]['synonyms'])
      sublime.active_window().show_quick_panel(synonyms, lambda i: self.synonymSelected(synonyms, i))
    else:
      self.view.erase_status('Thesaurus')

  def synonymSelected(self, synonyms, index):
    if index != -1:
      self.view.run_command('replace_region', { 'region': { 'a': self.region.a, 'b': self.region.b }, 'value': synonyms[index] })
    self.view.erase_status('Thesaurus')

  def selected_word(self):
    for region in self.view.sel():
      if not region.empty():
        self.region = region
        return self.view.substr(region)

  def synonyms(self, word):
    result = []
    try:
      data = self.get_json_from_api(word)
      return self.parse_response(data)
    except HTTPError:
      raise NoResultError()

  def parse_response(self, response):
    for entry in response['results'][0]['lexicalEntries']:
      for sense in entry['entries'][0]['senses']:
        synonyms = self.synonyms_from_sense(sense)
        if 'examples' in sense and len(sense['examples']) > 0:
          title = sense['examples'][0]['text']
        else:
          title = 'No examples :('
        yield { 'title': title, 'synonyms': synonyms }

  def synonyms_from_sense(self, sense):
    if 'subsenses' in sense:
      return self.synonyms_from_senses(sense['subsenses'])
    else:
      return self.synonyms_from_senses([sense])

  def synonyms_from_senses(self, senses):
    for sense in senses:
      for synonym in sense['synonyms']:
        yield synonym['text']

  def get_json_from_api(self, word):
    req = Request('https://od-api.oxforddictionaries.com/api/v1/entries/{}/{}/synonyms'.format(self.language(), word))
    req.add_header('accept', 'application/json')
    app_id, api_key = self.credentials()
    req.add_header('app_id', app_id)
    req.add_header('app_key', api_key)
    with urlopen(req) as res:
      return json.loads(res.read().decode('utf-8'))

  def credentials(self):
    settings = sublime.load_settings('Thesaurus.sublime-settings')
    return settings.get('app_id'), settings.get('api_key')

  def language(self):
    settings = sublime.load_settings('Thesaurus.sublime-settings')
    return settings.get('language', 'en')

class ReplaceRegionCommand(sublime_plugin.TextCommand):
  def run(self, edit, region, value):
    self.view.replace(edit, sublime.Region(region['a'], region['b']), value)
