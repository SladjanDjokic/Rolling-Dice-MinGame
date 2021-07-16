
import argparse
import math
from collections import Counter
#import random

def eta(data, unit='shannon'):
    base = {
        'shannon' : 2.,
        'natural' : math.exp(1),
        'hartley' : 10.
    }

    if len(data) <= 1:
        return 0

    counts = Counter()

    for d in data:
        counts[d] += 1

    ent = 0

    probs = [float(c) / len(data) for c in counts.values()]
    for p in probs:
        if p > 0.:
            ent -= p * math.log(p, base[unit])

    return ent



def entropy_by_chunk(data, chunk_size, verbose=True):
    min_entropy = 0
    max_entropy = 0
    avg_entropy = 0
    if chunk_size <= 0:
        count = 0
    else:
        count = int(len(data) / chunk_size)

    if count > 1:
        for check in range(count):
            start = check * chunk_size
            stop = start + chunk_size
            nugget = slice(start, stop)
            entropy = eta(data[nugget])
            if check == 0:
                max_entropy = min_entropy = entropy
            elif min_entropy > entropy:
                min_entropy = entropy
            elif max_entropy < entropy:
                max_entropy = entropy

            avg_entropy += entropy
    else:
        avg_entropy = entropy = eta(data)
        if verbose:
            print(f'data {len(data)} single chunk')
            print(f'entropy {entropy:3.3}')

    if count > 0:
        avg_entropy = avg_entropy / count
        if verbose:
            print(f'data {len(data)} count {count} chunks of {chunk_size}')
            print(f'avg entropy {avg_entropy:3.3}, min entropy {min_entropy:3}, max entropy {max_entropy:3}')

    return avg_entropy

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculate color entropy from files')
    '''
    parser.add_argument("files", help="jpg files you wish to check")

    parser.add_argument('-c', action='store', default='3',
                    dest='select',
                    help='only color red=1, green=1, blue=2, all=3')
    '''
    parser.add_argument('-k', dest='key',
                    default='732dfc3dcd4387b0e56f484970988389d63b57d0dc995d69e803bc602a6d1865',
                    help='key you want entropy on')

    args = parser.parse_args()
    key = bytes.fromhex(args.key)

    fred = b'see me retie my bowtie'
    entropy = eta(fred)
    print(f' {fred.hex()} {entropy:3.3}')
