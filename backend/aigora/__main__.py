"""Run the backend: `uv run aigora` (or `python -m aigora`)."""

import os

import uvicorn


def main() -> None:
    host = os.environ.get("AIGORA_HOST", "127.0.0.1")
    port = int(os.environ.get("AIGORA_PORT", "8765"))
    uvicorn.run("aigora.app:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    main()
