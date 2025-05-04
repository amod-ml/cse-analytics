import asyncio
import json
import logging
import pathlib

from bs4 import BeautifulSoup, Comment  # Import BeautifulSoup
from playwright.async_api import async_playwright

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Output Directory ---
OUTPUT_DIR = pathlib.Path("output/playwright_explore")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def explore_and_clean_cse_profile(url: str) -> dict:
    """
    Uses Playwright to navigate to the Quarterly Reports tab on a CSE profile,
    then cleans the resulting HTML and saves it.
    """
    result_info = {
        "initial_html_path": None,
        # "financials_tab_html_path": None, # Removing intermediate save
        "cleaned_quarterly_reports_path": None,
        "error": None,
    }
    playwright = None
    browser = None
    initial_html_path = OUTPUT_DIR / "initial_page.html"
    # financials_html_path = OUTPUT_DIR / "financials_tab.html" # Removing intermediate save
    cleaned_quarterly_html_path = OUTPUT_DIR / "quarterly_reports_tab_cleaned.html"
    error_html_path = OUTPUT_DIR / "error_page.html"

    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        logger.info(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        logger.info("Navigation complete.")

        # --- Get and Save Initial Structure ---
        logger.info("--- Saving Initial Page Structure ---")
        initial_html = await page.content()
        with open(initial_html_path, "w", encoding="utf-8") as f:
            f.write(initial_html)
        result_info["initial_html_path"] = str(initial_html_path.resolve())
        logger.info(f"Initial HTML saved to: {result_info['initial_html_path']}")
        logger.info("--- End of Initial Page Save ---\n")

        # --- Locate and Click 'Financials' Tab ---
        # *** Selector likely needs refinement based on initial_page.html ***
        financials_tab_selector = "a:has-text('Financials')"  # Example: //a[normalize-space()='Financials'] might be more robust
        logger.info(f"Attempting to click 'Financials' tab with selector: '{financials_tab_selector}'...")

        try:
            financials_tab_element = page.locator(financials_tab_selector)
            await financials_tab_element.wait_for(state="visible", timeout=15000)
            logger.info("'Financials' tab element found and visible. Clicking...")
            await financials_tab_element.click()
            logger.info("Clicked 'Financials' tab. Waiting for content...")
            await page.wait_for_timeout(3000)

            # --- Locate and Click 'Quarterly Reports' Tab (within Financials) ---
            # *** Selector likely needs refinement based on the HTML after clicking Financials ***
            quarterly_tab_selector = "a:has-text('Quarterly Reports')"  # Example: //a[normalize-space()='Quarterly Reports']
            logger.info(f"Attempting to click 'Quarterly Reports' tab with selector: '{quarterly_tab_selector}'...")

            try:
                quarterly_tab_element = page.locator(quarterly_tab_selector)
                await quarterly_tab_element.wait_for(state="visible", timeout=15000)
                logger.info("'Quarterly Reports' tab element found and visible. Clicking...")
                await quarterly_tab_element.click()
                logger.info("Clicked 'Quarterly Reports' tab. Waiting for final content...")
                await page.wait_for_timeout(4000)  # Slightly longer wait for final content

                # --- Get, Clean, and Save Final Structure ---
                logger.info("--- Getting Final Page HTML ---")
                final_html = await page.content()
                logger.info("--- Cleaning Final Page HTML ---")

                soup = BeautifulSoup(final_html, "html.parser")

                # Remove unwanted tags
                for tag_name in ["script", "style", "noscript", "meta"]:
                    for tag in soup.find_all(tag_name):
                        tag.decompose()
                        logger.debug(f"Removed <{tag_name}> tag")

                # Remove stylesheet links
                for link in soup.find_all("link", rel="stylesheet"):
                    link.decompose()
                    logger.debug("Removed <link rel='stylesheet'>")

                # Remove comments
                for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                    comment.extract()
                    logger.debug("Removed HTML comment")

                cleaned_html = soup.prettify()  # Get cleaned HTML as string
                logger.info("HTML Cleaning complete.")

                logger.info("--- Saving Cleaned Final Page Structure ---")
                with open(cleaned_quarterly_html_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_html)
                result_info["cleaned_quarterly_reports_path"] = str(cleaned_quarterly_html_path.resolve())
                logger.info(f"Cleaned 'Quarterly Reports' tab HTML saved to: {result_info['cleaned_quarterly_reports_path']}")
                logger.info("--- End of Final Page Save ---\n")

            except Exception as quarterly_err:
                error_msg = f"Could not find/click 'Quarterly Reports' tab ('{quarterly_tab_selector}') or clean/save HTML: {quarterly_err}"
                logger.error(error_msg, exc_info=True)  # Log traceback for cleaning errors too
                result_info["error"] = error_msg
                logger.warning("Saving current HTML state after failing to process 'Quarterly Reports' tab.")
                try:
                    current_html = await page.content()
                    with open(error_html_path, "w", encoding="utf-8") as f:
                        f.write(current_html)
                    logger.info(f"Error HTML saved to: {error_html_path.resolve()}")
                except Exception as save_err:
                    logger.error(f"Could not save error HTML: {save_err}")

        except Exception as financials_err:
            error_msg = f"Could not find or click the 'Financials' tab ('{financials_tab_selector}'): {financials_err}"
            logger.error(error_msg, exc_info=True)
            result_info["error"] = error_msg
            logger.warning("Saving current HTML state after failing to click 'Financials' tab.")
            try:
                current_html = await page.content()
                with open(error_html_path, "w", encoding="utf-8") as f:
                    f.write(current_html)
                logger.info(f"Error HTML saved to: {error_html_path.resolve()}")
            except Exception as save_err:
                logger.error(f"Could not save error HTML: {save_err}")

    except Exception as e:
        error_msg = f"An unexpected error occurred during scraping: {e}"
        logger.exception(error_msg)
        result_info["error"] = error_msg
        if "page" in locals() and page.is_closed() is False:  # Check if page exists and is open
            try:
                logger.warning("Attempting to save HTML state after unexpected error.")
                current_html = await page.content()
                with open(error_html_path, "w", encoding="utf-8") as f:
                    f.write(current_html)
                logger.info(f"Error HTML saved to: {error_html_path.resolve()}")
            except Exception as save_err:
                logger.error(f"Could not save error HTML: {save_err}")
    finally:
        if browser:
            await browser.close()
            logger.info("Browser closed.")
        if playwright:
            await playwright.stop()
            logger.info("Playwright stopped.")

    return result_info


async def main():
    """Main function to run the async scraper."""
    target_url = "https://www.cse.lk/pages/company-profile/company-profile.component.html?symbol=DIPD.N0000"
    logger.info(f"Starting Playwright exploration and cleaning for URL: {target_url}")
    # Ensure bs4 is installed: pip install beautifulsoup4
    result = await explore_and_clean_cse_profile(target_url)
    logger.info("\n--- Final Result ---")
    logger.info(json.dumps(result, indent=2))
    logger.info("--- End of Script ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript interrupted by user.")
    except Exception as e:
        logger.exception(f"\nAn unhandled error occurred during execution: {e}")
