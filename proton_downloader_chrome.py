import os
import time
import random 
import glob 
import json 
import zipfile 
import requests 
import re 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# --- Constants ---
MODAL_BACKDROP_SELECTOR = (By.CLASS_NAME, "modal-two-backdrop")
CONFIRM_BUTTON_SELECTOR = (By.CSS_SELECTOR, ".button-solid-norm:nth-child(2)")
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloaded_configs")
SERVER_ID_LOG_FILE = os.path.join(os.getcwd(), "downloaded_wg_ids.json") 
MAX_DOWNLOADS_PER_SESSION = 20 
RELOGIN_DELAY = 120 

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

class ProtonVPN:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        
        prefs = {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True 
        }
        self.options.add_experimental_option("prefs", prefs)
        self.driver = None

    def setup(self):
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.set_window_size(1936, 1048)
        self.driver.implicitly_wait(10)
        print("WebDriver initialized.")

    def teardown(self):
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")

    def load_downloaded_ids(self):
        if os.path.exists(SERVER_ID_LOG_FILE):
            try:
                with open(SERVER_ID_LOG_FILE, 'r') as f:
                    return set(json.load(f))
            except json.JSONDecodeError:
                return set()
        return set()

    def save_downloaded_ids(self, ids):
        with open(SERVER_ID_LOG_FILE, 'w') as f:
            json.dump(list(ids), f)
            
    def login(self, username, password):
        try:
            self.driver.get("https://protonvpn.com/")
            time.sleep(1) 
            self.driver.find_element(By.XPATH, "//a[contains(@href, 'https://account.protonvpn.com/login')]").click()
            time.sleep(1) 
            self.driver.find_element(By.ID, "username").send_keys(username)
            time.sleep(1) 
            self.driver.find_element(By.CSS_SELECTOR, ".button-large").click()
            time.sleep(1) 
            self.driver.find_element(By.ID, "password").send_keys(password)
            time.sleep(1) 
            self.driver.find_element(By.CSS_SELECTOR, ".button-large").click()
            time.sleep(3) 
            print("Login Successful.")
            return True
        except Exception as e:
            print(f"Error Login: {e}")
            return False

    def navigate_to_downloads(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".navigation-item:nth-child(7) .text-ellipsis"))
            ).click()
            time.sleep(2) 
            return True
        except Exception as e:
            print(f"Error Navigating to Downloads: {e}")
            return False

    def logout(self):
        try:
            self.driver.get("https://account.protonvpn.com/logout") 
            time.sleep(1) 
            return True
        except Exception:
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".p-1").click()
                time.sleep(1)
                self.driver.find_element(By.CSS_SELECTOR, ".mb-4 > .button").click()
                time.sleep(1) 
                return True
            except:
                return False

    def process_wireguard_downloads(self, downloaded_ids):
        print("\n--- Starting WireGuard Download Session ---")
        try:
            self.driver.execute_script("window.scrollTo(0,0)")
            time.sleep(1) 
            
            # Click WireGuard Tab
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".flex:nth-child(4) > .mr-8:nth-child(1) > .relative"))).click()
            time.sleep(2) 
            
            # Click Platform (Selecting the 3rd option)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".flex:nth-child(4) > .mr-8:nth-child(3) .radio-fakeradio"))).click()
            time.sleep(2)
            
            countries = self.driver.find_elements(By.CSS_SELECTOR, ".mb-6 details")
            download_counter = 0
            
            for country in countries:
                try:
                    country_name = country.find_element(By.CSS_SELECTOR, "summary").text.split('\n')[0].strip()
                    if download_counter >= MAX_DOWNLOADS_PER_SESSION:
                        print(f"Session limit ({MAX_DOWNLOADS_PER_SESSION}) reached.")
                        return False, downloaded_ids
                    
                    self.driver.execute_script("arguments[0].open = true;", country)
                    time.sleep(0.5)
                    rows = country.find_elements(By.CSS_SELECTOR, "tr")
                    all_configs_in_country_downloaded = True 

                    for row in rows[1:]: 
                        try:
                            server_id = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
                            if server_id in downloaded_ids: continue
                            
                            all_configs_in_country_downloaded = False
                            if download_counter >= MAX_DOWNLOADS_PER_SESSION: return False, downloaded_ids
                            
                            btn = row.find_element(By.CSS_SELECTOR, ".button")
                            
                            random_delay = random.randint(60, 90)
                            
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.5)
                            ActionChains(self.driver).move_to_element(btn).click().perform()
                            WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable(CONFIRM_BUTTON_SELECTOR)).click()
                            WebDriverWait(self.driver, 30).until(EC.invisibility_of_element_located(MODAL_BACKDROP_SELECTOR))
                            
                            download_counter += 1
                            print(f"[WG] Downloaded {server_id}. Waiting {random_delay}s...")
                            time.sleep(random_delay) 
                            downloaded_ids.add(server_id)
                        except Exception: continue 
                            
                    if all_configs_in_country_downloaded:
                        print(f"[WG] All configs for {country_name} done.")
                except Exception: continue
        except Exception as e: print(f"WG Loop Error: {e}")
        return True, downloaded_ids

    def organize_and_send_files(self):
        print("\n###################### Organizing and Sending Files ######################")
        
        wg_files = {} 

        # 1. Parse and Sort Files
        for filename in os.listdir(DOWNLOAD_DIR):
            if not filename.endswith(".conf"):
                continue

            file_path = os.path.join(DOWNLOAD_DIR, filename)
            
            name_no_ext = filename.rsplit('.', 1)[0]
            clean_name = re.sub(r'\s*\(\d+\)$', '', name_no_ext).strip().lower() 
            
            country_code = 'OTHER'

            # WireGuard Parsing Logic
            prefix = clean_name.replace("wg-", "")
            code = prefix.split('-')[0].split('#')[0].upper()
            if len(code) == 2 and code.isalpha():
                country_code = code
            
            if country_code not in wg_files: wg_files[country_code] = []
            wg_files[country_code].append(file_path)

        if not wg_files:
            print("No WireGuard files found.")
            return

        # 2. Create Single ZIP
        total_files = sum(len(v) for v in wg_files.values())
        print(f"Preparing Zip: {total_files} files across {len(wg_files)} countries.")
        
        zip_filename = "ProtonVPN_WireGuard_Configs.zip"
        zip_path = os.path.join(os.getcwd(), zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for country, files in wg_files.items():
                for file_path in files:
                    archive_name = os.path.join(country, os.path.basename(file_path))
                    zipf.write(file_path, arcname=archive_name)

        # 3. Send to Telegram (English Caption)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            caption = (
                f"✅ **New ProtonVPN WireGuard Bundle**\n\n"
                f"📂 **Structure:** Organized by Country Folders\n"
                f"🌍 **Countries:** {len(wg_files)}\n"
                f"📄 **Total Files:** {total_files}\n"
                f"ℹ️ **Format:** .conf (Windows/Router/Clients)\n\n"
                f"🔹 Files are sorted into folders inside the ZIP."
            )
            
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
                with open(zip_path, 'rb') as doc:
                    requests.post(url, 
                        data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, 
                        files={'document': doc}
                    )
                print(f"Sent {zip_filename} to Telegram.")
            except Exception as e:
                print(f"Telegram Error: {e}")
        
        # NOTE: os.remove(zip_path) has been removed permanently to keep the file for GitHub push.
        
        # 4. Cleanup downloaded files (Keep the ZIP and JSON)
        print("Cleaning up downloaded files...")
        for file in glob.glob(os.path.join(DOWNLOAD_DIR, '*')):
            os.remove(file)
        self.save_downloaded_ids(set()) 

    def run(self, username, password):
        wg_done = False
        session = 0
        wg_ids = self.load_downloaded_ids()
        
        try:
            while not wg_done and session < 20: 
                session += 1
                self.setup()
                if self.login(username, password) and self.navigate_to_downloads():
                    wg_done, wg_ids = self.process_wireguard_downloads(wg_ids)
                    self.save_downloaded_ids(wg_ids)
                self.logout()
                self.teardown()
                
                if not wg_done: 
                    print(f"Session {session} done. Re-logging in {RELOGIN_DELAY}s...")
                    time.sleep(RELOGIN_DELAY)
            
            self.organize_and_send_files()

        except Exception as e: print(f"Fatal Error: {e}")
        finally: self.teardown()

if __name__ == "__main__":
    U = os.environ.get("VPN_USERNAME")
    P = os.environ.get("VPN_PASSWORD")
    if U and P: 
        ProtonVPN().run(U, P)
    else: 
        print("Missing Credentials.")
