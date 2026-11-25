"""Entry point: run the GHOSTPATH X API on 127.0.0.1:8000 (lab only).

GHOSTPATH X v0.2.0 — Autonomous Attack-Path Discovery & Exploit Validation,
by Adarsh. Tagline: "Follow the ghost. Prove the path."
"""

import uvicorn

from core.config import settings


def main() -> None:
    print("GHOSTPATH X v0.2.0 — by Adarsh")
    print("Follow the ghost. Prove the path.")
    print(f"Lab API: http://{settings.host}:{settings.port} (isolated lab only)")
    uvicorn.run(
        "apps.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
