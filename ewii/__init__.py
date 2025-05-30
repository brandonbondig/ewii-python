import json
import logging
from html import unescape
from typing import Optional

import requests as re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from rich.logging import RichHandler

from .EwiiError import EwiiAPIError
from .Settings import Settings

settings = Settings()

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler()]
)

class EwiiClient:
    """
    Client for interacting with the EWII API.
    This client handles authentication, session management, and provides methods
    to access various endpoints of the EWII API.
    """

    def __init__(self, session: Optional[re.Session] = None):
        self.settings = settings or Settings()
        self.session = session or re.Session()
        self.BASE_URL = self.settings.BASE_URL
        self.LOGIN_PAGE = f"{self.BASE_URL}/privat/login-oidc"
        self.HOME_URL = f"{self.BASE_URL}/privat/"
        self.BASE_API = f"{self.BASE_URL}/api"
        self.timeout = 15

        self.logger = logging.getLogger(__name__)

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.BASE_API}/{path}"
        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
        except re.HTTPError as e:
            raise EwiiAPIError(f"{method} {url} failed: {e}") from e
        return resp.json()


    def _get_session(self):
        """Get the session information."""
        return self.session.cookies.get_dict()


    def _api_get(self, path: str, **params):
        """Make a GET request to the EWII API."""
        return self._request("GET", path, params=params)
    

    def _keep_alive(self):
        """Keep the session alive by making a request to the API."""
        self._request("GET", "aftaler")
    

    def login(self, headless: bool = False) -> None:
        """Interactive MitID login; closes the browser on success."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            ctx = browser.new_context()
            page = ctx.new_page()

            self.logger.info("[bold]Opening MitID login page…[/]")
            page.goto(self.LOGIN_PAGE, wait_until="load")
            
            page.wait_for_url(self.HOME_URL + "*")
            self.logger.info("[green] Logged in - dashboard loaded[/]")

            for ck in ctx.cookies(self.BASE_URL):
                self.session.cookies.set(
                    ck["name"], ck["value"], domain=ck["domain"], path=ck["path"]
                )
            browser.close()
    

    def get_consumption(self, date_from: str, date_to: str, meter_id: str):
        """Daily kWh + price between two ISO dates for *meter_id* (first meter by default)."""

        params = {
            "serviceomraade": "el",
            "interval": "P1D",
            "padding": "false",
            "maalepunktArt": "Fysisk",
            "maalepunktId": meter_id,
            "perioder[0].Start": f"{date_from}T00:00:00.000Z",
            "perioder[0].Slut": f"{date_to}T00:00:00.000Z",
        }
        return self._api_get("forbrug", **params)
    

    def get_individ_oplysninger(self):
        """Get the list of available meters."""
        return self._api_get("samtykker/00000000-0000-0000-0000-000000000000/get-individOplysninger")
    

    def get_aftaler(self):
        """Get the list of available meters."""
        return self._api_get("aftaler")


    def get_rapporter(self):
        """Get the list of available meters."""
        return self._api_get("rapporter")
    
    
    def get_info(self) -> dict:
        """
        Parse the data embedded in the HTML of the /privat page.
        """
        resp = self.session.get(f"{self.BASE_URL}/privat", timeout=15)
        resp.raise_for_status()
        html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        div  = soup.find("div", class_="ewii-selfservice--context-data")
        if div is None:
            raise RuntimeError("context <div> not found in /privat HTML")
        attrs = div.attrs

        ctx_type         = attrs.get("data-individ-context-type")
        forbrugs_raw     = attrs.get("data-individ-forbrugssteder")
        virksomheder_raw = attrs.get("data-individ-virksomheder")

        forbrugssteder = (
            json.loads(unescape(forbrugs_raw)) if forbrugs_raw and forbrugs_raw != "null" else None
        )
        virksomheder = (
            json.loads(unescape(virksomheder_raw)) if virksomheder_raw and virksomheder_raw != "null" else None
        )

        return {
            "context_type": ctx_type,
            "forbrugssteder": forbrugssteder,
            "virksomheder": virksomheder,
        }