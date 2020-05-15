import os

from ..auto import detect_modified_images, parse_image_with_tag
from ..context import context
from ..errors import FatalError
from ..image_bundle import ImageBundle


class BuildCommand:
    def __init__(self, parser):
        parser.add_argument("-d", "--debug", action="store_true")
        parser.add_argument("-b", "--branch", type=str)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--cross-build", action="store_true")
        parser.add_argument("--no-cache", action="store_true")
        parser.add_argument("images", type=str, nargs="*")

    def run(self, args):
        context.debug = args.debug
        context.dry_run = args.dry_run
        context.no_cache = args.no_cache
        if args.cross_build:
            context.cross_build = context.buildx_installed

        if not context.git.branch:
            if not args.branch:
                raise FatalError("No Git repository detected. Please use "
                                 "\"--branch\" to specify a branch manually.")
            else:
                context.branch = args.branch

        cwd = os.getcwd()

        try:
            os.chdir(context.images_dir)
            if len(args.images) == 0:
                for image in detect_modified_images():
                    image.build()
            else:
                for image in args.images:
                    name, tag = parse_image_with_tag(image)
                    ImageBundle(name, tag).build()
        finally:
            os.chdir(cwd)
