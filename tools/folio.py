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

import textwrap

class Folio(Story):

    static_style = textwrap.dedent("""
        @page {
            size: A4;
            margin: 15mm 5mm 10mm 20mm;
            @top-center {
                content: counter(page) " / " counter(pages);
                width: 100%;
                vertical-align: bottom;
                border-bottom: .5pt solid;
                margin-bottom: .7cm;
            }
        }
        html {
            font-family: 'helvetica neue', helvetica, arial, sans-serif;
        }
        section {
            break-before: page;
        }
        table {
          table-layout: fixed;
          width: 100%;
          border-collapse: collapse;
        }

        thead th:nth-child(1) {
          width: 10%;
        }

        thead th:nth-child(2) {
          width: 65%;
        }

        thead th:nth-child(3) {
          width: 20%;
        }

        td.cue {
          border-top: #c5c5c5 dotted 1px;
        }

        tr td:nth-child(1) {
          padding: 0.5em;
          padding-left: 0.1em;
          text-align: left;
        }

        tr td:nth-child(2) {
          padding: 1.5em;
        }

        tr td:nth-child(3) {
          font-size: 0.7em;
          padding: 0 0.5em 0.5em 0.5em;
          text-align: left;
          vertical-align: top;
        }

        table caption {
          break-after: avoid;
        }

        td {
          padding: 1em 0 1em 0;
          font-family: monospace;
        }

        dt {
        clear: left;
        color: olive;
        float: left;
        font-family: "monospace";
        padding-right: 0.3em;
        text-align: right;
        text-transform:capitalize;
        width: 100px;
        }

        dt:after {
        content: ":";
        }

    """)

    @classmethod
    def render_animated_frame_to_html(cls, frame, **kwargs):
        html = super().render_animated_frame_to_html(frame)
        html =  html.replace("<main", "<section").replace("</main", "</section")
        return  html.replace("<nav", "<div").replace("</nav", "</div")

    def __init__(self, dwell, pause, **kwargs):
        super().__init__(**kwargs)
        self.dwell = dwell
        self.pause = pause
        self.sections = []

    def animate_frame(self, presenter, frame, dwell=None, pause=None):
        dwell = presenter.dwell if dwell is None else dwell
        pause = presenter.pause if pause is None else pause
        animation = presenter.animate(frame, dwell=dwell, pause=pause)
        return self.render_animated_frame_to_html(animation)

    def read(self, presenter=None, reply=None):
        presenter = self.represent(reply, previous=presenter)

        for frame in presenter.frames:
            section = self.animate_frame(presenter, frame, self.dwell, self.pause)
            self.sections.append(section)

        reply = self.context.deliver(cmd="", presenter=presenter)
        return presenter, reply

    def run(self, n=0):
        presenter, reply = None, None
        while True:
            presenter, reply = self.read(presenter, reply)

            if not n:
                break
            else:
                n -= 1

    @property
    def html(self, title="Folio"):
        style = "\n".join((
            self.render_dict_to_css(vars(self.settings)),
            self.static_style,
        ))
        return self.render_body_html(title=title, base_style="").format(
            "",
            style,
            "\n".join(self.sections)
        )

def main(args):
    log_manager = LogManager()
    log = log_manager.get_logger("main")

    if args.log_path:
        log(args.log_level, ColourAdapter(), sys.stderr)
        log.set_route(log.Level.NOTSET, LogAdapter(), args.log_path)
    else:
        log.set_route(args.log_level, ColourAdapter(), sys.stderr)

    drama = Drama()
    drama.folder = args.paths

    folio = Folio(args.dwell, args.pause, context=drama)
    folio.run(args.repeat)

    print(folio.html)

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
