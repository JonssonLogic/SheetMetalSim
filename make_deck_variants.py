"""Generate named variants of explicit-main.k for A/B testing in LS-DYNA.

Each variant differs from the base deck by a few *CONTROL_* fields and carries
its own *TITLE, so glstat / d3hsp / messag all say which one produced them.

    python make_deck_variants.py
    python make_deck_variants.py --out "C:/Users/CV/Desktop/Forming_test/forming" \
                                 --include forming.k --endtim 0.02

Fields are addressed by (line, field) in fixed 10-character columns, and every
edit asserts the value it expects to find, so a shifted deck fails loudly
instead of silently writing to the wrong field.

Record every run in docs/test-log.md.
"""
import argparse
import io
import os

BASE = "explicit-main.k"

TITLE_LINE = 3
INCLUDE_LINE = 7
ENDTIM = (13, 1)

# field addresses, verified against the base deck
ORIEN = (24, 7)     # *CONTROL_CONTACT   - auto reorientation of contact segments
PENOPT = (24, 5)    # *CONTROL_CONTACT   - penalty stiffness option
SHLEDG = (34, 1)    # *CONTROL_CONTACT   - shell edge shape
DT2MS = (16, 5)     # *CONTROL_TIMESTEP  - mass scaling floor
MAXLVL = (73, 4)    # *CONTROL_ADAPTIVE  - adaptive refinement levels
ORIENT = (75, 7)    # *CONTROL_ADAPTIVE  - use user orientation for FORMING
ADPFREQ = (73, 1)   # *CONTROL_ADAPTIVE  - time interval between refinements

# suffix -> (title, [(addr, new value, expected current value), ...])
VARIANTS = {
    "orient": (
        "FORMING_ORIENT",
        [(ORIENT, "1", "0"), (ORIEN, "3", "0")],
    ),
    "penopt4": (
        "FORMING_PENOPT4",
        [(PENOPT, "4", "0")],
    ),
    "orient-penopt4": (
        "FORMING_ORIENT_PENOPT4",
        [(ORIENT, "1", "0"), (ORIEN, "3", "0"), (PENOPT, "4", "0")],
    ),
    # Refine the blank one level deeper (0.5 mm instead of 1 mm) so it can
    # follow a tight tool radius. DT2MS drops with it: at a 9.0e-8 floor a
    # 0.5 mm element needs no mass scaling at all, where against the current
    # 2.25e-7 floor it would carry +442%. Costs runtime, not mass.
    "refine": (
        "FORMING_REFINE",
        [(MAXLVL, "3", "2"), (DT2MS, "-1.0E-7", "-2.5E-7")],
    ),
    # Halve the adaptive interval. The punch closes 0.22 mm between checks at
    # the current setting, against ADPENE = 1.0 mm of look-ahead, so this
    # should not be the binding constraint - but it tests that directly.
    "adpfreq": (
        "FORMING_ADPFREQ",
        [(ADPFREQ, "0.00012375", "0.0002475")],
    ),
}


def set_field(lines, addr, value, expect):
    line_no, field_no = addr
    i = line_no - 1
    lo, hi = (field_no - 1) * 10, field_no * 10
    old = lines[i][lo:hi]
    if old.strip() != expect:
        raise SystemExit("line %d field %d is %r, expected %r - deck has shifted"
                         % (line_no, field_no, old.strip(), expect))
    lines[i] = lines[i][:lo] + value.rjust(10) + lines[i][hi:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".", help="where to write the variants")
    ap.add_argument("--include", help="override the *INCLUDE filename")
    ap.add_argument("--endtim", help="override *CONTROL_TERMINATION ENDTIM")
    args = ap.parse_args()

    base = io.open(BASE, encoding="utf-8").read().split("\n")
    if not os.path.isdir(args.out):
        os.makedirs(args.out)

    for suffix, (title, edits) in sorted(VARIANTS.items()):
        lines = list(base)
        for addr, value, expect in edits:
            set_field(lines, addr, value, expect)
        lines[TITLE_LINE - 1] = title
        if args.include:
            lines[INCLUDE_LINE - 1] = args.include
        if args.endtim:
            set_field(lines, ENDTIM, args.endtim, lines[ENDTIM[0] - 1][:10].strip())

        name = "explicit-main_%s.k" % suffix
        path = os.path.join(args.out, name)
        io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
        changed = ", ".join("%s=%s" % (n, v) for (n, (a, v, e)) in
                            zip(["L%d.f%d" % addr for addr, _, _ in edits],
                                edits))
        print("  %-34s  title=%-24s %s" % (name, title, changed))


if __name__ == "__main__":
    main()
