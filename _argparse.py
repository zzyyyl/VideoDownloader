from argparse import ArgumentParser


def ArgParser():
    parser = ArgumentParser()
    parser.add_argument("--silence", help="run in silence", action='store_true')
    parser.add_argument("-u", "--url", help="video url", metavar="URL", dest="url")
    return parser
