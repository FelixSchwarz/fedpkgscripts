
import sys

try:
    import colorama
except ImportError:
    sys.stderr.write('please install python3-colorama\n')
    sys.exit(1)

__all__ = ['colorama_color']

# -----------------------------------------------------------------------------
# https://github.com/tartley/colorama/pull/141
import contextlib

_Fore   = colorama.ansi.AnsiFore()
_Back   = colorama.ansi.AnsiBack()
_Style  = colorama.ansi.AnsiStyle()

fore_values = set(_Fore.__dict__.values())
back_values = set(_Back.__dict__.values())
style_values = set(_Style.__dict__.values())

fore_stack = [_Fore.RESET]
back_stack = [_Back.RESET]
style_stack = [_Style.NORMAL]


# FS: This code seems to be buggy when using background colors.
@contextlib.contextmanager
def colorama_color(*args):
    for arg in args:
        print(arg, end='');
        if arg in fore_values:
            fore_stack.append(arg)
        elif arg in back_values:
            back_stack.append(arg)
        elif arg in style_values:
            style_stack.append(arg)
    yield
    for arg in reversed(args):
        # review comment from @wiggin15
        # I think we don't need this loop. If we pass more than one Fore value,
        # for example, we are going to print the colors in reverse (except the
        # first one), but we don't need to print any color codes after the text
        # has been written. The reason this code works is because the stacks
        # always end with a reset - so all we need to do after the yield is
        # print the reset codes, or only print Style.RESET_ALL.
        if arg == fore_stack[-1]:
            fore_stack.pop()
            print(fore_stack[-1], end='')
        elif arg == back_stack[-1]:
            back_stack.pop()
            print(back_stack[-1], end='')
        elif arg == style_stack[-1]:
            style_stack.pop()
            print(style_stack[-1], end='')
# -----------------------------------------------------------------------------

