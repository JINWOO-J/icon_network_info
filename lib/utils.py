import sys
import os, time, datetime
import json
import hashlib
from datetime import datetime
from timeit import default_timer
import threading
import boto3
from botocore.handlers import disable_signing
from boto3.s3.transfer import TransferConfig

class bcolors:
    red = "\033[91m"
    green = "\033[92m"
    yellow = "\033[93m"
    light_purple = "\033[94m"
    purple = "\033[95m"

    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._prevent_bytes = 0

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            # tx = bytes_amount - self._prevent_bytes
            sys.stdout.write(
                "\r \t %s  %s / %s  (%.2f%%) " % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush


def get_DistributionId(url):
    client = boto3.client('cloudfront')
    paginator = client.get_paginator('list_distributions')
    response_iterator = paginator.paginate()
    for i in response_iterator:
        for j in i['DistributionList']['Items']:
            if j['Aliases']['Items'][0] == url:
                return j['Id']


def invalidate_cloudfont(DistributionId, purge_list=[]):
    client = boto3.client('cloudfront')

    print("invalidate list")
    dump(purge_list)

    try:
        response = client.create_invalidation(
            #DistributionId=get_id(sys.argv[1]),
            DistributionId=DistributionId,
            InvalidationBatch={
                'Paths': {
                    'Quantity': len(purge_list),
                    # 'Items': [
                    #     '/*'
                    # ],
                    'Items': purge_list
                    # 'Items': ['/{}'.format(f) for f in purge_list]
                },
                'CallerReference': str(todaydate("ms")).replace(".", "")
            }
        )
    except Exception as e:
        # e = str(e).replace(":", ":\n")
        CPrint(f"\n[ERROR] invalidate_cloudfont fail / cause->{e}\n","red")
        sys.exit(1)
    return response


def multi_part_upload_with_s3(filename=None, key_path=None, bucket=None, upload_type="single"):
    start_time = default_timer()
    # print(f"\t bucket -> {bucket} ")
    if bucket == "-hk":
        s3 = boto3.resource(
            's3',
            region_name="ap-east-1"
        )
    else:
        s3 = boto3.resource(
            's3',
            # region_name="ap-northeast-2"
        )
    ##single parts
    if upload_type == "single":
        # s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
        config = TransferConfig(multipart_threshold=838860800, max_concurrency=10, multipart_chunksize=8388608,
                                num_download_attempts=5, max_io_queue=100, io_chunksize=262144, use_threads=True)
    # multiparts mode -> AWS S3 CLI: Anonymous users cannot initiate multipart uploads
    elif upload_type == "multi":
        pass
        config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10,
                                multipart_chunksize=1024 * 25, use_threads=True)
    else:
        CPrint(f"Unknown upload_type-> {upload_type}", "red")
    if filename is None:
        CPrint(f"[ERROR] filename is None", "red")
        raise SystemExit()
    if key_path is None:
        key_path = filename
    try:
        s3.meta.client.upload_file(filename, bucket, key_path,
                                   # ExtraArgs={'ACL': 'public-read', 'ContentType': 'text/pdf'},
                                   Config=config,
                                   Callback=ProgressPercentage(filename)
                                   )
    except Exception as e:
        e = str(e).replace(":", ":\n")
        CPrint(f"\n[ERROR] File upload fail / cause->{e}\n","red")
        sys.exit(1)
        # raise SystemExit()
    elapsed = default_timer() - start_time
    time_completed_at = "{:5.3f}s".format(elapsed)
    print(f"\n\t Upload is completed -> {filename} / {time_completed_at}")


