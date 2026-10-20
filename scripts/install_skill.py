"""Copy the public skill package to an explicit new directory."""
import argparse
from pathlib import Path
import shutil
import sys

from check_package import check

ROOT = Path(__file__).resolve().parents[1]


def install(destination):
    destination = Path(destination).expanduser()
    resolved = destination.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError('Choose a destination outside the source package.')
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination already exists; choose a new directory.')
    if check():
        raise ValueError('Package validation failed; no installation was created.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    try:
        for source in ROOT.iterdir():
            if source.name.startswith('.') or source.name == '__pycache__':
                continue
            if source.is_dir():
                shutil.copytree(source, destination / source.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                shutil.copy2(source, destination / source.name)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    try:
        print('Installed: ' + str(install(args.destination)))
        return 0
    except (ValueError, OSError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
