"""Command-line entry point for logdrift.

Usage examples::

    logdrift tail service-a.log service-b.log --level WARNING --service api
    logdrift tail app.log --keyword error --format json
"""

import argparse
import signal
import sys

from logdrift.tailer import LogTailer
from logdrift.aggregator import LogAggregator
from logdrift.filters import by_level, by_service, by_keyword, compose
from logdrift.formatter import get_formatter


def _build_filters(args):
    filters = []
    if args.level:
        filters.append(by_level(args.level))
    if args.service:
        filters.append(by_service(args.service))
    if args.keyword:
        filters.append(by_keyword(args.keyword))
    return filters


def _run_tail(args):
    tailers = [LogTailer(path) for path in args.files]
    filters = _build_filters(args)
    formatter = get_formatter(args.format)
    agg = LogAggregator(tailers, filters=filters)

    def _shutdown(sig, frame):  # noqa: ARG001
        print("\nStopping logdrift…", file=sys.stderr)
        agg.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    agg.start()
    try:
        for entry in agg.stream():
            print(formatter(entry))
    except KeyboardInterrupt:
        agg.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logdrift",
        description="Lightweight real-time log aggregation utility.",
    )
    sub = parser.add_subparsers(dest="command")

    tail = sub.add_parser("tail", help="Tail and filter one or more log files.")
    tail.add_argument("files", nargs="+", metavar="FILE", help="Log file paths to tail.")
    tail.add_argument("--level", metavar="LEVEL", help="Minimum log level (e.g. WARNING).")
    tail.add_argument("--service", metavar="NAME", help="Filter by service name.")
    tail.add_argument("--keyword", metavar="WORD", help="Filter by keyword in message.")
    tail.add_argument(
        "--format",
        choices=["text", "json", "compact"],
        default="text",
        help="Output format (default: text).",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "tail":
        _run_tail(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
