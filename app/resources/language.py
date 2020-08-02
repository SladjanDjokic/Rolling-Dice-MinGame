import os
import logging

import app.util.json as json
import app.util.request as request

logger = logging.getLogger(__name__)

class LanguageResource(object):

    current_path = os.path.dirname(os.path.abspath(__file__))

    def on_get(self, req, resp):

        languages = ['de', 'en-US', 'es', 'ja', 'ko', 'zh']

        data = {}
        for language in languages:

            file_path = self.current_path + "/../util/languages/" + language + ".json"
        
            with open(file_path, "r") as read_file:
                data[language] = json.load(read_file)
        
        resp.body = json.dumps(data)

    def on_post(self, req, resp):
        (language, id, text) = request.get_json_or_form(
            "language", "id", "text", req=req)
        
        file_path = self.current_path + "/../util/languages/" + language + ".json"
        data = {}
        with open(file_path, "r") as read_file:
            data = json.load(read_file)
            read_file.close()

        data[id] = text
        with open(file_path, "w") as write_file:
            json.dump(data, write_file)
            write_file.close()

        resp.body = json.dumps(data)
        
