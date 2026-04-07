from __future__ import annotations

import uvicorn

from dharma_shield.server import app


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
