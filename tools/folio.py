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

Usage::

    python -m tools.folio blathnaid/tale/ | weasyprint - folio.pdf

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
#  Plan for break-before break-inside break-after
#  Output is a directory, ?.html + images
#  Generate the required command for weasyprint

# 10 formatting rules:
#  1. Single spacing
#  2. Justify text to both sides
#  3. Indent first line of each paragraph (0.3")
#  4. ... except first line of chapter or scene break
#  5. Chapter headers on a new page
#  6. ... sp page break before each chapter
#  7. Chapter header begins 1/3 to 2/3 way down the page
#  8. Page numbers
#  9. Page numbers not displayed on chapter header page
# 10. Author name, Book title on opposite leaves
# 11. Drop caps or all caps/italics on chapter start?


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

        section {
        break-before: page;
        }

        blockquote {
        display: flex;
        flex-direction: row;
        }

        h1 {
        margin-bottom: 18%;
        margin-top: 28%;
        text-transform: capitalize;
        text-align: center;
        }

        .shot h2 {
        display: none;
        }

        blockquote header {
        display: none;
        }

        .line:first-of-type blockquote header {
        display: block;
        font-weight: bold;
        text-transform: capitalize;
        }

        p {
        font-family: serif;
        font-size: large;
        margin-bottom: 2rem;
        text-align: justify;
        text-indent: 3rem;
        }

        .shot:first-of-type p {
        text-indent: 0rem;
        }
    """)

    def __init__(self, dwell, pause, **kwargs):
        super().__init__(**kwargs)
        self.dwell = dwell
        self.pause = pause
        self.chapters = []
        self.metadata = {}
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
        witness = next(i.element for v in frame.values() for i in v if hasattr(i, "element"))
        dialogue = "\n".join(i for l in frame[Model.Line] for i in self.animated_line_to_html(l, **kwargs))
        stills = "\n".join(self.animated_still_to_html(i, **kwargs) for i in frame[Model.Still])
        last = frame[Model.Line][-1] if frame[Model.Line] else Presenter.Animation(0, 0, None)
        if not self.chapters or self.chapters[-1].get("scene") != frame["scene"]:
            if self.chapters:
                yield "</section>"
            metadata = {"path": witness.path, "chapter": len(self.chapters) + 1, "scene": frame["scene"]}
            self.chapters.append(metadata)
            yield from self.render_metadata(**metadata)

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
        self.log.debug(self.seconds)

    def animate_frame(self, presenter, frame, dwell=None, pause=None):
        dwell = presenter.dwell if dwell is None else dwell
        pause = presenter.pause if pause is None else pause
        animation = presenter.animate(frame, dwell=dwell, pause=pause)
        return "\n".join(self.render_animated_frame_to_html(animation))

    def render_metadata(self, **kwargs):
        yield '<section class="metadata">'
        yield "<dl>"
        metadata = dict(self.metadata, **kwargs)
        for k, v in metadata.items():
            if not v:
                continue

            yield f"<dt>{k}</dt>"
            if isinstance(v, list):
                yield from (f"<dd>{i}</dd>" for i in v)
            else:
                yield f"<dd>{v}</dd>"
        yield "</dl>"
        yield "</section>"

    def read(self, presenter=None, reply=None):
        presenter = self.represent(reply, previous=presenter)
        self.metadata.update(presenter.metadata)

        for frame in presenter.frames:
            section = self.animate_frame(presenter, frame, self.dwell, self.pause)
            self.sections.append(section)
        self.sections[-1] += "\n</section>"

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
    def css(self):
        return  "\n".join((
            self.render_dict_to_css(vars(self.settings)),
            self.static_style,
        ))

    def render_html(self, links=[], style="", sections=[]):
        title = next(iter(self.metadata.get("title", [self.__class__.__name__])), self.__class__.__name__)
        return self.render_body_html(title=title, base_style="").format(
            "\n".join(links), style, "\n".join(sections)
        )


class TypeGetter:

    def __init__(self, paths):
        self.paths = [i for p in paths for i in (p.iterdir() if p.is_dir() else [p])]
        self.log = LogManager().get_logger("main").clone("getter")
        for p, t in zip(self.paths, map(self.guess_type, self.paths)):
            if t[0]:
                self.log.info(f"Recognized {p} as type {t[0]}")
            else:
                self.log.warning(f"Unrecognized file type: {p}")

    @staticmethod
    def guess_type(path):
        if str(path).endswith(".rst"):
            return ("text/x-rst", None)
        else:
            return mimetypes.guess_type(path, strict=False)

    @property
    def css(self):
        return [p for p in self.paths if self.guess_type(p)[0] == "text/css"]

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

    getter = TypeGetter(args.paths)

    drama = Drama()
    drama.folder = getter.rst

    folio = Folio(args.dwell, args.pause, context=drama)

    folio.run(args.repeat)

    if args.css:
        print(folio.css)
    else:
        style = "\n".join([p.read_text() for p in getter.css]) or folio.css
        print(folio.render_html(style=style, sections=folio.sections))

    return 0


def parser():
    rv = add_performance_options(
        add_common_options(
            argparse.ArgumentParser()
        )
    )
    rv.add_argument(
        "--css", default=False, action="store_true",
        help="Emit internal styles as CSS."
    )
    rv.add_argument(
        "paths", nargs="*", type=pathlib.Path,
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
