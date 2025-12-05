"""AFCS 실행 진입점."""
from __future__ import annotations

from afcs.ui.app import AFCSApplication


def main():
    app = AFCSApplication()
    app.run()


if __name__ == "__main__":
    main()
