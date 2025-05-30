from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BASE_URL: str = "https://www.ewii.dk"   
    TOKEN_ENDPOINT: str = "https://netseidbroker.mitid.dk/connect/token"
    CLIENT_ID: str = "416f6384-b429-4f71-bcbe-163e503260b1"