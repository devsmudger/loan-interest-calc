import argparse
import pandas as pd
import numpy as np
import math

def calculate_irr_from_cash_flows(cash_flows):
    """
    Calculate IRR using numpy's roots function.
    """
    if not cash_flows: return 0
    roots = np.roots(cash_flows[::-1])
    real_roots = roots[np.isreal(roots)].real
    rates = [(1/x) - 1 for x in real_roots if x > 0]
    return rates[0] if rates else 0

def generate_amortization_schedule(financed_amount, net_principal, payments, periodic_irr, promo_periods, 
                                   promo_interest_amt, standard_interest_amt,
                                   fees=0, subsidy=0, commission=0, mode='standard'):
    """
    Generate a month-by-month schedule showing Flat, Effective, and Income Recognition components.
    Supports standard (pro-rata) and incremental (baseline vs. total) modes.
    """
    schedule = []
    remaining_balance_eff = net_principal
    remaining_balance_base = financed_amount
    total_periods = len(payments)
    
    # Calculate Base IRR for incremental mode (Contract perspective only)
    base_cash_flows = [financed_amount] + [-p for p in payments]
    base_periodic_irr = calculate_irr_from_cash_flows(base_cash_flows)
    
    # Total upfront net inflow for standard amortization allocation
    total_upfront = fees + subsidy - commission
    
    for idx, payment in enumerate(payments):
        period = idx + 1
        
        # 1. Total Effective Income based on Total IRR
        eff_income = remaining_balance_eff * periodic_irr
        
        # 2. Base Income based on Base IRR (used for incremental mode)
        base_income = remaining_balance_base * base_periodic_irr
        
        # For the final period, we ensure balances hit exactly zero
        if period == total_periods:
            eff_principal = remaining_balance_eff
            base_principal = remaining_balance_base
        else:
            eff_principal = payment - eff_income
            base_principal = payment - base_income
            
        remaining_balance_eff -= eff_principal
        remaining_balance_base -= base_principal
        
        # Flat interest logic: what the customer pays
        current_flat_interest = promo_interest_amt if period <= promo_periods else standard_interest_amt
        
        # 3. Allocation Logic
        if mode == 'incremental':
            # Incremental Model:
            # - Int. Amort = Base Yield - Flat Interest
            # - Subsidy/Comm = Total Yield - Base Yield
            int_amort = base_income - current_flat_interest
            inc_gap = eff_income - base_income
            
            # Pro-rata split of the incremental gap between subsidy and commission
            total_inc_items = subsidy - commission
            if total_inc_items != 0:
                subsidy_inc = inc_gap * (subsidy / total_inc_items)
                comm_exp = inc_gap * (commission / total_inc_items)
            else:
                subsidy_inc = comm_exp = 0
                
        else:
            # Standard Model:
            # - Pro-rata split of the total gap (Eff Income - Flat Interest)
            net_amort = eff_income - current_flat_interest
            int_amort = 0 # Not used in standard display
            if total_upfront != 0:
                subsidy_inc = net_amort * (subsidy / total_upfront)
                comm_exp = net_amort * (commission / total_upfront)
            else:
                subsidy_inc = comm_exp = 0
            
        schedule.append({
            "Period": period,
            "Payment": payment,
            "Customer Interest": current_flat_interest,
            "Int. Amort": int_amort,
            "Subsidy Inc.": subsidy_inc,
            "Comm. Exp.": comm_exp,
            "Net Lender Income": eff_income,
            "Eff. Principal": eff_principal,
            "Balance (Eff.)": max(0, remaining_balance_eff)
        })
        
    return pd.DataFrame(schedule)

