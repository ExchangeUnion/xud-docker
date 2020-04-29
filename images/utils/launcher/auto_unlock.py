class Action:
    def __init__(self, node_manager):
        self.node_manager = node_manager

    @property
    def shell(self):
        return self.node_manager.shell

    def xucli_unlock_wrapper(self, xud):
        while True:
            try:
                print()
                xud.cli("unlock", self.shell)
                break
            except KeyboardInterrupt:
                raise
            except:
                pass

    def execute(self):
        xud = self.node_manager.get_node("xud")
        self.xucli_unlock_wrapper(xud)
