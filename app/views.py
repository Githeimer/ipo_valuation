from django.shortcuts import render
import pandas as pd

def upload_files(request):
    table_html = None
    total_profit = None
    is_profit = None
    
    def format_nepali_currency(amount):
        """Format number in Nepali currency style (2,00,000)"""
        if pd.isna(amount) or amount == 0:
            return "0"
        
        # Convert to string and handle negative numbers
        is_negative = amount < 0
        amount_str = f"{abs(amount):.2f}"
        
        # Split integer and decimal parts
        if '.' in amount_str:
            integer_part, decimal_part = amount_str.split('.')
        else:
            integer_part, decimal_part = amount_str, "00"
        
        # Add commas in Nepali style (groups of 2 after first 3 digits from right)
        if len(integer_part) > 3:
            # First group of 3 from right
            result = integer_part[-3:]
            remaining = integer_part[:-3]
            
            # Then groups of 2
            while len(remaining) > 2:
                result = remaining[-2:] + "," + result
                remaining = remaining[:-2]
            
            if remaining:
                result = remaining + "," + result
        else:
            result = integer_part
        
        # Add decimal part if not zero
        if decimal_part != "00":
            result += "." + decimal_part
        
        return ("-" if is_negative else "") + result
    table_html = None
    total_profit = None
    is_profit = None
    
    if request.method == 'POST' and request.FILES.get('wacc_file') and request.FILES.get('portfolio_file'):
        wacc_file = request.FILES['wacc_file']
        portfolio_file = request.FILES['portfolio_file']
        
        try:
            wacc_df = pd.read_csv(wacc_file)
            portfolio_df = pd.read_csv(portfolio_file)
            
            # Ensure correct column naming based on your CSVs
            wacc_df.rename(columns={
                'Scrip Name': 'Scrip',
                'WACC Calculated Quantity': 'Quantity',
                'WACC Rate': 'Bought Rate'
            }, inplace=True)
            
            # Merge only on scrips you currently own
            merged_df = pd.merge(portfolio_df, wacc_df, on='Scrip', how='inner')
            
            # Ensure numeric
            numeric_cols = ['Quantity', 'Bought Rate', 'Last Transaction Price (LTP)']
            for col in numeric_cols:
                merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0)
            
            # Calculate columns
            merged_df['Initial Investment'] = merged_df['Quantity'] * merged_df['Bought Rate']
            merged_df['Current Return'] = merged_df['Quantity'] * merged_df['Last Transaction Price (LTP)']
            merged_df['Profit/Loss'] = merged_df['Current Return'] - merged_df['Initial Investment']
            
            # Apply 5% cut on profit only (not on losses)
            merged_df['Profit/Loss (after 5%)'] = merged_df['Profit/Loss'].apply(
                lambda x: x * 0.95 if x > 0 else x
            )
            
            total_profit = merged_df['Profit/Loss (after 5%)'].sum()
            total_investment = merged_df['Initial Investment'].sum()
            total_current_value = merged_df['Current Return'].sum()
            is_profit = total_profit > 0
            
            # Format totals for display
            formatted_total_profit = format_nepali_currency(total_profit)
            formatted_total_investment = format_nepali_currency(total_investment)
            formatted_total_current_value = format_nepali_currency(total_current_value)
            
            display_df = merged_df[['Scrip', 'Quantity', 'Bought Rate', 'Initial Investment',
                                    'Last Transaction Price (LTP)', 'Current Return', 'Profit/Loss (after 5%)']]
            
            # Format currency columns
            currency_columns = ['Initial Investment', 'Current Return', 'Profit/Loss (after 5%)']
            for col in currency_columns:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(format_nepali_currency)
            
            print(display_df)  # To print on your console for your reference
            
            # Generate HTML table with proper styling
            table_html = display_df.to_html(
                classes='table table-striped table-bordered', 
                index=False, 
                table_id="results-table",
                escape=False
            )
            
            # Add color styling to profit/loss column
            import re
            def add_profit_loss_styling(match):
                cell_content = match.group(1)
                # Extract numeric value to check if profit or loss
                numeric_match = re.search(r'(-?\d+(?:,\d+)*(?:\.\d+)?)', cell_content)
                if numeric_match:
                    # Remove commas and convert to float for comparison
                    numeric_value = float(numeric_match.group(1).replace(',', ''))
                    css_class = 'profit' if numeric_value >= 0 else 'loss'
                    return f'<td class="{css_class}">{cell_content}</td>'
                return match.group(0)
            
            # Find the profit/loss column and add styling (last column)
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