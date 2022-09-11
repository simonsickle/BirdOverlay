import datetime
from dateutil import parser as date
import json
import requests
import time
import os
from dotenv import load_dotenv

class Owlet:
    def __init__(self):
        """Initialize API Token."""
        load_dotenv()
        
        self.__client = requests.session()
        self.__JWT = ""
        self.__MINI_TOKEN = ""
        self.__OWLET_USER = str(os.getenv('USER_EMAIL'))
        self.__OWLET_PASS = str(os.getenv('USER_PASS'))
        self.__OWLET_REGION = "world"
        self.__OWLET_TOKEN = None
        self.__OWLET_REGION_CONFIG = {
            "world": {
                "url_mini": "https://ayla-sso.owletdata.com/mini/",
                "url_signin": "https://user-field-1a2039d9.aylanetworks.com/api/v1/token_sign_in",
                "url_base": "https://ads-field-1a2039d9.aylanetworks.com/apiv1",
                "apiKey": "AIzaSyCsDZ8kWxQuLJAMVnmEhEkayH1TSxKXfGA",
                "app_id": "sso-prod-3g-id",
                "app_secret": "sso-prod-UEjtnPCtFfjdwIwxqnC0OipxRFU",
            },
            "europe": {
                "url_mini": "https://ayla-sso.eu.owletdata.com/mini/",
                "url_signin": "https://user-field-eu-1a2039d9.aylanetworks.com/api/v1/token_sign_in",
                "url_base": "https://ads-field-eu-1a2039d9.aylanetworks.com/apiv1",
                "apiKey": "AIzaSyDm6EhV70wudwN3iOSq3vTjtsdGjdFLuuM",
                "app_id": "OwletCare-Android-EU-fw-id",
                "app_secret": "OwletCare-Android-EU-JKupMPBoj_Npce_9a95Pc8Qo0Mw",
            },
        }
        self.__API_KEY = self.__OWLET_REGION_CONFIG[self.__OWLET_REGION]["apiKey"]
        self.__API_URL = self.__OWLET_REGION_CONFIG[self.__OWLET_REGION]["url_base"]
        self.__OWLET_TOKEN_EXPIRE_TIME = None
        self.__OWLET_TOKEN_REAUTH_ATTEMPTS = 0
        self.__OWLET_TOKEN_REAUTH_MAX_ATTEMPTS = 5
        self.__OWLET_TOKEN = self.authenticate()
        self.__devices = None
        self.__token = None

    def authenticate(self, reauthenticate=False):
        # authenticate against Firebase, get the JWT.
        # need to pass the X-Android-Package and X-Android-Cert headers because
        # the API key is restricted to the Owlet Android app
        # https://cloud.google.com/docs/authentication/api-keys#api_key_restrictions
        if reauthenticate:
            if (
                self.__OWLET_TOKEN_REAUTH_ATTEMPTS
                <= self.__OWLET_TOKEN_REAUTH_MAX_ATTEMPTS
            ):
                self.__OWLET_TOKEN_REAUTH_ATTEMPTS = (
                    self.__OWLET_TOKEN_REAUTH_ATTEMPTS + 1
                )
                self.__OWLET_TOKEN_REAUTH_RESET_TIMER = time.time() + 1800
            elif time.time() >= self.__OWLET_TOKEN_REAUTH_RESET_TIMER:
                self.__OWLET_TOKEN_REAUTH_ATTEMPTS = 1
            else:
                return self.__OWLET_TOKEN, None
        try:
            r = requests.post(
                f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={self.__API_KEY}",
                data=json.dumps(
                    {
                        "email": self.__OWLET_USER,
                        "password": self.__OWLET_PASS,
                        "returnSecureToken": True,
                    }
                ),
                headers={
                    "X-Android-Package": "com.owletcare.owletcare",
                    "X-Android-Cert": "2A3BC26DB0B8B0792DBE28E6FFDC2598F9B12B74",
                },
            )
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            #_LOGGER.error("Owlet API Could not Authenticate against Firebase: %s" % e)
            return False, e
        self.__JWT = r.json()["idToken"]
        # authenticate against owletdata.com, get the mini_token
        try:
            r = requests.get(
                self.__OWLET_REGION_CONFIG[self.__OWLET_REGION]["url_mini"],
                headers={"Authorization": self.__JWT},
            )
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            #_LOGGER.error(
            #    "Owlet API Could not Authenticate against owletdata.com: %s" % e
            #)
            return False, e
        self.__MINI_TOKEN = r.json()["mini_token"]
        # authenticate against Ayla, get the access_token
        try:
            r = requests.post(
                self.__OWLET_REGION_CONFIG[self.__OWLET_REGION]["url_signin"],
                json={
                    "app_id": self.__OWLET_REGION_CONFIG[self.__OWLET_REGION]["app_id"],
                    "app_secret": self.__OWLET_REGION_CONFIG[self.__OWLET_REGION][
                        "app_secret"
                    ],
                    "provider": "owl_id",
                    "token": self.__MINI_TOKEN,
                },
            )
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            #_LOGGER.error("Owlet API Could not Authenticate against Firebase: %s" % e)
            return False, e
        self.__OWLET_TOKEN = r.json()["access_token"]
        # we will re-auth 60 seconds before the token expires
        self.__OWLET_TOKEN_EXPIRE_TIME = time.time() + r.json()["expires_in"] - 60
        #_LOGGER.info("Owlet API Token for %s acquired" % self.__OWLET_USER)
        return self.__OWLET_TOKEN, None

    def api_get(self, route):
        return self.__client.get(
            self.__API_URL + route,
            headers={"Authorization": "auth_token " + self.__OWLET_TOKEN},
        )

    def api_post(self, route, json_body):
        return self.__client.post(
            self.__API_URL + route,
            json=json_body,
            headers={"Authorization": "auth_token " + self.__OWLET_TOKEN},
        )

    @property
    def token(self):
        if (
            (self.__OWLET_TOKEN is None)
            or (self.__OWLET_TOKEN_EXPIRE_TIME is None)
            or (time.time() >= self.__OWLET_TOKEN_EXPIRE_TIME)
        ):
            return False
        return True

    def get_devices(self):
        try:
            # _LOGGER.info("Getting list of Owlet Devices")
            r = self.api_get("/devices.json")
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            # _LOGGER.error("Owlet Network error while retrieving devices: %s" % e)
            time.sleep(5)
            self.__client = requests.session()
            return []
        self.__devices = r.json()
        self.__device_serial_numbers = []
        if len(self.__devices) < 1:
            print("No owlet smart sock")
            #_LOGGER.info("No Owlet Smart Sock Found")
        # Allow for multiple devices
        else:
            for device in self.__devices:
                if device["device"]["dsn"] not in self.__device_serial_numbers:
                    self.__device_serial_numbers.append(device["device"]["dsn"])
                    #_LOGGER.info(
                    #    "Found Owlet Smart Sock with Serial Number %s"
                    #    % device["device"]["dsn"]
                    #)
        return self.__device_serial_numbers

    @property
    def devices(self):
        if self.__devices is None or self.__device_serial_numbers is None:
            self.get_devices()
        return self.__device_serial_numbers

    def activate_sock(self, dsn):
        try:
            r = self.api_post(
                "/dsns/%s/properties/APP_ACTIVE/datapoints.json" % dsn,
                {"datapoint": {"metadata": {}, "value": 1}},
            )
            r.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            #_LOGGER.error("Owlet Network error while activating Sock %s: %s" % (dsn, e))
            time.sleep(5)
            self.__client = requests.session()
            return False

    def sock_properties(self, dsn):
        if self.activate_sock(dsn):
            device_props = {"DSN": dsn}
            try:
                r = self.api_get("/dsns/%s/properties.json" % dsn)
                timestamp = datetime.date.today().isoformat()
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                #_LOGGER.error(
                #    "Owlet Network error while retrieving data for Sock %s: %s"
                #    % (dsn, e)
                #)
                time.sleep(5)
                self.__client = requests.session()
                return False, False
            response_body = r.json()
            #_LOGGER.error("OWLET: %s" % json.dumps(r.json()))
            for prop in response_body:
                device_props[prop["property"]["name"]] = prop["property"]
            return device_props, timestamp
        else:
            return False, False

    def vitals(self, dsn):
        p, timestamp = self.sock_properties(dsn)
        if p is not False:
            if "REAL_TIME_VITALS" in p:
                # Sock is a Smart Sock 3
                rt_vitals = json.loads(p["REAL_TIME_VITALS"]["value"])
                return {
                    "dsn": p["DSN"],
                    "charge_status": rt_vitals["chg"],
                    "heart_rate": "%d" % rt_vitals["hr"],
                    "base_station_on": rt_vitals["bso"],
                    "oxygen_saturation": "%d" % rt_vitals["ox"],
                    "movement": "%d" % rt_vitals["mv"],
                    "battery": "%d" % rt_vitals["bat"],
                    "ble_rssi": "%d" % rt_vitals["rsi"],
                    "LOW_INTEG_READ": bool(p["LOW_INTEG_READ"]["value"]),
                    "LOW_BATT_ALRT": bool(p["LOW_BATT_ALRT"]["value"]),
                    "HIGH_HR_ALRT": bool(p["HIGH_HR_ALRT"]["value"]),
                    "LOW_HR_ALRT": bool(p["LOW_HR_ALRT"]["value"]),
                    "LOW_OX_ALRT": bool(p["LOW_OX_ALRT"]["value"]),
                    "DISCOMFORT_ALRT": bool(p["DISCOMFORT_ALRT"]["value"]),
                    "SOCK_DISCON_ALRT": bool(p["SOCK_DISCON_ALRT"]["value"]),
                    "PREVIEW_LOW_PRIORITY_ALARM": bool(p["PREVIEW_LOW_PRIORITY_ALARM"]["value"]),
                    "PREVIEW_HIGH_PRIORITY_ALARM": bool(p["PREVIEW_HIGH_PRIORITY_ALARM"]["value"]),
                    "PREVIEW_MED_PRIORITY_ALARM": bool(p["PREVIEW_MED_PRIORITY_ALARM"]["value"]),
                    "RED_ALERT_SUMMARY": "%s" % p["RED_ALERT_SUMMARY"]["value"],
                    "ts": date.parse(p["REAL_TIME_VITALS"]["data_updated_at"]),
#                    "rt_vitals": rt_vitals,
                    "error": False,
                }, p
            elif "CHARGE_STATUS" in p:
                # Sock is a Smart Sock 2
                return {
                    "dsn": p["DSN"],
                    "charge_status": p["CHARGE_STATUS"]["value"],
                    "heart_rate": "%d" % p["HEART_RATE"]["value"],
                    "base_station_on": p["BASE_STATION_ON"]["value"],
                    "oxygen_saturation": "%d" % p["OXYGEN_LEVEL"]["value"],
                    "movement": "%d" % p["MOVEMENT"]["value"],
                    "battery": "%d" % p["BATT_LEVEL"]["value"],
                    "ble_rssi": "%d" % p["BLE_RSSI"]["value"],
                    "LOW_INTEG_READ": bool(p["LOW_INTEG_READ"]["value"]),
                    "LOW_BATT_ALRT": bool(p["LOW_BATT_ALRT"]["value"]),
                    "HIGH_HR_ALRT": bool(p["HIGH_HR_ALRT"]["value"]),
                    "LOW_HR_ALRT": bool(p["LOW_HR_ALRT"]["value"]),
                    "LOW_OX_ALRT": bool(p["LOW_OX_ALRT"]["value"]),
                    "SOCK_DISCON_ALRT": bool(p["SOCK_DISCON_ALRT"]["value"]),
                    "RED_ALERT_SUMMARY": "",
                    "error": False,
                }, p
        return {"dsn": dsn, "error": True}, p