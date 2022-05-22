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
import logging
from pathlib import Path
import sys

from balladeer import Drama
from balladeer import Story
from turberfield.dialogue.cli import add_common_options
from turberfield.utils.misc import log_setup


def main(args):
    log = logging.getLogger(log_setup(args))
    drama = Drama()
    drama.folder = ["blathnaid/dlg/tale.rst"]

    story = Story(context=drama)
    presenter = story.represent()

    for frame in presenter.frames:
        animation = presenter.animate(frame)

        for line, duration in story.render_frame_to_terminal(animation):
            #print(line)
            pass

    return 0


def parser():
    rv = add_common_options(
        argparse.ArgumentParser()
    )
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
