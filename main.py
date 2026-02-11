from fastapi import FastAPI
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI(title="Global Market & Portfolio Risk API")

@app.get("/")
def health():
    return {"status": "API is alive"}
