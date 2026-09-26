import uvicorn

from agent.config import settings
from agent.service import app


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=settings.agent_port)


if __name__ == "__main__":
    run()
