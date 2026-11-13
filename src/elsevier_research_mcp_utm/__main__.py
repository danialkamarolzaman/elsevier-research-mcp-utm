import sys

from . import __version__

usage = '''usage: elsevier-research-mcp-utm [mode]

modes:
  serve     run the MCP server on stdio (default)
  doctor    check API key, access tier, quota and download limits
  version   print the version
'''


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'serve'
    if mode == 'serve':
        from .server import mcp
        mcp.run()
    elif mode == 'doctor':
        from . import doctor
        report = doctor.run()
        print(doctor.text(report))
        sys.exit(0 if report['api_key_valid'] else 1)
    elif mode in ('version', '--version', '-V'):
        print(__version__)
    elif mode in ('help', '--help', '-h'):
        print(usage)
    else:
        print(f'unknown mode: {mode}\n\n{usage}')
        sys.exit(2)


if __name__ == '__main__':
    main()
