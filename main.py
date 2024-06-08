from colorama import Fore, Style, init
import os
import sys
import json
import time
import random
import requests
from base64 import b64decode
from multiprocessing import Process

init(autoreset=True)

class ConfigModel:
    def __init__(self, interval: int, sleep: int, min_energy: int, start_range: int, end_range: int):
        self.interval = interval
        self.sleep = sleep
        self.min_energy = min_energy
        self.start_range = start_range
        self.end_range = end_range

class Onchain:
    def __init__(self, token):
        self.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.5",
            "content-type": "application/json",
            "origin": "https://db4.onchaincoin.io",
            "referer": "https://db4.onchaincoin.io/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "te": "trailers",
        }
        self.token = token
        self.has_recovery = False

    def log(self, message, color=Fore.LIGHTWHITE_EX):
        year, mon, day, hour, minute, second, a, b, c = time.localtime()
        mon = str(mon).zfill(2)
        hour = str(hour).zfill(2)
        minute = str(minute).zfill(2)
        second = str(second).zfill(2)
        print(f"{color}[{year}-{mon}-{day} {hour}:{minute}:{second}] {message}")

    def countdown(self, t):
        while t:
            menit, detik = divmod(t, 60)
            jam, menit = divmod(menit, 60)
            jam = str(jam).zfill(2)
            menit = str(menit).zfill(2)
            detik = str(detik).zfill(2)
            print(f"waiting until {jam}:{menit}:{detik} ", flush=True, end="\r")
            t -= 1
            time.sleep(1)
        print("                          ", flush=True, end="\r")

    def parser_data(self, data):
        output = {}
        for i in unquote(data).split("&"):
            key, value = i.split("=")
            output[key] = value
        return output

    def is_expired(self):
        header, payload, sign = self.token.split(".")
        depayload = b64decode(payload + "==").decode("utf-8")
        jepayload = json.loads(depayload)
        exp = jepayload["exp"]
        now = int(time.time())
        return now > int(exp)

    def refresh_token(self):
        self.token = get_new_token()

    def get_me(self):
        headers = self.headers
        headers["authorization"] = f"Bearer {self.token}"
        try:
            res = self.http("https://db4.onchaincoin.io/api/info", headers)
            if '"success":true' in res.text:
                name = res.json()["user"]["fullName"]
                clicks = res.json()["user"]["clicks"]
                energy = res.json()["user"]["energy"]
                refill = res.json()["user"]["dailyEnergyRefill"]
                if refill >= 1:
                    self.has_recovery = True

                self.log(f"login as : {name}")
                return True

            self.log(f"failed fetch data info !, http status code : {res.status_code}", color=Fore.LIGHTRED_EX)
        except Exception as e:
            self.log(f"An error occurred during get_me: {e}", color=Fore.LIGHTRED_EX)

        return False

    def click(self, cfg: ConfigModel):
        _click = random.randint(cfg.start_range, cfg.end_range)
        data = {"clicks": _click}
        headers = self.headers
        headers["authorization"] = f"Bearer {self.token}"
        headers["content-length"] = str(len(json.dumps(data)))
        try:
            res = self.http("https://db4.onchaincoin.io/api/klick/myself/click", headers, json.dumps(data))
            if "Insufficient energy" in res.text:
                self.log("Insufficient energy", color=Fore.LIGHTYELLOW_EX)
                self.countdown(cfg.sleep)
                return True

            if '"clicks"' in res.text:
                clicks = res.json()["clicks"]
                energy = res.json()["energy"]
                coins = res.json()["coins"]
                self.log(f"total click : {clicks}")
                self.log(f"total coin : {coins}")
                self.log(f"remaining energy : {energy}")
                if cfg.min_energy >= int(energy):
                    if self.has_recovery:
                        headers["content-length"] = str(len(json.dumps({})))
                        self.http("https://db4.onchaincoin.io/api/boosts/energy", headers=headers, data=json.dumps({}))
                        self.has_recovery = False
                        return True
                    self.countdown(cfg.sleep)
                return True

            self.log(f"failed to click, http status code : {res.status_code}", color=Fore.LIGHTRED_EX)
        except Exception as e:
            self.log(f"An error occurred during click: {e}", color=Fore.LIGHTRED_EX)

        return False

    def http(self, url, headers, data=None):
        while True:
            try:
                if data is None:
                    res = requests.get(url, headers=headers)
                    open('.http_request.log','a').write(res.text + '\n')
                    return res
                res = requests.post(url, headers=headers, data=data)
                open('.http_request.log','a').write(res.text + '\n')
                return res
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.SSLError,
            ):
                self.log("connection error !", color=Fore.LIGHTRED_EX)
                time.sleep(cfg.sleep)  

