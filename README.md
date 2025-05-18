# ewii-python

Unofficial client for Denmark’s **EWII** self-service portal

Query meters, daily kWh, contracts, and more from Python or expose them through a webserver.

## 📚 Public methods

| Method                                | Description                                                           |
| ------------------------------------- | --------------------------------------------------------------------- |
| `login(headless=False)`               | Interactive MitID login; copies cookies into your `requests.Session`. |
| `get_consumption(from, to, meter_id)` | Array of daily kWh values.                                              |
| `get_individ_oplysninger()`           | Personal/identity data.                                               |
| `get_aftaler()`                       | Active contracts.                                                     |
| `get_info()`                          | Hidden JSON blob from `/privat` (addresses, meters, etc.).            |
| `_keep_alive()`                       | Lightweight ping to keep cookies fresh.                               |

---

## 📦 Installation

```bash
pip install ewii
playwright install chromium
```

---

## Script example

```python
import json, requests
from datetime import date
from ewii import EwiiClient

client = EwiiClient()
client.login(headless=True)

info = client.get_info()
meter = info["forbrugssteder"][0]["maalepunkter"][0]["maalepunktId"]

today = date.today(); first = today.replace(day=1)
print(client.get_consumption(first.isoformat(), today.isoformat(), meter))
```

---

## 🌐 Minimal FastAPI webserver
Create a python file called `app.py`
```python
import json, threading, requests
from datetime import date
from fastapi import FastAPI, Query, HTTPException
from ewii import EwiiClient

KEEP_ALIVE_TIMER = 30
stop = threading.Event()
client = EwiiClient(requests.Session())

def keep_alive(evt):
    while not evt.wait(KEEP_ALIVE_TIMER):
        try:
            client._keep_alive()
            print("keep-alive")
        except Exception as e:
            print(e)

app = FastAPI(title="EWII API")

@app.on_event("startup")
def start():
    threading.Thread(target=keep_alive, args=(stop,), daemon=True).start()

@app.on_event("shutdown")
def done():
    stop.set()

@app.get("/consumption")
def consumption(meter_id: str, date_from: date, date_to: date):
    try:
        return client.get_consumption(date_from.isoformat(),
                                      date_to.isoformat(),
                                      meter_id)
    except Exception as e:
        raise HTTPException(502, str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive Swagger UI. The background thread pings EWII every 5 minutes so the session stays alive.

---


> **Note**  This library is **unofficial** and not affiliated with EWII. Use responsibly and respect EWII’s terms of service.
