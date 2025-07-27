from fastapi import FastAPI

app = FastAPI()

# TODO: Setup CORS with .env based origins


@app.get("/healthcheck")
def health():  # TODO: Remove me
    return {"status": "Alive"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=4040, host="0.0.0.0")
