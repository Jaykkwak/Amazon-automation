import time
from selenium.webdriver.common.keys import Keys
import json
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException
from amazon_config import (
    get_chrome_web_driver,
    get_web_driver_options,
    set_ignore_certificate_error,
    set_browser_as_incognito,
    set_automation_as_head_less,
    DIRECTORY,
    NAME,
    CURRENCY,
    FILTERS,
    BASE_URL,
    USER,
    PASSWORD
)


class GenerateReport:
    def __init__(self, file_name, filters, base_link, currency, data):
        self.data = data
        self.file_name = file_name
        self.filters = filters
        self.base_link = base_link
        self.currency = currency
        report = {
            'title': self.file_name,
            'currency': self.currency,
            'filters': self.filters,
            'base_link': self.base_link,
            'products': self.data
        }
        print("Creating report...")
        with open(f"{DIRECTORY}/{file_name}.json", 'w') as f:
            json.dump(report, f, indent=6)
        print("Done...")


class AmazonAPI:
    def __init__(self, search_term, filters, base_url, currency, user, password):
        self.USER = user
        self.PASSWORD = password
        self.base_url = base_url
        self.search_term = search_term
        options = get_web_driver_options()
        set_ignore_certificate_error(options)
        set_browser_as_incognito(options)
        self.driver = get_chrome_web_driver(options)
        self.currency = currency
        self.price_filter = f"&rh=p_36%3A{filters['min']}00-{filters['max']}00"

    def run(self):
        print("Login..")
        self.get_login()
        print("Starting Script..")
        print(f"Looking for {self.search_term} products ...")
        links = self.get_products_links()
        time.sleep(1)
        if not links:
            print("Stopped script")
            return
        print(f"Got {len(links)} links to products...")
        print("Getting info about products...")
        products = self.get_products_info(links)
        print(f"Got info about {len(products)} products...")
        products = self.find_best_item(products)
        best_item_link = products[0]["url"]
        self.get_item_cart(best_item_link)
        #self.driver.quit()
        return products

    def get_login(self):
        self.driver.get(self.base_url)
        login = self.driver.find_element_by_id("nav-link-accountList")
        login.click()
        time.sleep(1)
        user = self.driver.find_element_by_id("ap_email")
        user.send_keys(self.USER)
        user.send_keys(Keys.ENTER)
        time.sleep(1)
        password = self.driver.find_element_by_id("ap_password")
        password.send_keys(self.PASSWORD)
        password.send_keys(Keys.ENTER)

    def get_item_cart(self, best_item_link):
        self.driver.get(best_item_link)
        time.sleep(2)
        cart = self.driver.find_element_by_id("add-to-cart-button")
        cart.click()

    def find_best_item(self, products):
        try:
            return sorted(products, key=lambda i: i["price"])
        except Exception as e:
            print(e)
            print("Problem with sorting items")
            return None

    def get_products_info(self, links):
        asins = self.get_asins(links)
        products = []
        for asin in asins:
            product = self.get_single_product_info(asin)
            if product:
                products.append(product)
        return products

    def get_asins(self, links):
        return [self.get_asin(link) for link in links]

    def get_single_product_info(self, asin):
        print(f"Product ID: {asin} - getting data ...")
        product_short_url = self.shorten_url(asin)
        self.driver.get(f'{product_short_url}?language=en_US')
        time.sleep(2)
        title = self.get_title()
        seller = self.get_seller()
        price = self.get_price()
        if title and seller and price:
            product_info = {
                "asin": asin,
                "url": product_short_url,
                "title": title,
                "seller": seller,
                "price": price
            }
            return product_info
        return None

    def shorten_url(self, asin):
        return self.base_url + "/dp/" + asin

    @staticmethod
    def get_asin(product_link):
        return product_link[product_link.find("/dp/") + 4:product_link.find("/ref")]

    def get_title(self):
        try:
            return self.driver.find_element_by_id("productTitle").text
        except Exception as e:
            print(e)
            print(f"Can't get title of a product")
            return None

    def get_seller(self):
        try:
            return self.driver.find_element_by_id("bylineInfo").text
        except Exception as e:
            print(e)
            print(f"Can't get seller of a product")
            return None

    def get_price(self):
        price = None
        try:
            price = self.driver.find_element_by_id("priceblock_ourprice").text
            price = price.split("$")
            price = float(price[1])
        except NoSuchElementException:
            try:
                availablity = self.driver.find_element_by_id("availability").text
                if "Available" in availablity:
                    price = self.driver.find_element_by_class_name("olp-padding-right").text
            except Exception as e:
                print(e)
                print(f"Can't get price of a product")
                return None
        except Exception as e:
            print(e)
            print(f"Can't get price of a product")
            return None
        return price

    def get_products_links(self):
        self.driver.get(self.base_url)
        element = self.driver.find_element_by_id("twotabsearchtextbox")
        element.send_keys(self.search_term)
        element.send_keys(Keys.ENTER)
        time.sleep(2)
        self.driver.get(f"{self.driver.current_url}{self.price_filter}")
        print(f"Our url {self.driver.current_url}")
        time.sleep(2)
        result_list = self.driver.find_elements_by_class_name("s-result-list")
        links = []
        try:
            results = result_list[0].find_elements_by_xpath(
                      "//div / span / div / div / div[2] / div[2] / div / div[1] / div / div / div[1]/ h2 / a")
            links = [link.get_attribute('href') for link in results]
            return links
        except Exception as e:
            print("Didn't get any products")
            print(e)
            return links


if __name__ == '__main__':
    am = AmazonAPI(NAME, FILTERS, BASE_URL, CURRENCY, USER, PASSWORD)
    data = am.run()
    GenerateReport(NAME, FILTERS, BASE_URL, CURRENCY, data)
