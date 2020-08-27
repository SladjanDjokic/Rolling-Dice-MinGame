import os
import datetime
import errno

# The safe_open helper lets us handle opening non existent folders


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def safe_open(path, rights):
    ''' Open "path" for writing, creating any parent directories as needed.
    '''
    mkdir_p(os.path.dirname(path))
    return open(path, rights)


def timestampify_filekey(file_path):
    file_id = str(int(datetime.datetime.now().timestamp() * 1000))
    (dirname, true_filename) = os.path.split(file_path)
    file_name = file_id + "-" + true_filename
    storage_key = f"{dirname}/{file_name}"
    return storage_key


def s3fy_filekey(file_key):
    # boto3 methods accepts a file key without '/' in the beggining when it is a nested key and /filekey.ext when it is a root file key
    (dirname, file_name) = os.path.split(file_key)
    key = file_key.lstrip('/') if dirname != '/' else file_key
    return key
