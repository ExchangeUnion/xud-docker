import argparse


def test1():
    p = argparse.ArgumentParser()

    def str2bool(s):
        s = s.lower()
        if s not in ('true', 'false'):
            raise ValueError('not a valid boolean value')
        return s == 'true'

    p.add_argument("--foo", type=str2bool, default=True)
    args = p.parse_args(["--foo=false"])
    print(args)
    args = p.parse_args([])
    print(args)
