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
import mimetypes
import pathlib
import sys

from balladeer import Drama
from balladeer import Story
from turberfield.dialogue.adapters import ColourAdapter
from turberfield.dialogue.cli import add_common_options
from turberfield.dialogue.cli import add_performance_options
from turberfield.dialogue.main import HTMLHandler
from turberfield.dialogue.model import Model
from turberfield.utils.logger import LogAdapter
from turberfield.utils.logger import LogManager

import textwrap

# TODO
#  Format images
#  Prepend sections from .html files
#  Create metadata links from producer.metadata
#  Plan for break-before break-inside break-after
#  Insert CSS
#  Output is a directory, ?.html + images
#  Generate the required command for weasyprint


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

    def __init__(self, dwell, pause, **kwargs):
        super().__init__(**kwargs)
        self.dwell = dwell
        self.pause = pause
        self.chapters = []
        self.sections = []
        self.seconds = 0
        lm = LogManager()
        self.log = lm.clone(lm.get_logger("main"), "folio")

    def animated_line_to_html(self, anim, **kwargs):
        name = getattr(anim.element.persona, "name", anim.element.persona)
        name = "{0.firstname} {0.surname}".format(name) if hasattr(name, "firstname") else name
        delay = self.seconds + anim.delay
        duration = self.seconds + anim.duration
        yield f'<div class="line" style="animation-delay: {delay:.2f}s; animation-duration: {duration:.2f}s">'
        if name:
            yield "<blockquote>"
            yield f"<header>{name}</header>"
            yield f"{anim.element.html}".rstrip()
            yield "</blockquote>"
        else:
            yield f"{anim.element.html}".rstrip()
        yield "</div>"

    def render_animated_frame_to_html(self, frame, controls=[], **kwargs):
        dialogue = "\n".join(i for l in frame[Model.Line] for i in self.animated_line_to_html(l, **kwargs))
        stills = "\n".join(self.animated_still_to_html(i, **kwargs) for i in frame[Model.Still])
        last = frame[Model.Line][-1] if frame[Model.Line] else Presenter.Animation(0, 0, None)
        if not self.chapters or self.chapters[-1] != frame["scene"]:
            if self.chapters:
                yield "</section>"
            self.chapters.append(frame["scene"])

            yield '<section class="scene">'
            yield f"<h1>{frame['scene']}</h1>"
            yield '<div class="shot">'
            yield f"<h2>{frame['name']}</h2>"
            if stills.strip():
                yield f"{stills}"
            yield f"{dialogue}"
            yield "</div>"
        else:
            yield '<div class="shot">'
            yield f"<h2>{frame['name']}</h2>"
            if stills.strip():
                yield f"{stills}"
            yield f"{dialogue}"
            yield "</div>"

        self.seconds += last.duration
        self.log.info(self.seconds)

    def animate_frame(self, presenter, frame, dwell=None, pause=None):
        dwell = presenter.dwell if dwell is None else dwell
        pause = presenter.pause if pause is None else pause
        animation = presenter.animate(frame, dwell=dwell, pause=pause)
        return "\n".join(self.render_animated_frame_to_html(animation))

    def read(self, presenter=None, reply=None):
        presenter = self.represent(reply, previous=presenter)

        for frame in presenter.frames:
            section = self.animate_frame(presenter, frame, self.dwell, self.pause)
            self.sections.append(section)

        reply = self.context.deliver(cmd="", presenter=presenter)
        return presenter, reply

    def run(self, n=0):
        presenter, reply = None, None
        while self.context.folder:
            presenter, reply = self.read(presenter, reply)

            if not n:
                break
            else:
                n -= 1
        else:
            self.log.warning("Folder is empty")

    @property
    def html(self, title="Folio"):
        style = "\n".join((
            self.render_dict_to_css(vars(self.settings)),
            self.static_style,
        ))
        return self.render_body_html(title=title, base_style="").format(
            "",
            style,
            "\n".join(self.sections + ["</section>"])
        )

class TypeSetter:

    def __init__(self, paths):
        self.paths = [i for p in paths for i in (p.iterdir() if p.is_dir() else [p])]

    @staticmethod
    def guess_type(path):
        if str(path).endswith(".rst"):
            return ("text/x-rst", None)
        else:
            return mimetypes.guess_type(path, strict=False)

    @property
    def rst(self):
        return [p for p in self.paths if self.guess_type(p)[0] == "text/x-rst"]


def main(args):
    log = LogManager().get_logger("main")

    if args.log_path:
        log(args.log_level, ColourAdapter(), sys.stderr)
        log.set_route(log.Level.NOTSET, LogAdapter(), args.log_path)
    else:
        log.set_route(args.log_level, ColourAdapter(), sys.stderr)

    setter = TypeSetter(args.paths)

    drama = Drama()
    drama.folder = setter.rst

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
