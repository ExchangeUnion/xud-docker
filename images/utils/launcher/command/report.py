class Command:
    def __init__(self, context):
        network = context.network
        network_dir = context.network_dir
        self.text = f"""Please click on https://github.com/ExchangeUnion/xud/issues/\
new?assignees=kilrau&labels=bug&template=bug-report.md&title=Short%2C+concise+\
description+of+the+bug, describe your issue, drag and drop the file "{network}\
.log" which is located in "{network_dir}" into your browser window and submit \
your issue."""

    def match(self, *args):
        return args[0] == "report"

    def run(self, *args):
        print(self.text)
