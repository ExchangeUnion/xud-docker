import os
import re
from subprocess import check_output, PIPE

from .context import context
from .image_bundle import ImageBundle
from .errors import FatalError


def get_modified_image(x):
    if x.startswith("images/utils"):
        return ImageBundle("utils", "latest")
    else:
        p = re.compile(r"^images/([^/]*)/([^/]*)/.*$")
        m = p.match(x)
        if m:
            if m.group(2) == "shared":
                all_tags = []
                for tag in os.listdir(m.group(1)):
                    if tag != "shared":
                        all_tags.append(ImageBundle(m.group(1), tag))
                return all_tags
            else:
                return ImageBundle(m.group(1), m.group(2))
        else:
            return None


def add_diff_lines_to_modified_images(modified, lines):
    for x in lines:
        r = get_modified_image(x)
        if x.startswith("images") and r:
            if isinstance(r, list):
                modified.update(r)
            else:
                modified.add(r)


def get_modified_images_since_commit(commit):
    result = set()
    lines = check_output("git diff --name-only {}".format(commit), shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    return sorted(result)


def get_modified_images_at_head():
    result = set()
    lines = check_output("git diff --name-only", shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    lines = check_output("git diff --name-only --cached", shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    return sorted(result)


def get_modified_images_at_commit(commit):
    if commit == "HEAD":
        return get_modified_images_at_head()

    result = set()
    lines = check_output("git diff-tree --no-commit-id --name-only -r {}".format(commit), shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    return sorted(result)


def get_unmodified_history(img, history, history_modified):
    h = history
    for i, m in enumerate(history_modified):
        if img in m:
            h = history[:i + 1]
            break
    return h


def get_modified_images():
    if context.git.branch == "master":
        modified = get_modified_images_since_commit(context.commit_before_travis)
    else:
        modified = get_modified_images_since_commit(context.git.master_head)
    history_modified = []

    if context.debug:
        print("\033[1mBranch {} history:\033[0m".format(context.git.branch))
    for commit in context.git.history:
        images = get_modified_images_at_commit(commit)
        history_modified.append(images)
        if context.debug:
            print("\033[33m{}:\033[0m {}".format(commit[:7], context.git.get_commit_message(commit)))
            if len(images) == 0:
                print("  (None)")
            else:
                for img in images:
                    print("- {}".format(img.image_dir))

    if context.debug:
        print("\033[1mImages' unmodified history:\033[0m")
    for img in modified:
        unmodified_history = get_unmodified_history(img, context.git.history, history_modified)
        img.set_unmodified_history(unmodified_history)
        if context.debug:
            print("- {}: {}".format(img.image_dir, ", ".join([h[:7] for h in unmodified_history])))

    return filter_deleted_images(modified)


def parse_image_with_tag(image):
    if ":" in image:
        parts = image.split(":")
        return parts[0], parts[1]
    else:
        if image == "utils":
            return "utils", "latest"
        else:
            raise FatalError("Missing tag")


def filter_deleted_images(images):
    result = []
    for img in images:
        if os.path.exists(img.image_dir):
            result.append(img)
    return result


def print_modified_images(images):
    if len(images) == 0:
        return
    print("\033[1mDetected modified images:\033[0m")
    for img in images:
        print("- {}".format(img.image_dir))


def detect_modified_images():
    modified = get_modified_images()
    print_modified_images(modified)
    return modified