def get_new_token(query_string):
    url = 'https://db4.onchaincoin.io/api/validate'
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://db4.onchaincoin.io',
        'referer': 'https://db4.onchaincoin.io/',
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    }
    data = {"hash": query_string}

    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        if response_data.get("success"):
            return response_data.get("token")
        else:
            print(f"{Fore.LIGHTRED_EX}Failed to get new token:", response_data)
            return None
    except Exception as e:
        print(f"{Fore.LIGHTRED_EX}An error occurred while getting new token:", e)
        return None

def claim_account(query_string, cfg):
    token_str = get_new_token(query_string)
    if not token_str:
        print(f"{Fore.LIGHTRED_EX}Failed to obtain a valid token for account: {query_string}")
        return

    onchain = Onchain(token_str)
    if not onchain.get_me():
        return

    while True:
        if onchain.is_expired():
            print(f"{Fore.LIGHTYELLOW_EX}Token expired, refreshing token for account: {query_string}...")
            token_str = get_new_token(query_string)
            if not token_str:
                print(f"{Fore.LIGHTRED_EX}Failed to refresh token for account: {query_string}")
                return
            onchain.token = token_str

        try:
            if not onchain.click(cfg):
                print(f"{Fore.LIGHTRED_EX}Click failed for account: {query_string}, retrying after sleep interval...")
                time.sleep(cfg.sleep)
        except Exception as e:
            print(f"{Fore.LIGHTRED_EX}An error occurred in claim_account for account: {query_string}: {e}")
            time.sleep(cfg.sleep)

        time.sleep(cfg.interval)

def main(interval, sleep, end_range):

    start_range = 1 
    if start_range > end_range:
        print(f"{Fore.LIGHTRED_EX}The value of click range end must be higher than start value!")
        sys.exit()

    cfg = ConfigModel(interval, sleep, 5, start_range, end_range)

    try:
        with open("data.txt") as f:
            account_list = f.read().splitlines()
    except FileNotFoundError:
        print(f"{Fore.LIGHTRED_EX}'data.txt' file is not found!")
        sys.exit()

    if not account_list:
        print(f"{Fore.LIGHTYELLOW_EX}No accounts found in 'data.txt' file!")
        sys.exit()

    processes = []
    for account_query in account_list:
        process = Process(target=claim_account, args=(account_query, cfg))
        process.start()
        processes.append(process)

    for process in processes:
        process.join()

if __name__ == "__main__":
    
    try:
        os.system("cls" if os.name == "nt" else "clear")
        banner = f"""{Fore.LIGHTGREEN_EX}
        ┏┓   ┓   •  
        ┃┃┏┓┏┣┓┏┓┓┏┓
        ┗┛┛┗┗┛┗┗┻┗┛┗
        """
        print(banner)
        print(f"{Fore.LIGHTCYAN_EX}ONCHAIN Auto Clicker | IM-Hanzou 2024\nGithub: https://github.com/IM-Hanzou\n")
        print(f"{Fore.LIGHTYELLOW_EX}Original Script By WINNODE\nGithub: https://github.com/Winnode\n")
        interval = int(input("Enter Click Delay: "))
        sleep = 1800
        end_range = int(input("Enter Click Max: "))
    except ValueError:
        print(f"{Fore.LIGHTRED_EX}Please enter valid number!")
        sys.exit()

    main(interval, sleep, end_range)
