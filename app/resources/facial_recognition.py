import logging
import pickle
import numpy as np

import falcon
import app.util.json as json

from app import settings
from app.da.facial_recognition import FacialRecognitionDA
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import SessionExistsError

logger = logging.getLogger(__name__)


class FacialRecognitionResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.facial_recognition'),
                                    "topic": settings.get('kafka.topics.auth')
                                    },
                           }

    def on_get(self, req, resp):
        """
        Check for facial recognition data (this could be moved to settings) Return True/False to trigger
        Perform DB query for facial data or if facial_data settings is set to True
        """
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except Exception as e:
            raise SessionExistsError(e)
        # TODO get user settings to see if facial_recognition is enabled
        member_id = session['member_id']
        # member_settings = MemberSettingDA().get_member_settings(member_id)
        # if not member_settings.get('facial_recognition'):
        #     raise MemberNotFound(member_id)
        member_embeddings = FacialRecognitionDA().user_has_embedding(member_id)
        # TODO verify embeddings are relatively new based on update date
        if member_embeddings:
            resp.body = json.dumps({
                "success": True,
            })
        else:
            resp.body = json.dumps({
                "success": False
            })
            resp.status = falcon.HTTP_404

    def on_post(self, req, resp):
        """
        Train or Match facial data based on the video stream based on query_params or post_data.
        Perform Db query for facial data or save data based on training if training succedes

        """
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except Exception as e:
            raise SessionExistsError(e)

        member_id = session.get('member_id')

        # TODO get user settings to see if facial_recognition is enabled
        # member_id = session['member_id']
        # member_settings = MemberSettingDA().get_member_settings(member_id)
        # if not member_settings.get('facial_recognition'):
        #     raise MemberNotFound(member_id)

        if req.params.get('training-data'):
            # FE passes us trained embedding to save
            data = req.media
            embeddings = data.get('embeddings')
            # TODO Check if we have group emeddings. If not create
            # TODO append user embeddings to matrix. Also save embeddings to facial so we know their id in the matrix
            # group_embeddings = FacialRecognitionDA.get_all_user_embeddings()
            user_name = embeddings[0].get('label')
            embeddings_list = []
            for e in embeddings:
                embeddings_list.append(e.get('descriptors'))
            # e = np.array(embeddings_list)
            # Convert to float array
            # embedding = list(embedding.items())
            # embedding = np.array(embeddings)
            embeddings_list = np.asfarray(embeddings_list)
            logger.debug(embeddings_list)
            embeddings_list = pickle.dumps(embeddings_list)

            db_resp = FacialRecognitionDA().create_user_embedding(member_id, embeddings_list)
            # TODO Add update
            if db_resp:
                resp.body = json.dumps({
                    "success": True
                })
                resp.status = falcon.HTTP_201
            else:
                logger.error("Error saving face embedding")
                resp.status = falcon.HTTP_400
        elif req.params.get('train'):
            # TODO Train new embeddings. This is BE Flow using video/picture for reach angle
            pass
        else:
            # FE Sends embeddings and we compare with our own twist for security
            data = req.media
            new_embedding = data.get('embedding')
            # new_embedding = list(new_embedding.items())
            logger.debug(f"new_embedding, {new_embedding}")
            new_array = np.array(new_embedding).transpose()
            logger.debug(f"new_array {new_array}")
            old_embeddings_data = FacialRecognitionDA().get_user_embedding(int(session.get('member_id')))
            old_array = old_embeddings_data.get('embedding')
            logger.debug(f"old_array {old_array}")
            np_dist = np.linalg.norm(old_array - new_array, axis=1)
            logger.debug(np_dist)
            # dist_sum = np.sum(np_dist)
            # Sum every 5 numbers to get the sum for each user
            group_dist_sum = np.add.reduceat(np_dist, np.arange(0, len(np_dist), 5))
            logger.debug(f"Group DISTANCE Matrix {group_dist_sum}")
            # If any of the sums match and it matches the users index
            match = False
            for s in range(0, len(group_dist_sum)):
                if group_dist_sum[s] < float(settings.get('facial_recognition.distance_max')):
                    # TODO match member_id to index s to make sure its them
                    match = True

            if match:
                resp.body = json.dumps({
                    "success": True
                })
                resp.status = falcon.HTTP_200
                # TODO produce positive result to kafka
            else:
                resp.body = json.dumps({
                    "success": False
                })
                resp.status = falcon.HTTP_400
                # TODO produce false positive to kafka

