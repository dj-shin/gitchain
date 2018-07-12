import hashlib
import subprocess
import time
import re
from datetime import datetime
import itertools
import string
import multiprocessing as mp
import argparse


def gen(idx, n_procs, msg, q, difficulty):
    repeat = 6
    l = len(msg) + repeat + 2
    data = b'commit %d\0%s' % (l, msg)
    r = re.compile(b'(committer (.*) )(?P<commit_time>\d+)( .*)')
    current_time = int(r.search(data).group('commit_time').decode())
    now = int(time.time())
    for t in range(now + 120, now + 86400):
        new_str = r.search(data).group(1) + str(t).encode() + r.search(data).group(4)
        replaced = r.sub(new_str, data)
        for nonce in itertools.islice(itertools.product(string.ascii_letters, repeat=repeat), idx, len(string.ascii_letters) ** repeat, n_procs):
            nonce = ''.join(nonce)
            padded = replaced + b'\n' + nonce.encode() + b'\n'
            commit_hash = hashlib.sha1(padded).hexdigest()
            if commit_hash[:difficulty] == '0' * difficulty:
                q.put((t, nonce))


parser = argparse.ArgumentParser(description='Git commit miner')
parser.add_argument('-d','--difficulty', type=int, default=7)
parser.add_argument('-t','--threads', type=int, default=32)
parser.add_argument('-f', '--force-commit', action='store_true', default=False)

if __name__ == '__main__':
    args = parser.parse_args()
    n_procs = args.threads
    difficulty = args.difficulty
    ctx = mp.get_context('spawn')
    q = ctx.Queue()
    plist = list()
    sp = subprocess.run(['git', 'cat-file', 'commit', 'HEAD'], stdout=subprocess.PIPE)
    msg = sp.stdout
    start = time.time()
    for idx in range(n_procs):
        p = ctx.Process(target=gen, args=(idx, n_procs, msg, q, difficulty))
        p.start()
        plist.append(p)

    t, nonce = q.get()
    end = time.time()
    for p in plist:
        p.terminate()
    print('Run time:', end - start)

    print(t)
    print(datetime.fromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S'))
    print(nonce)
    if args.force_commit:
        now = int(time.time())
        wait = t - now
        print('waiting %d seconds to commit' % wait)
        sp = subprocess.run(['git', 'log', '-1', '--pretty=%B'], stdout=subprocess.PIPE)
        message = sp.stdout.decode()
        time.sleep(wait)
        sp = subprocess.run(['git', 'commit', '-a', '--amend', '-m', message + nonce + '\n'])
