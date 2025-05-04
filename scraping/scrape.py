import asyncio
import json
import logging
import pathlib

import aiofiles  # Import aiofiles
from bs4 import BeautifulSoup, Comment
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Output Directory ---
# Ensure the output directory name doesn't clash if running for multiple symbols
# For now, using a fixed name based on the original script
OUTPUT_DIR = pathlib.Path("output/playwright_explore_rpe")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_HTML_PATH = OUTPUT_DIR / "error_page.html"


async def _save_html_async(filepath: pathlib.Path, content: str, description: str) -> None:
    """Asynchronously saves HTML content to a file."""
    try:
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(content)
        logger.info(f"{description} HTML saved to: {filepath.resolve()}")
    except Exception as e:
        logger.error(f"Failed to save {description} HTML to {filepath}: {e}")


async def _click_tab_and_wait(page: Page, selector: str, description: str, timeout_ms: int = 15000, wait_after: int = 3000) -> bool:
    """Attempts to click a tab specified by selector and waits."""
    logger.info(f"Attempting to click '{description}' tab with selector: '{selector}'...")
    try:
        tab_element = page.locator(selector)
        # Wait for the element to be attached and visible
        await tab_element.wait_for(state="visible", timeout=timeout_ms)
        logger.info(f"'{description}' tab element found and visible. Clicking...")
        # Use force=True cautiously if needed, but try without first
        await tab_element.click(timeout=timeout_ms)
        logger.info(f"Clicked '{description}' tab. Waiting {wait_after}ms...")
        await page.wait_for_timeout(wait_after)
        return True
    except PlaywrightError as e:
        logger.error(f"Could not find or click the '{description}' tab ('{selector}'): {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while clicking '{description}' tab: {e}")
        return False


def _clean_html(html_content: str) -> str:
    """Cleans HTML content by removing script, style, meta, etc."""
    logger.info("--- Cleaning HTML ---")
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove unwanted tags
        removed_count = 0
        for tag_name in ["script", "style", "noscript", "meta", "link"]:  # Include link here
            for tag in soup.find_all(tag_name):
                # Further check for link tags to only remove stylesheets if needed
                if tag.name == "link" and "stylesheet" not in tag.get("rel", []):
                    continue
                tag.decompose()
                removed_count += 1
        logger.debug(f"Removed {removed_count} script/style/noscript/meta/link tags.")

        # Remove comments
        comment_count = 0
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            comment_count += 1
        logger.debug(f"Removed {comment_count} HTML comments.")

        cleaned_html = soup.prettify()
        logger.info("HTML Cleaning complete.")
        return cleaned_html
    except Exception as e:
        logger.error(f"Error during HTML cleaning: {e}")
        # Return original content if cleaning fails
        return html_content


async def explore_and_clean_cse_profile(url: str) -> dict:
    """
    Uses Playwright to navigate to the Quarterly Reports tab on a CSE profile,
    then cleans the resulting HTML and saves it.
    """
    result_info = {
        "initial_html_path": None,
        "cleaned_quarterly_reports_path": None,
        "error": None,
    }
    playwright = None
    browser = None
    page = None  # Define page here for broader scope in finally block
    initial_html_path = OUTPUT_DIR / "initial_page.html"
    cleaned_quarterly_html_path = OUTPUT_DIR / "quarterly_reports_tab_cleaned.html"

    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        logger.info(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        logger.info("Navigation complete.")

        # --- Get and Save Initial Structure ---
        initial_html = await page.content()
        await _save_html_async(initial_html_path, initial_html, "Initial Page")
        result_info["initial_html_path"] = str(initial_html_path.resolve())

        # --- Click 'Financials' Tab ---
        # *** Adjust selector as needed ***
        financials_selector = "a:has-text('Financials')"
        if not await _click_tab_and_wait(page, financials_selector, "Financials"):
            result_info["error"] = f"Failed to click 'Financials' tab ({financials_selector})"
            await _save_html_async(ERROR_HTML_PATH, await page.content(), "Error state after Financials click fail")
            return result_info  # Exit early if first click fails

        # --- Click 'Quarterly Reports' Tab ---
        # *** Adjust selector as needed ***
        quarterly_selector = "a:has-text('Quarterly Reports')"
        if not await _click_tab_and_wait(page, quarterly_selector, "Quarterly Reports"):
            result_info["error"] = f"Failed to click 'Quarterly Reports' tab ({quarterly_selector})"
            await _save_html_async(ERROR_HTML_PATH, await page.content(), "Error state after Quarterly Reports click fail")
            return result_info  # Exit early if second click fails

        # --- Get, Clean, and Save Final Structure ---
        logger.info("Getting final page HTML for cleaning...")
        final_raw_html = await page.content()
        cleaned_html = _clean_html(final_raw_html)
        await _save_html_async(cleaned_quarterly_html_path, cleaned_html, "Cleaned Quarterly Reports")
        result_info["cleaned_quarterly_reports_path"] = str(cleaned_quarterly_html_path.resolve())

    except Exception as e:
        error_msg = f"An unexpected error occurred during scraping: {e}"
        logger.exception(error_msg)  # Use logger.exception here
        result_info["error"] = error_msg
        # Attempt to save HTML if page object exists and is usable
        if page and not page.is_closed():
            try:
                logger.warning("Attempting to save HTML state after unexpected error.")
                await _save_html_async(ERROR_HTML_PATH, await page.content(), "Error state after unexpected exception")
            except Exception as save_err:
                logger.error(f"Could not save error HTML after unexpected exception: {save_err}")
    finally:
        if browser:
            await browser.close()
            logger.info("Browser closed.")
        if playwright:
            await playwright.stop()
            logger.info("Playwright stopped.")

    return result_info


async def main() -> None:  # Added return type annotation
    """Main function to run the async scraper."""
    # *** Update this URL if needed ***
    target_url = "https://www.cse.lk/pages/company-profile/company-profile.component.html?symbol=REXP.N0000"
    logger.info(f"Starting Playwright exploration and cleaning for URL: {target_url}")
    # Ensure dependencies are installed: pip install beautifulsoup4 aiofiles
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
