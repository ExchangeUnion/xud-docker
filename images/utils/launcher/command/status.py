BRIGHT_BLACK = "\033[90m"
BLUE = "\033[34m"
RESET = "\033[0m"
BOLD = "\033[0;1m"

class Command:
    def __init__(self, context):
        self._context = context

    def match(self, *args):
        return args[0] == "status"

    def run(self):
        containers = self._containers
        names = list(containers)
        col1_title = "SERVICE"
        col2_title = "STATUS"
        col1_width = max(max([len(name) for name in names]), len(col1_title))
        col2_width = 62 - col1_width - 7
        col1_fmt = "%%-%ds" % col1_width
        col2_fmt = "%%-%ds" % col2_width

        border_style = BRIGHT_BLACK
        service_style = BLUE
        title_style = BOLD

        print(f"{border_style}┌─%s─┬─%s─┐{RESET}" % ("─" * col1_width, "─" * col2_width))
        print(f"{border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET} {title_style}%s{RESET} {border_style}│{RESET}" % (col1_fmt % col1_title, col2_fmt % col2_title))
        for name in names:
            print(f"{border_style}├─%s─┼─%s─┤{RESET}" % ("─" * col1_width, "─" * col2_width))
            print(f"{border_style}│{RESET} {service_style}%s{RESET} {border_style}│{RESET} {border_style}%s{RESET} {border_style}│{RESET}" % (col1_fmt % name, col2_fmt % ""))
        print(f"{border_style}└─%s─┴─%s─┘{RESET}" % ("─" * col1_width, "─" * col2_width))

        lock = threading.Lock()

        def update_line(name, text, fetching=False):
            nonlocal border_style
            i = names.index(name)
            n = len(names)
            y = (n - i) * 2
            x = col1_width + 2
            if fetching:
                print(f"\033[%dA\033[%dC{border_style}%s{RESET}\033[%dD\033[%dB" % (y, x + 3, col2_fmt % text[:col2_width], x + col2_width + 3, y), end="")
            else:
                print("\033[%dA\033[%dC%s\033[%dD\033[%dB" % (y, x + 3, col2_fmt % text[:col2_width], x + col2_width + 3, y), end="")
            sys.stdout.flush()

        result = {name: None for name in names}

        def update_status(name, status):
            nonlocal result
            with lock:
                result[name] = status
                update_line(name, status)

        def status_wrapper(container, name, update_status):
            status = container.status()
            update_status(name, status)

        class State:
            def __init__(self, result):
                self.counter = 0
                self.result = result

            def __repr__(self):
                return f"<State counter={self.counter} result={self.result}>"

        def fetching(state: State):
            with lock:
                for name, status in state.result.items():
                    if status is None:
                        dots = abs(3 - state.counter % 6)
                        update_line(name, "fetching" + "." * dots, fetching=True)

        def fetching_loop(stop_event: threading.Event):
            nonlocal result
            state = State(result)
            while not stop_event.is_set():
                fetching(state)
                state.counter += 1
                stop_event.wait(1)
            self._logger.debug("fetching loop end")

        stop_fetching_animation = threading.Event()
        threading.Thread(target=fetching_loop, args=(stop_fetching_animation,), name="Animation").start()

        while len(containers) > 0:
            failed = {}
            with ThreadPoolExecutor(max_workers=len(containers)) as executor:
                fs = {executor.submit(status_wrapper, container, name, update_status): (name, container) for name, container in self._containers.items()}
                done, not_done = wait(fs, 30)
                for f in done:
                    name, container = fs[f]
                    try:
                        f.result()
                    except:
                        self._logger.exception("Failed to get %s status", name)
                        failed[name] = container
                for f in not_done:
                    name, container = fs[f]
                    self._logger.debug("Get %s status timeout", name)
                    failed[name] = container
            if len(failed) > 0:
                for name in failed.keys():
                    update_status(name, "failed to fetch status")
            containers = {}

        stop_fetching_animation.set()