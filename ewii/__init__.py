from html import unescape
from typing import Optional

import json
import requests as re
from rich import print
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class EwiiClient:
    BASE_URL = "https://www.ewii.dk"
    LOGIN_PAGE = f"{BASE_URL}/privat/login-oidc"
    HOME_URL = f"{BASE_URL}/privat/"
    BASE_API = f"{BASE_URL}/api"            

    TOKEN_ENDPOINT = "https://netseidbroker.mitid.dk/connect/token"
    CLIENT_ID = "416f6384-b429-4f71-bcbe-163e503260b1"
    

    def __init__(self, session: Optional[re.Session] = None):
        self.session = session or re.Session()


    def _get_session(self):
        """Get the session information."""
        return self.session.cookies.get_dict()


    def _api_get(self, path: str, **params):
        r = self.session.get(f"{self.BASE_API}/{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    

    def _keep_alive(self):
        """Keep the session alive by making a request to the API."""
        self.session.get("https://www.ewii.dk/api/aftaler", timeout=15)
    

    def login(self, headless: bool = False) -> None:
        """Interactive MitID login; closes the browser on success."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            ctx = browser.new_context()
            page = ctx.new_page()

            print("[bold]Opening MitID login page…[/]")
            page.goto(self.LOGIN_PAGE, wait_until="load")
            
            page.wait_for_url(self.HOME_URL + "*")
            print("[green] Logged in - dashboard loaded[/]")

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

        if BeautifulSoup:
            soup = BeautifulSoup(html, "html.parser")
            div  = soup.find("div", class_="ewii-selfservice--context-data")
            if div is None:
                raise RuntimeError("context <div> not found in /privat HTML")
            attrs = div.attrs
        else:
            
            import re
            match = re.search(
                r'<div class="ewii-selfservice--context-data"([^>]+)>', html, re.I
            )
            if not match:
                raise RuntimeError("context <div> not found (no BeautifulSoup)")
            raw_attrs = match.group(1)
            attrs = dict(re.findall(r'data-([^=]+)="([^"]*)"', raw_attrs))

        
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