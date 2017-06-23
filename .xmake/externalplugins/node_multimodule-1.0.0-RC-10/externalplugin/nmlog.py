import log


"""
 Wiki: ANSI escape code (the following may not apply as is to Python)
 Foreground: 3X
 Background: 4X
 Black letters on white background use ESC[30;47m

 Black    0
 Red      1
 Green    2
 Yellow   3
 Blue     4
 Magenta  5
 Cyan     6
 White    7
"""

def info(*args):
    _nmLogger.info(*args)


def error(*args):
    _nmLogger.error(*args)

def warning(*args):
    _nmLogger.warning(*args)


def debug(*args):
    _nmLogger.debug(*args)


def colored_logs():
    """Call this function to enable colored logs."""
    global _nmLogger
    _nmLogger = ColorLog


class ColorLog(object):
    @staticmethod
    def info(*args):
        # green
        log.info("\033[1;32m[node_multimodule]\033[1;0m", *args)

    @staticmethod
    def error(*args):
        # red
        log.error("\033[1;31m[node_multimodule]\033[1;0m", *args)

    @staticmethod
    def warning(*args):
        # yellow
        log.warning("\033[1;33m[node_multimodule]\033[1;0m", *args)

    @staticmethod
    def debug(*args):
        # cyan
        log.debug("\033[1;36m[node_multimodule]\033[1;0m", *args)


_nmLogger = log
