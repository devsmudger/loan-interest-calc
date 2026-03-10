import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_irr(cash_flows):
    if not cash_flows: return 0
    # Use a more stable IRR solver for edge cases
    try:
        roots = np.roots(cash_flows[::-1])
        real_roots = roots[np.isreal(roots)].real
        rates = [(1/x) - 1 for x in real_roots if x > 0]
        return rates[0] if rates else 0
    except:
        return 0

def calculate_revolving_loan(credit_limit, annual_rate, transactions, drawdown_fee_pct=0, monthly_fee=0, ol_fee_flat=0, ol_fee_pct=0):
    transactions.sort(key=lambda x: x[0])
    start_date = transactions[0][0]
    last_trans_date = transactions[-1][0]
    
    if last_trans_date.month == 12:
        end_date = datetime(last_trans_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(last_trans_date.year, last_trans_date.month + 1, 1) - timedelta(days=1)

    daily_data = []
    bal_principal = 0.0
    bal_interest = 0.0
    bal_fees = 0.0
    
    accrued_interest_total = 0.0
    accrued_fees_total = 0.0
    
    current_date = start_date
    trans_dict = {t[0].date(): t[1] for t in transactions}
    
    # Cash flows for EIR: we only count up to the point where debt hits zero
    eir_cash_flows = []
    debt_cleared = False
    
    while current_date <= end_date:
        trans_amt = trans_dict.get(current_date.date(), 0)
        daily_flow = 0.0
        
        # 1. Monthly Fee
        if current_date.day == 1 and current_date > start_date:
            bal_fees += monthly_fee
            accrued_fees_total += monthly_fee
            daily_flow -= monthly_fee
            
        # 2. Transaction
        if trans_amt > 0: # Withdrawal
            draw_fee = trans_amt * (drawdown_fee_pct / 100)
            bal_principal += trans_amt
            bal_fees += draw_fee
            accrued_fees_total += draw_fee
            daily_flow = trans_amt - draw_fee
            debt_cleared = False
        elif trans_amt < 0: # Repayment
            payment = abs(trans_amt)
            
            # For EIR, if this payment clears the debt, we only count the part that hits 0
            current_total_due = bal_principal + bal_interest + bal_fees
            if payment >= current_total_due and not debt_cleared:
                daily_flow = -current_total_due # Only count what was owed
                debt_cleared = True
            elif not debt_cleared:
                daily_flow = trans_amt
            
            # Allocation
            p_fees = min(payment, bal_fees)
            bal_fees -= p_fees
            payment -= p_fees
            p_int = min(payment, bal_interest)
            bal_interest -= p_int
            payment -= p_int
            bal_principal -= payment # principal can go negative
            
        # 3. Accrue Interest
        if bal_principal > 0:
            daily_interest = (bal_principal * (annual_rate / 100)) / 365
        else:
            daily_interest = 0.0
        bal_interest += daily_interest
        accrued_interest_total += daily_interest
        
        # 4. Over-limit
        monthly_max_bal = max(bal_principal + bal_interest + bal_fees, 0) # simplified max track
        
        is_last_day = (current_date + timedelta(days=1)).day == 1
        if is_last_day:
            # Re-calculating monthly max accurately would require a sub-loop, 
            # using daily_data for the month instead
            month_data = [d for d in daily_data if d['Date'].month == current_date.month and d['Date'].year == current_date.year]
            month_max = max([d['Total Debt'] for d in month_data] + [bal_principal + bal_interest + bal_fees])
            
            if month_max > credit_limit:
                ol_fee = ol_fee_flat + ((month_max - credit_limit) * ol_fee_pct / 100)
                bal_fees += ol_fee
                accrued_fees_total += ol_fee
                if not debt_cleared:
                    daily_flow -= ol_fee
            
        eir_cash_flows.append(daily_flow)
        daily_data.append({
            "Date": current_date.date(),
            "Principal": bal_principal,
            "Interest Owed": bal_interest,
            "Fees Owed": bal_fees,
            "Total Debt": bal_principal + bal_interest + bal_fees,
            "Transaction": trans_amt
        })
        current_date += timedelta(days=1)
        
    # If not cleared by the end, add final balance as outflow for EIR
    if not debt_cleared:
        eir_cash_flows[-1] -= (bal_principal + bal_interest + bal_fees)

    eir = ((1 + calculate_irr(eir_cash_flows))**365 - 1) * 100
    
    df = pd.DataFrame(daily_data)
    df['Month'] = pd.to_datetime(df['Date']).dt.to_period('M')
    summary = df.groupby('Month').agg({
        'Transaction': [lambda x: x[x > 0].sum(), lambda x: x[x < 0].sum()],
        'Principal': 'last', 'Interest Owed': 'last', 'Fees Owed': 'last', 'Total Debt': 'last'
    })
    summary.columns = ['Withdrawals', 'Repayments', 'End Principal', 'End Interest', 'End Fees', 'Total Debt']
    
    return summary, accrued_interest_total, accrued_fees_total, eir

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=float, required=True)
    parser.add_argument("--rate", type=float, required=True)
    parser.add_argument("--drawdown-fee", type=float, default=0)
    parser.add_argument("--monthly-fee", type=float, default=0)
    parser.add_argument("--overlimit-fee-flat", type=float, default=0)
    parser.add_argument("--overlimit-fee-pct", type=float, default=0)
    parser.add_argument("--trans", nargs='+', required=True)
    args = parser.parse_args()
    
    parsed = []
    for t in args.trans:
        d, a = t.split(':')
        parsed.append((datetime.strptime(d, '%Y-%m-%d'), float(a)))
        
    summary, tint, tfees, eir = calculate_revolving_loan(args.limit, args.rate, parsed, args.drawdown_fee, args.monthly_fee, args.overlimit_fee_flat, args.overlimit_fee_pct)
    
    print("\n" + "="*125)
    print("                REVOLVING CREDIT SUMMARY (Fees -> Interest -> Principal)")
    print("                Note: Negative Total Debt = Credit Balance (Bank owes you)")
    print("="*125)
    print(f"Credit Limit: {args.limit:,.2f} | Nominal Rate: {args.rate:.2f}%")
    print("-" * 125)
    pd.options.display.float_format = '{:,.2f}'.format
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(summary)
    print("-" * 125)
    print(f"TOTAL INTEREST ACCRUED: {tint:,.2f} (Total charged by bank)")
    print(f"TOTAL FEES ACCRUED:     {tfees:,.2f} (Total penalties/fees charged)")
    print(f"ANNUAL EIR (TRUE COST): {eir:.2f}% (Calculated up to debt clearance)")
    print("-" * 125)
    print(f"TOTAL COST OF CREDIT:   {tint + tfees:,.2f} (Sum of all interest and fees)")
    print("="*125 + "\n")

if __name__ == "__main__":
    main()
