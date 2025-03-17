import newrelic.agent
newrelic.agent.initialize('newrelic.ini')

from app.main import app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


    # 8fe21eca4872cf9d834d3559e34e0c5dFFFFNRAL

    # NRAK-0QW2J4UY7U1Q1PD4G5YSIHGA507