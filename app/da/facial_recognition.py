import logging
import pickle

from app.util.db import source

logger = logging.getLogger(__name__)


class FacialRecognitionDA(object):
    source = source

    @classmethod
    def user_has_embedding(cls, member_id):
        return cls.__user_has_embedding('id', member_id)

    @classmethod
    def get_user_embedding(cls, member_id):
        return cls.__get_user_embedding('member_id', member_id)

    @classmethod
    def create_user_embedding(cls, member_id, embedding):
        try:
            query = ("""
                        INSERT INTO face_embeddings (member_id, embeddings)
                        VALUES (%s, %s)
                        ON conflict(member_id) DO UPDATE 
                        SET embeddings = %s
                    """)
            params = (member_id, embedding, embedding)
            cls.source.execute(query, params)
            cls.source.commit()

            query = ("""
                        INSERT INTO member_security_preferences (member_id, facial_recognition)
                        VALUES (%s, true)
                        ON conflict(member_id) DO UPDATE 
                        SET facial_recognition = true
                    """)

            params = (member_id, )
            cls.source.execute(query, params)
            cls.source.commit()

            return True
        except:
            return False


    @classmethod
    def create_default_embeddings_matrix(cls):
        import numpy as np
        np.arange(128).reshape(1, 128)

    @classmethod
    def get_all_user_embeddings(cls):
        # TODO need a singleton here of just a giant blob
        pass

    @classmethod
    def __get_user_embedding(cls, key, value):
        query = ("""
               SELECT
                   member_id,
                   embeddings,
                   create_date,
                   update_date
               FROM face_embeddings
               WHERE {} = %s
               """.format(key))

        params = (value,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    member_id,
                    embedding,
                    create_date,
                    update_date
            ) in cls.source.cursor:
                embedding = pickle.loads(embedding)
                face_embeddings = {
                    "member_id": member_id,
                    "embedding": embedding,
                    "create_date": create_date,
                    "update_date": update_date,
                }

                return face_embeddings
        return None

    @classmethod
    def __user_has_embedding(cls, key, value):
        query = ("""
            SELECT
                member_id,
                create_date,
                update_date
            FROM face_embeddings
            WHERE {} = %s
            """.format(key))

        params = (value)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    member_id,
                    create_date,
                    update_date
            ) in cls.source.cursor:
                face_embeddings = {
                    "id": member_id,
                    "create_date": create_date,
                    "update_date": update_date,
                }

                return face_embeddings
        return None