import uvicorn

from agent.service import app


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
