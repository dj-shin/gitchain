import hashlib
import subprocess
import time
import re
from datetime import datetime
import itertools
import string
import multiprocessing as mp


def gen(idx, n_procs, msg, q):
    repeat = 6
    l = len(msg) + repeat + 2
    data = b'commit %d\0%s' % (l, msg)
    r = re.compile(b'(committer [^ ]+ [^ ]+ )(?P<commit_time>\d+)( .*)')
    current_time = int(r.search(data)['commit_time'].decode())
    now = int(time.time())
    difficulty = 7
    for t in range(now + 120, now + 86400):
        new_str = r.search(data)[1] + str(t).encode() + r.search(data)[3]
        replaced = r.sub(new_str, data)
        for nonce in itertools.islice(itertools.product(string.ascii_letters, repeat=repeat), idx, len(string.ascii_letters) ** repeat, n_procs):
            nonce = ''.join(nonce)
            padded = replaced + b'\n' + nonce.encode() + b'\n'
            commit_hash = hashlib.sha1(padded).hexdigest()
            if commit_hash[:difficulty] == '0' * difficulty:
                q.put((t, nonce))


if __name__ == '__main__':
    n_procs = 32
    ctx = mp.get_context('spawn')
    q = ctx.Queue()
    plist = list()
    sp = subprocess.run(['git', 'cat-file', 'commit', 'HEAD'], stdout=subprocess.PIPE)
    msg = sp.stdout
    for idx in range(n_procs):
        p = ctx.Process(target=gen, args=(idx, n_procs, msg, q))
        p.start()
        plist.append(p)

    t, nonce = q.get()
    for p in plist:
        p.terminate()

    print(t)
    print(datetime.fromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S'))
    print(nonce)