def dump(obj, nested_level=0, output=sys.stdout):
    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    spacing = '   '
    def_spacing = '   '
    if type(obj) == dict:
        print('%s{' % (def_spacing + (nested_level) * spacing))
        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                print(bcolors.OKGREEN + '%s%s:' % (def_spacing + (nested_level + 1) * spacing, k) + bcolors.ENDC, end="")
                dump(v, nested_level + 1, output)
            else:
                print(bcolors.OKGREEN + '%s%s:' % (def_spacing + (nested_level + 1) * spacing, k) + bcolors.WARNING + ' %s' % v + bcolors.ENDC,
                      file=output)
        print('%s}' % (def_spacing + nested_level * spacing), file=output)
    elif type(obj) == list:
        print('%s[' % (def_spacing + (nested_level) * spacing), file=output)
        for v in obj:
            if hasattr(v, '__iter__'):
                dump(v, nested_level + 1, output)
            else:
                print(bcolors.WARNING + '%s%s' % (def_spacing + (nested_level + 1) * spacing, v) + bcolors.ENDC, file=output)
        print('%s]' % (def_spacing + (nested_level) * spacing), file=output)
    else:
        print(bcolors.WARNING + '%s%s' % (def_spacing + nested_level * spacing, obj) + bcolors.ENDC)


def CPrint(msg, color="green"):
    print(getattr(bcolors, color) + "%s" % msg + bcolors.ENDC)


def kvPrint(key, value, value_check=False):
    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    key_width = 9
    key_value = 3

    is_print = True

    if value_check:
        is_print = False

        if value:
            is_print = True

    if is_print:
        print(bcolors.OKGREEN + "{:>{key_width}} : ".format(key, key_width=key_width) + bcolors.ENDC, end="")
        print(bcolors.WARNING + "{:>{key_value}} ".format(str(value), key_value=key_value) + bcolors.ENDC)


def openJson(filename):
    if filename is None:
        filename = "FILENAME is NONE"
    try:
        json_data = open(filename).read()
    except:
        print("Error Openning json : " + filename)
        json_data = None
    try:
        result = json.loads(json_data)
    except:
        print("Error Decoding json : " + filename)
        result = {}
    return result


def writeJson(filename, data):
    with open(filename, "w") as outfile:
        # if updated_time:
        #     data["updated_time"] = todaydate("log")
        json.dump(data, outfile, indent=4)
    if os.path.exists(filename):
        CPrint("[OK] Write json file -> %s, %s" % (filename, file_size(filename)))


def writeFile(filename, data):
    with open(filename, "w") as f:
        f.write(data)
    if os.path.exists(filename):
        CPrint("[OK] Write file -> %s, %s" % (filename, file_size(filename)))


def convert_bytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    for x in ["bytes", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def file_size(file_path):
    """
    this function will return the file size
    """
    if os.path.isfile(file_path):
        file_info = os.stat(file_path)
        return convert_bytes(file_info.st_size)


def get_md5(fpath):
    assert os.path.isfile(fpath)
    md5o = hashlib.md5()
    with open(fpath, 'rb') as f:
        # read in 1MB chunks
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            md5o.update(chunk)
    return md5o.hexdigest()


def dict_compare(data1, data2):
    d1, d2 = (data1.copy(), data2.copy())
    if d1.get("updated_time"):
        del(d1["updated_time"])
    if d2.get("updated_time"):
        del(d2["updated_time"])
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same


def todaydate(type=None):
    if type is None:
        return '%s' % datetime.now().strftime("%Y%m%d")
    elif type == "log":
        return '%s' % datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif type == "ms":
        return '%s' % datetime.now().strftime("%Y%m%d_%H%M%S.%f")[:-3]


def pretty(value, htchar='\t', lfchar='\n', indent=0):
    nlch = lfchar + htchar * (indent + 1)
    if type(value) is dict:
        items = [
            nlch + repr(key) + ': ' + pretty(value[key], htchar, lfchar, indent + 1)
            for key in value
        ]
        return '{%s}' % (','.join(items) + lfchar + htchar * indent)
    elif type(value) is list:
        items = [
            nlch + pretty(item, htchar, lfchar, indent + 1)
            for item in value
        ]
        return '[%s]' % (','.join(items) + lfchar + htchar * indent)
    elif type(value) is tuple:
        items = [
            nlch + pretty(item, htchar, lfchar, indent + 1)
            for item in value
        ]
        return '(%s)' % (','.join(items) + lfchar + htchar * indent)
    else:
        return str(value)



