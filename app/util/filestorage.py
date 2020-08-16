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


def add_ts_to_file_key(file_path):
    file_id = str(int(datetime.datetime.now().timestamp() * 1000))
    (dirname, true_filename) = os.path.split(file_path)
    file_name = file_id + "-" + true_filename
    storage_key = f"{dirname}/{file_name}"
    return storage_key
