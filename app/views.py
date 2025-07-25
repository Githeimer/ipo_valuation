from django.shortcuts import render
import pandas as pd

def upload_files(request):
    table_html = None
    total_profit = None
    is_profit = None

    def format_nepali_currency(amount):
        """Format number in Nepali currency style (e.g., 2,00,000)"""
        if pd.isna(amount) or amount == 0:
            return "0"

        is_negative = amount < 0
        amount_str = f"{abs(amount):.2f}"

        if '.' in amount_str:
            integer_part, decimal_part = amount_str.split('.')
        else:
            integer_part, decimal_part = amount_str, "00"

        if len(integer_part) > 3:
            result = integer_part[-3:]
            remaining = integer_part[:-3]
            while len(remaining) > 2:
                result = remaining[-2:] + "," + result
                remaining = remaining[:-2]
            if remaining:
                result = remaining + "," + result
        else:
            result = integer_part

        if decimal_part != "00":
            result += "." + decimal_part

        return ("-" if is_negative else "") + result

    if request.method == 'POST' and request.FILES.get('wacc_file') and request.FILES.get('portfolio_file'):
        wacc_file = request.FILES['wacc_file']
        portfolio_file = request.FILES['portfolio_file']

        try:
            # Read files
            wacc_df = pd.read_csv(wacc_file)
            portfolio_df = pd.read_csv(portfolio_file)

            # Rename for consistency
            wacc_df.rename(columns={
                'Scrip Name': 'Scrip',
                'WACC Rate': 'Bought Rate'
            }, inplace=True)

            portfolio_df.rename(columns={
                'Current Balance': 'Quantity'
            }, inplace=True)

            # Merge data on 'Scrip'
            merged_df = pd.merge(wacc_df, portfolio_df[['Scrip', 'Quantity', 'Last Transaction Price (LTP)']], on='Scrip', how='inner')

            # Ensure numeric types
            numeric_cols = ['Quantity', 'Bought Rate', 'Last Transaction Price (LTP)']
            for col in numeric_cols:
                merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0)

            # Calculations
            merged_df['Initial Investment'] = merged_df['Quantity'] * merged_df['Bought Rate']
            merged_df['Current Return'] = merged_df['Quantity'] * merged_df['Last Transaction Price (LTP)']
            merged_df['Profit/Loss'] = merged_df['Current Return'] - merged_df['Initial Investment']
            merged_df['Profit/Loss (after 5%)'] = merged_df['Profit/Loss'].apply(lambda x: x * 0.95 if x > 0 else x)

            # Totals
            total_profit = merged_df['Profit/Loss (after 5%)'].sum()
            total_investment = merged_df['Initial Investment'].sum()
            total_current_value = merged_df['Current Return'].sum()
            is_profit = total_profit > 0

            formatted_total_profit = format_nepali_currency(total_profit)
            formatted_total_investment = format_nepali_currency(total_investment)
            formatted_total_current_value = format_nepali_currency(total_current_value)

            # Create display table
            display_df = merged_df[['Scrip', 'Quantity', 'Bought Rate', 'Initial Investment',
                                    'Last Transaction Price (LTP)', 'Current Return', 'Profit/Loss (after 5%)']]

            # Format currency columns
            currency_columns = ['Initial Investment', 'Current Return', 'Profit/Loss (after 5%)']
            for col in currency_columns:
                display_df[col] = display_df[col].apply(format_nepali_currency)

            # Convert to HTML table
            table_html = display_df.to_html(
                classes='table table-striped table-bordered',
                index=False,
                table_id="results-table",
                escape=False
            )

            # Highlight profit/loss values
            import re
            def add_profit_loss_styling(match):
                cell_content = match.group(1)
                numeric_match = re.search(r'(-?\d+(?:,\d+)*(?:\.\d+)?)', cell_content)
                if numeric_match:
                    numeric_value = float(numeric_match.group(1).replace(',', ''))
                    css_class = 'profit' if numeric_value >= 0 else 'loss'
                    return f'<td class="{css_class}">{cell_content}</td>'
                return match.group(0)

            pattern = r'<td>([^<]*?(?:-?\d+(?:,\d+)*(?:\.\d+)?)[^<]*?)</td>(?=\s*</tr>)'
            table_html = re.sub(pattern, add_profit_loss_styling, table_html)

        except Exception as e:
            print(f"Error: {e}")

    return render(request, 'upload.html', {
        'table_html': table_html,
        'total_profit': formatted_total_profit if table_html else None,
        'total_investment': formatted_total_investment if table_html else None,
        'total_current_value': formatted_total_current_value if table_html else None,
        'is_profit': is_profit
    })