def main():
    parser = argparse.ArgumentParser(description="Advanced Microfinance IRR and EIR Calculator")
    parser.add_argument("principal", type=float, help="Total loan amount")
    parser.add_argument("interest_flat_monthly", type=float, help="Standard monthly flat interest rate (%)")
    parser.add_argument("term", type=int, help="Loan term (number of periods)")
    parser.add_argument("--frequency", choices=['M', 'W', 'B'], default='M', help="Payment frequency")
    parser.add_argument("--down-payment", "-d", type=float, default=0, help="Down payment amount")
    parser.add_argument("--grace", type=int, default=0, help="Principal grace period (interest-only)")
    parser.add_argument("--promo-months", type=int, default=0, help="Promotion period (number of periods)")
    parser.add_argument("--promo-rate", type=float, default=0, help="Monthly flat rate during promotion (%)")
    parser.add_argument("--promo-mode", choices=['spread', 'delayed'], default='spread',
                        help="spread: Even payments across term | delayed: Lower payments during promo")
    parser.add_argument("--fees", type=float, default=0, help="Upfront fees paid by borrower")
    parser.add_argument("--subsidy", type=float, default=0, help="Upfront subsidy paid by dealer/third-party")
    parser.add_argument("--commission", type=float, default=0, help="Upfront commission paid to dealer/agent")
    parser.add_argument("--round-to", type=float, default=1000, help="Rounding amount (default: 0 for exact)")
    parser.add_argument("--mode", choices=['standard', 'incremental'], default='standard',
                        help="standard: Pro-rata allocation | incremental: Base vs. Total yield analysis")


    args = parser.parse_args()

    # 1. Frequency Conversions
    freq_map = {'M': 12, 'W': 52, 'B': 26}
    periods_per_year = freq_map[args.frequency]
    
    financed_amount = args.principal - args.down_payment
    
    # Calculate Periodic Rates
    if args.frequency == 'M':
        r_std = args.interest_flat_monthly / 100
        r_promo = args.promo_rate / 100
    elif args.frequency == 'W':
        r_std = (args.interest_flat_monthly / 4) / 100
        r_promo = (args.promo_rate / 4) / 100
    else: # Bi-weekly
        r_std = (args.interest_flat_monthly / 2) / 100
        r_promo = (args.promo_rate / 2) / 100

    # 2. Calculate the TARGET TOTAL amount
    interest_promo_per_period = financed_amount * r_promo
    interest_std_per_period = financed_amount * r_std
    
    total_interest_promo = interest_promo_per_period * args.promo_months
    total_interest_std = interest_std_per_period * max(0, args.term - args.promo_months)
    
    total_to_pay = financed_amount + total_interest_promo + total_interest_std
    
    # 3. Determine Payments
    payments = []
    running_total_paid = 0
    
    # Rounding logic helper
    def round_pmt(val):
        if args.round_to <= 0: return val
        return math.ceil(val / args.round_to) * args.round_to

    # Standard values for 'spread' mode
    raw_payment_spread = total_to_pay / args.term
    rounded_payment_spread = round_pmt(raw_payment_spread)
    
    # Standard values for 'delayed' mode
    monthly_principal = financed_amount / args.term
    rounded_promo_payment = round_pmt(monthly_principal + interest_promo_per_period)
    rounded_standard_payment = round_pmt(monthly_principal + interest_std_per_period)

    for i in range(args.term - 1):
        period = i + 1
        
        # Check for Grace Period (Principal Grace)
        if period <= args.grace:
            payment = interest_promo_per_period if period <= args.promo_months else interest_std_per_period
        else:
            if args.promo_mode == 'delayed':
                current_target = rounded_promo_payment if period <= args.promo_months else rounded_standard_payment
            else:
                current_target = rounded_payment_spread
            
            # Safety check: don't overpay before last month
            payment = current_target if (running_total_paid + current_target) < total_to_pay else max(0, total_to_pay - running_total_paid)
        
        payments.append(payment)
        running_total_paid += payment
        
    # Last payment
    last_payment = max(0, total_to_pay - running_total_paid)
    payments.append(last_payment)
    
    # 4. Calculate IRR and EIR
    # Net disbursement (Lender Perspective) = Financed - Fees - Subsidy + Commission
    net_financed = financed_amount - args.fees - args.subsidy + args.commission
    cash_flows = [net_financed] + [-p for p in payments]
    periodic_irr = calculate_irr_from_cash_flows(cash_flows)
    
    if periodic_irr is not None:
        annual_irr = periodic_irr * periods_per_year * 100
        annual_eir = ((1 + periodic_irr)**periods_per_year - 1) * 100
    else:
        periodic_irr = annual_irr = annual_eir = 0.0

    # 5. Generate Schedule
    df_schedule = generate_amortization_schedule(
        financed_amount, net_financed, payments, periodic_irr, args.promo_months, 
        interest_promo_per_period, interest_std_per_period,
        args.fees, args.subsidy, args.commission, mode=args.mode
    )

    # 6. Display Results
    freq_names = {'M': 'Monthly', 'W': 'Weekly', 'B': 'Bi-weekly'}
    print("\n" + "="*125)
    print(f"           MICROFINANCE LOAN SUMMARY ({freq_names[args.frequency]}) - MODE: {args.mode.upper()}")
    print("="*125)
    summary_data = {
        "Parameter": [
            "Total Principal",
            "Down Payment",
            "Financed Amount", 
            "Borrower Fees",
            "Dealer Subsidy",
            "Agent Commission",
            "Net Disbursement",
            "Standard Monthly Rate",
            "Promo Monthly Rate",
            "Promo Duration",
            "Promo Mode",
            "Target Total to Pay",
            "Promo Payment (Est.)",
            "Standard Payment (Est.)",
            "Last Payment"
        ],
        "Value": [
            f"{args.principal:,.2f}",
            f"{args.down_payment:,.2f}",
            f"{financed_amount:,.2f}", 
            f"{args.fees:,.2f}",
            f"{args.subsidy:,.2f}",
            f"{args.commission:,.2f}",
            f"{net_financed:,.2f}",
            f"{args.interest_flat_monthly:.4f}%",
            f"{args.promo_rate:.4f}%",
            f"{args.promo_months} Periods",
            args.promo_mode.upper(),
            f"{total_to_pay:,.2f}",
            f"{payments[0]:,.2f}",
            f"{rounded_standard_payment:,.2f}" if args.promo_mode == 'delayed' else f"{rounded_payment_spread:,.2f}",
            f"{last_payment:,.2f}"
        ]
    }
    print(pd.DataFrame(summary_data).to_string(index=False))
    
    print("\n" + "-"*110)
    print(f"             EFFECTIVE RATES (With Dual-Rate Impact)")
    print("-"*110)
    rates_data = {
        "Rate Type": ["Annual Nominal (Weighted)", "Annual IRR", "Annual EIR (Effective)"],
        "Value": [f"{ ((total_interest_promo + total_interest_std)/financed_amount)/(args.term/periods_per_year)*100 :.2f}%", f"{annual_irr:.2f}%", f"{annual_eir:.2f}%"]
    }
    print(pd.DataFrame(rates_data).to_string(index=False))

    print("\n" + "-"*125)
    print("                FULL AMORTIZATION SCHEDULE (Lender Yield Breakdown)")
    print("-"*125)
    pd.options.display.float_format = '{:,.2f}'.format
    if args.mode == 'incremental':
        cols = ["Period", "Payment", "Customer Interest", "Int. Amort", "Subsidy Inc.", "Comm. Exp.", "Net Lender Income", "Eff. Principal", "Balance (Eff.)"]
    else:
        cols = ["Period", "Payment", "Customer Interest", "Subsidy Inc.", "Comm. Exp.", "Net Lender Income", "Eff. Principal", "Balance (Eff.)"]
    print(df_schedule[cols].to_string(index=False))
    print("="*125 + "\n")

if __name__ == "__main__":
    main()
