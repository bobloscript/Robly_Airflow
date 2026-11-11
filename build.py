#!/usr/bin/env python3
"""Builds Source.luau from the library part of Example.luau.

Strips comments and whitespace; names are left as they are, so the output
is the same program token for token. Usage: build.py Example.luau Source.luau
"""
import re, sys

NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
NUMBER = re.compile(r'0[xX][0-9a-fA-F_]+|0[bB][01_]+|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?')
LONG_OPEN = re.compile(r'\[(=*)\[')
OPS = ['...', '..=', '//=', '..', '==', '~=', '<=', '>=', '::', '->', '+=', '-=', '*=', '/=', '%=', '^=', '//']

def tokenize(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in ' \t\r\n':
            i += 1
            continue
        if src.startswith('--', i):
            m = LONG_OPEN.match(src, i + 2)
            if m:
                end = src.index(']' + m.group(1) + ']', m.end())
                i = end + len(m.group(1)) + 2
            else:
                j = src.find('\n', i)
                i = n if j < 0 else j
            continue
        m = LONG_OPEN.match(src, i)
        if m:
            end = src.index(']' + m.group(1) + ']', m.end()) + len(m.group(1)) + 2
            out.append(('str', src[i:end]))
            i = end
            continue
        if c in '"\'':
            j = i + 1
            while src[j] != c:
                if src[j] == '\n':
                    raise SyntaxError('unfinished string at %d' % i)
                j += 2 if src[j] == '\\' else 1
            out.append(('str', src[i:j + 1]))
            i = j + 1
            continue
        if c == '`':
            raise SyntaxError('interpolated strings are not supported by this build script (offset %d)' % i)
        m = NAME.match(src, i)
        if m:
            out.append(('word', m.group()))
            i = m.end()
            continue
        if c.isdigit() or (c == '.' and i + 1 < n and src[i + 1].isdigit()):
            m = NUMBER.match(src, i)
            out.append(('word', m.group()))
            i = m.end()
            continue
        for op in OPS:
            if src.startswith(op, i):
                out.append(('op', op))
                i += len(op)
                break
        else:
            out.append(('op', c))
            i += 1
    return out

_pairs = {}
def needs_space(a, b):
    (ka, ta), (kb, tb) = a, b
    if ka == 'str' or kb == 'str':
        # "[" before a long string would read as a deeper long bracket.
        return ta.endswith('[') and tb.startswith('[')
    if ka == 'word' and kb == 'word':
        # Names, keywords and numbers always need a gap: Luau reads "5and" as one bad number.
        return True
    key = (ta, tb)
    if key not in _pairs:
        try:
            _pairs[key] = [t for _, t in tokenize(ta + tb)] != [ta, tb]
        except Exception:
            _pairs[key] = True
    return _pairs[key]

def minify(src):
    tokens = tokenize(src)
    parts = []
    for index, token in enumerate(tokens):
        if index and needs_space(tokens[index - 1], token):
            parts.append(' ')
        parts.append(token[1])
    return ''.join(parts), tokens

def main(example, target):
    src = open(example, encoding='utf8').read()
    marker = '\nend)()\n'
    cut = src.index(marker) + len(marker)
    lib = src[:cut]
    assert lib.startswith('-- The library lives') or 'local Library = (function()' in lib[:400]
    out, tokens = minify(lib)
    out += ' return Library\n'
    # The build must read back as the same tokens.
    again = tokenize(out)
    assert again[:len(tokens)] == tokens, 'minified output does not match the source'
    open(target, 'w', encoding='utf8', newline='\n').write(out)
    print('%s: %d bytes from %d (%d tokens)' % (target, len(out.encode()), len(lib.encode()), len(tokens)))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
