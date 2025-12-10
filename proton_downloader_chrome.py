import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# Define the selector for the modal backdrop which causes the click interception error
MODAL_BACKDROP_SELECTOR = (By.CLASS_NAME, "modal-two-backdrop")
CONFIRM_BUTTON_SELECTOR = (By.CSS_SELECTOR, ".button-solid-norm:nth-child(2)")

# Define the download path accessible by GitHub Actions
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloaded_configs")

# Create the download directory if it doesn't exist
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
    print(f"Created download directory: {DOWNLOAD_DIR}")


class ProtonVPN:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        
        # --- Optimization for GitHub Actions/Server Environments ---
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        
        # *** Key Configuration: Setting the Download Path in Chrome ***
        prefs = {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True 
        }
        self.options.add_experimental_option("prefs", prefs)

        self.driver = None

    def setup(self):
        """Initializes the WebDriver (Chrome) with Headless options."""
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.set_window_size(1936, 1048)
        self.driver.implicitly_wait(10)
        print("WebDriver initialized successfully in Headless mode (Chrome).")

    def teardown(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")
            
    # --- Login, Navigation methods remain the same ---

    def login(self, username, password):
        try:
            self.driver.get("https://protonvpn.com/")
            time.sleep(2)
            # ... (Rest of Login logic) ...
            self.driver.find_element(By.XPATH, "//a[contains(@href, 'https://account.protonvpn.com/login')]").click()
            time.sleep(2)
            user_field = self.driver.find_element(By.ID, "username")
            user_field.clear()
            user_field.send_keys(username)
            time.sleep(1)
            self.driver.find_element(By.CSS_SELECTOR, ".button-large").click()
            time.sleep(2)
            pass_field = self.driver.find_element(By.ID, "password")
            pass_field.clear()
            pass_field.send_keys(password)
            time.sleep(1)
            self.driver.find_element(By.CSS_SELECTOR, ".button-large").click()
            time.sleep(5)
            print("Login Successful.")
            return True
        except Exception as e:
            print(f"Error Login: {e}")
            return False

    def navigate_to_downloads(self):
        try:
            downloads_link_selector = (By.CSS_SELECTOR, ".navigation-item:nth-child(7) .text-ellipsis")
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(downloads_link_selector)
            ).click()
            time.sleep(3)
            print("Navigated to Downloads section.")
            return True
        except Exception as e:
            print(f"Error Navigating to Downloads: {e}")
            return False

    def download_configurations(self):
        try:
            self.driver.execute_script("window.scrollTo(0,0)")
            time.sleep(2)

            # Click the configuration type tab (e.g., OpenVPN)
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".flex:nth-child(4) > .mr-8:nth-child(3) > .relative").click()
                time.sleep(2)
            except:
                pass

            countries = self.driver.find_elements(By.CSS_SELECTOR, ".mb-6 details")
            print(f"Found {len(countries)} countries to process.")

            for country in countries:
                try:
                    self.driver.execute_script("arguments[0].open = true;", country)
                    time.sleep(0.5)

                    country_name = country.find_element(By.CSS_SELECTOR, "summary").text.split('\n')[0]
                    buttons = country.find_elements(By.CSS_SELECTOR, "tr .button")

                    for index, btn in enumerate(buttons):
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.5)

                            # 1. Click to open the modal
                            ActionChains(self.driver).move_to_element(btn).click().perform()

                            # 2. Wait explicitly for the confirm button to be clickable (Modal appeared)
                            confirm_btn = WebDriverWait(self.driver, 15).until(
                                EC.element_to_be_clickable(CONFIRM_BUTTON_SELECTOR)
                            )
                            confirm_btn.click()

                            # 3. CRITICAL: Wait for the modal backdrop to disappear (Max 15 seconds)
                            WebDriverWait(self.driver, 15).until(
                                EC.invisibility_of_element_located(MODAL_BACKDROP_SELECTOR)
                            )
                            
                            print(f"Successfully downloaded config {index + 1} for {country_name}.")

                            # 4. CRITICAL: Increased delay to 15 seconds to prevent rate limiting/race conditions
                            time.sleep(15) 

                        except (TimeoutException, ElementClickInterceptedException) as e:
                            print(f"Error downloading file {index + 1} for {country_name}. Timeout or Interception. Retrying cleanup... Error: {e}")
                            # Attempt to ensure the backdrop is cleared before continuing
                            try:
                                WebDriverWait(self.driver, 5).until(
                                    EC.invisibility_of_element_located(MODAL_BACKDROP_SELECTOR)
                                )
                            except:
                                print("Warning: Backdrop cleanup failed, continuing anyway.")
                            
                            # Massive wait for server recovery
                            time.sleep(30)
                            continue
                        
                        except Exception as e:
                            print(f"General error during download {index + 1} for {country_name}: {e}")
                            time.sleep(30)
                            continue

                except Exception as e:
                    print(f"Error processing country block: {e}")
                    continue

            return True

        except Exception as e:
            print(f"Error in main download loop: {e}")
            return False

    def logout(self):
        # ... (Logout logic remains the same) ...
        try:
            self.driver.find_element(By.CSS_SELECTOR, ".p-1").click()
            time.sleep(1)
            self.driver.find_element(By.CSS_SELECTOR, ".mb-4 > .button").click()
            time.sleep(2)
            print("Logout Successful.")
            return True
        except Exception as e:
            print(f"Error Logout: {e}")
            return False

    def run(self, username, password):
        try:
            self.setup()
            if self.login(username, password):
                if self.navigate_to_downloads():
                    self.download_configurations()
                self.logout()
        except Exception as e:
            print(f"Runtime Error: {e}")
        finally:
            self.teardown()

if __name__ == "__main__":
    USERNAME = os.environ.get("VPN_USERNAME")
    PASSWORD = os.environ.get("VPN_PASSWORD")
    
    if not USERNAME or not PASSWORD:
        print("---")
        print("ERROR: VPN_USERNAME or VPN_PASSWORD not loaded from environment variables.")
        print("Please configure them as Secrets in your GitHub repository.")
        print("---")
    else:
        print("Account info loaded from environment variables. Starting workflow...")
        proton = ProtonVPN()
        proton.run(USERNAME, PASSWORD)
