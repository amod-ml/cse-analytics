import json

from google import genai
from google.genai import types

from app.utils.google_genai_client import get_google_genai_client
from app.utils.structlogger import logger


async def generate_financial_data(file_path: str) -> dict:
    logger.info("Creating Google GenAI client...")
    client = await get_google_genai_client()

    logger.info(f"Uploading file: {file_path}")
    files = [
        client.files.upload(file=str(file_path)),
    ]
    logger.info(f"File uploaded. URI: {files[0].uri}")
    model = "gemini-2.5-flash-preview-04-17"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=files[0].uri,
                    mime_type=files[0].mime_type,
                ),
                types.Part.from_text(
                    text="""Extract the required financial data from the attached quarterly report PDF according to the given schema and instructions.
                    Focus on the Group/Consolidated P&L for the latest quarter reported.
                    Strictly ignore links that point to Interim Financial Statements or any other reports other than Quarterly Financial Reports."""
                ),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(
            thinking_budget=8192,
        ),
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=[
                "company_name",
                "period_end_date",
                "currency",
                "unit",
                "revenue",
                "cost_of_sales",
                "gross_profit",
                "operating_expenses",
                "profit_before_tax",
                "net_income_parent",
            ],
            properties={
                "company_name": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="Name of the company (e.g., 'DIPPED PRODUCTS PLC'). Null if not found.",
                ),
                "period_end_date": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="End date of the latest quarter reported (YYYY-MM-DD). Null if not found.",
                ),
                "currency": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="Currency used in the report (e.g., 'LKR', 'Rs.'). Null if not found.",
                ),
                "unit": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="Unit of financial figures (e.g., ''000', 'Millions', 'Absolute').",
                ),
                "revenue": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Turnover/Revenue for the latest quarter. Null if not found.",
                ),
                "cost_of_sales": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Cost of Sales/COGS for the latest quarter (as a positive number). Null if not found.",
                ),
                "gross_profit": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Gross Profit for the latest quarter. Null if not found.",
                ),
                "operating_expenses": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Sum of Distribution and Admin costs, or total Operating Expenses for the latest quarter (as a positive number). Null if not found/calculable.",
                ),
                "profit_before_tax": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Profit/(loss) before tax for the latest quarter. Null if not found.",
                ),
                "net_income_parent": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Profit/(loss) for the period attributable to parent equity holders (or total if attribution not specified) for the latest quarter. Null if not found.",
                ),
            },
        ),
        system_instruction=[
            types.Part.from_text(
                text="""You are an expert financial data extraction tool.
                Your task is to analyze the provided quarterly financial report PDF and extract key information from the Profit and Loss (P&L) statement, also known as the Statement of Profit or Loss.

                Instructions:
                1.  Prioritize the **Consolidated/Group** statement figures if available. If only Company figures are present, use those.
                2.  Focus **only** on the data column representing the **most recent quarter** presented in the P&L statement (e.g., \"3 months ended [Date]\").
                Do not extract data from cumulative columns (e.g., \"6 months ended\") or comparative columns for the previous year.
                3.  Extract the following financial metrics for that specific quarter:
                    * `company_name`: The name of the company publishing the report (e.g., \"DIPPED PRODUCTS PLC\"). If not explicitly found, return null.
                    * `period_end_date`: The end date of the most recent quarter reported in 'YYYY-MM-DD' format (e.g., \"2017-06-30\" from \"30/06/2017\").
                    * `currency`: The currency reported (e.g., \"LKR\" or \"Rs.\"). If not explicitly found, return null.
                    * `unit`: The unit of the figures (e.g., \"'000\", \"Millions\", \"Absolute\"). If reported in thousands like \"Rs. '000\", use \"'000\".
                    If not specified, assume absolute value and return \"Absolute\".
                    * `revenue`: The 'Turnover' or 'Revenue' figure.
                    * `cost_of_sales`: The 'Cost of sales' or 'Cost of Goods Sold' figure.
                    Often presented as a negative number or in parentheses; return it as a positive number.
                    * `gross_profit`: The 'Gross profit' figure.
                    * `operating_expenses`: Sum of 'Distribution costs' and 'Administrative expenses'.
                    If these are not itemized, look for a line item like 'Operating Expenses' and extract that. Return as a positive number.
                    If neither breakdown nor a single line item is found, return null.
                    * `profit_before_tax`: The 'Profit/(loss) before tax' figure.
                    * `net_income_parent`: The 'Profit/(loss) for the period' specifically 'Attributable to: Equity holders of the parent'.
                    If this specific attribution is not present, use the main 'Profit/(loss) for the period' figure.
                4.  Extract only the numeric values. Remove currency symbols, commas, and handle parentheses indicating negative numbers
                (return the absolute value for costs/expenses as requested, but maintain the sign for profit/loss figures).
                5.  If a specific metric cannot be found in the P&L for the latest quarter, return `null` for that field.
                6.  Strictly adhere to the provided JSON schema for the response format. Do not add any extra text or explanations."""
            ),
        ],
    )

    logger.info("Calling Gemini model for content extraction...")
    all_text = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        logger.info("Received response chunk from Gemini model.")
        all_text += chunk.text
    logger.info(f"Result: {all_text}")
    return json.loads(all_text)
