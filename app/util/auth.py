from app.da.session import SessionDA


def validate_token(token):
    return SessionDA.get_session(token)
