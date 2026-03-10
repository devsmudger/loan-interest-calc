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

def generate_amortization_schedule(net_principal, payments, periodic_irr, promo_periods, promo_interest_amt, standard_interest_amt):
    """
    Generate a month-by-month schedule showing both Flat and Effective (IRR) components.
    """
    schedule = []
    remaining_balance_eff = net_principal
    total_periods = len(payments)
    
    for idx, payment in enumerate(payments):
        period = idx + 1
        
        # Effective components based on IRR
        eff_interest = remaining_balance_eff * periodic_irr
        
        # For the final period, we ensure the balance hits exactly zero
        if period == total_periods:
            eff_principal = remaining_balance_eff
        else:
            eff_principal = payment - eff_interest
            
        remaining_balance_eff -= eff_principal
        
        # Flat interest logic: use promo amount during promo period, otherwise standard
        current_flat_interest = promo_interest_amt if period <= promo_periods else standard_interest_amt
        current_flat_principal = payment - current_flat_interest
        
        schedule.append({
            "Period": period,
            "Payment": payment,
            "Flat Principal": current_flat_principal,
            "Flat Interest": current_flat_interest,
            "Eff. Principal": eff_principal,
            "Eff. Interest (IRR)": eff_interest,
            "Balance (Eff.)": max(0, remaining_balance_eff)
        })
        
    return pd.DataFrame(schedule)

def main():
    parser = argparse.ArgumentParser(description="Advanced Microfinance IRR and EIR Calculator")
    parser.add_argument("principal", type=float, help="Total loan amount")
    parser.add_argument("interest_flat_monthly", type=float, help="Standard monthly flat interest rate (%)")
    parser.add_argument("term", type=int, help="Loan term (number of periods)")
    parser.add_argument("--frequency", choices=['M', 'W', 'B'], default='M', help="Payment frequency")
    parser.add_argument("--grace", type=int, default=0, help="Principal grace period (interest-only)")
    parser.add_argument("--promo-months", type=int, default=0, help="Promotion period (number of periods)")
    parser.add_argument("--promo-rate", type=float, default=0, help="Monthly flat rate during promotion (%)")
    parser.add_argument("--promo-mode", choices=['spread', 'delayed'], default='spread',
                        help="spread: Even payments across term | delayed: Lower payments during promo")
    parser.add_argument("--fees", type=float, default=0, help="Upfront fees")
    parser.add_argument("--round-to", type=float, default=1000, help="Rounding amount (default: 1000)")

    args = parser.parse_args()

    # 1. Frequency Conversions
    freq_map = {'M': 12, 'W': 52, 'B': 26}
    periods_per_year = freq_map[args.frequency]
    
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
    interest_promo_per_period = args.principal * r_promo
    interest_std_per_period = args.principal * r_std
    
    total_interest_promo = interest_promo_per_period * args.promo_months
    total_interest_std = interest_std_per_period * max(0, args.term - args.promo_months)
    
    total_to_pay = args.principal + total_interest_promo + total_interest_std
    
    # 3. Determine Payments
    payments = []
    running_total_paid = 0
    
    # Standard values for 'spread' mode
    raw_payment_spread = total_to_pay / args.term
    rounded_payment_spread = math.ceil(raw_payment_spread / args.round_to) * math.ceil(args.round_to)
    
    # Standard values for 'delayed' mode
    monthly_principal = args.principal / args.term
    rounded_promo_payment = math.ceil((monthly_principal + interest_promo_per_period) / args.round_to) * args.round_to
    rounded_standard_payment = math.ceil((monthly_principal + interest_std_per_period) / args.round_to) * args.round_to

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
    net_principal = args.principal - args.fees
    cash_flows = [net_principal] + [-p for p in payments]
    periodic_irr = calculate_irr_from_cash_flows(cash_flows)
    
    if periodic_irr is not None:
        annual_irr = periodic_irr * periods_per_year * 100
        annual_eir = ((1 + periodic_irr)**periods_per_year - 1) * 100
    else:
        periodic_irr = annual_irr = annual_eir = 0.0

    # 5. Generate Schedule
    df_schedule = generate_amortization_schedule(
        net_principal, payments, periodic_irr, args.promo_months, interest_promo_per_period, interest_std_per_period
    )

    # 6. Display Results
    freq_names = {'M': 'Monthly', 'W': 'Weekly', 'B': 'Bi-weekly'}
    print("\n" + "="*110)
    print(f"           MICROFINANCE LOAN SUMMARY ({freq_names[args.frequency]})")
    print("="*110)
    summary_data = {
        "Parameter": [
            "Loan Principal", 
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
        "Value": [f"{ ((total_interest_promo + total_interest_std)/args.principal)/(args.term/periods_per_year)*100 :.2f}%", f"{annual_irr:.2f}%", f"{annual_eir:.2f}%"]
    }
    print(pd.DataFrame(rates_data).to_string(index=False))

    print("\n" + "-"*110)
    print("                FULL AMORTIZATION SCHEDULE (Dual Rate Comparison)")
    print("-"*110)
    pd.options.display.float_format = '{:,.2f}'.format
    cols = ["Period", "Payment", "Flat Principal", "Flat Interest", "Eff. Principal", "Eff. Interest (IRR)", "Balance (Eff.)"]
    print(df_schedule[cols].to_string(index=False))
    print("="*110 + "\n")

if __name__ == "__main__":
    main()
