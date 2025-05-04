from fastapi import FastAPI

from app.utils.structlogger import logger

app = FastAPI()


@app.get("/")
def read_root() -> dict[str, str]:
    logger.info("Hello, World!")
    return {"message": "Hello, World!"}
