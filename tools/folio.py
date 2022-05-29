#!/usr/bin/env python3
#   encoding: utf-8

# This is a parser-based text adventure.
# Copyright (C) 2022 D E Haynes

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
TODO: Generate orders as per turberfield-dialogue:main.

.. _WeasyPrint: http://weasyprint.org/

"""

import argparse
import pathlib
import sys

from balladeer import Drama
from balladeer import Story
from turberfield.dialogue.adapters import ColourAdapter
from turberfield.dialogue.cli import add_common_options
from turberfield.dialogue.cli import add_performance_options
from turberfield.dialogue.main import HTMLHandler
from turberfield.utils.logger import LogAdapter
from turberfield.utils.logger import LogManager


def main(args):
    log_manager = LogManager()
    log = log_manager.get_logger("main")

    if args.log_path:
        log_manager.set_route(log, args.log_level, ColourAdapter(), sys.stderr)
        log_manager.set_route(log, log.Level.NOTSET, LogAdapter(), args.log_path)
    else:
        log_manager.set_route(log, args.log_level, ColourAdapter(), sys.stderr)

    drama = Drama()
    drama.folder = ["blathnaid/dlg/tale.rst"]

    handler = HTMLHandler(dwell=args.dwell, pause=args.pause)
    story = Story(context=drama)
    presenter = story.represent()

    for frame in presenter.frames:
        for seq in frame.values():
            for obj in seq:
                try:
                    next(handler(obj))
                except Exception as e:
                    raise
                    log.error(str(e))

        animation = presenter.animate(frame)
        for line, duration in story.render_frame_to_terminal(animation):
            log.debug(line)

    print(handler.to_html(metadata=presenter.metadata))
    return 0


def parser():
    rv = add_performance_options(
        add_common_options(
            argparse.ArgumentParser()
        )
    )
    rv.add_argument(
        "paths", nargs="+", type=pathlib.Path,
        help="Supply one or more paths to dialogue files."
    )
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
