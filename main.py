import argparse
import pandas as pd
import numpy as np

def calculate_simple_interest(principal, rate, time_years):
    """
    Calculate simple interest.
    Formula: I = P * R * T
    """
    return principal * (rate / 100) * time_years

def calculate_compound_interest(principal, rate, time_years, compounds_per_year=12):
    """
    Calculate compound interest.
    Formula: A = P(1 + r/n)^(nt)
    Interest = A - P
    """
    amount = principal * (1 + (rate / 100) / compounds_per_year) ** (compounds_per_year * time_years)
    return amount - principal

def calculate_irr(principal, monthly_payment, n_months):
    """
    Calculate the monthly IRR using the Newton-Raphson method.
    Solves P = M * (1 - (1+r)**-n) / r
    """
    if monthly_payment * n_months <= principal:
        return 0.0

    # Initial guess for monthly rate (flat rate is a good start)
    r = (monthly_payment * n_months / principal - 1) / n_months
    
    for _ in range(100):
        # f(r) = M * (1 - (1+r)**-n) / r - P
        # f'(r) = M * [ (n * r * (1+r)**(-n-1) - (1 - (1+r)**-n) ) / r**2 ]
        
        f_r = monthly_payment * (1 - (1 + r)**-n_months) / r - principal
        f_prime_r = monthly_payment * ( (n_months * r * (1 + r)**(-n_months - 1) - (1 - (1 + r)**-n_months)) / r**2 )
        
        new_r = r - f_r / f_prime_r
        if abs(new_r - r) < 1e-7:
            return new_r
        r = new_r
        
    return r

def calculate_loan_details(total_principal, down_payment, monthly_interest_rate_flat, term_months):
    """
    Calculate loan details including Flat Rate, IRR, and EIR.
    """
    principal = total_principal - down_payment
    monthly_interest_flat = principal * (monthly_interest_rate_flat / 100)
    monthly_principal = principal / term_months
    monthly_payment = monthly_interest_flat + monthly_principal
    total_interest = monthly_interest_flat * term_months
    total_payment = principal + total_interest
    
    flat_rate_annual = monthly_interest_rate_flat * 12
    monthly_irr = calculate_irr(principal, monthly_payment, term_months)
    eir_annual = ((1 + monthly_irr)**12 - 1) * 100
    irr_annual = monthly_irr * 12 * 100
    
    data = {
        "Description": [
            "Total Principal",
            "Down Payment",
            "Financed Amount",
            "Loan Term (Months)",
            "Monthly Interest (Flat)",
            "Monthly Principal",
            "Monthly Total Payment",
            "Total Interest",
            "Total Amount to Pay (Excl. Down)",
            "Flat Rate (Annual %)",
            "IRR (Annual %)",
            "EIR (Annual %)"
        ],
        "Value": [
            f"{total_principal:,.2f}",
            f"{down_payment:,.2f}",
            f"{principal:,.2f}",
            f"{term_months}",
            f"{monthly_interest_flat:,.2f}",
            f"{monthly_principal:,.2f}",
            f"{monthly_payment:,.2f}",
            f"{total_interest:,.2f}",
            f"{total_payment:,.2f}",
            f"{flat_rate_annual:.2f}%",
            f"{irr_annual:.2f}%",
            f"{eir_annual:.2f}%"
        ]
    }
    
    return pd.DataFrame(data)

def main():
    parser = argparse.ArgumentParser(description="Loan Interest Calculator")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Subcommand: basic
    basic_parser = subparsers.add_parser("basic", help="Basic interest calculation")
    basic_parser.add_argument("principal", type=float, help="The initial amount of money")
    basic_parser.add_argument("rate", type=float, help="The annual interest rate (in percentage)")
    basic_parser.add_argument("term_months", type=float, help="The loan term in months")
    basic_parser.add_argument("--down-payment", "-d", type=float, default=0, help="Down payment amount")
    basic_parser.add_argument("--compound", action="store_true", help="Calculate compound interest")
    basic_parser.add_argument("--n", type=int, default=12, help="Compounding periods per year")

    # Subcommand: loan
    loan_parser = subparsers.add_parser("loan", help="Detailed loan calculation (Flat vs Effective)")
    loan_parser.add_argument("principal", type=float, help="Total loan amount")
    loan_parser.add_argument("interest_flat", type=float, help="Monthly flat interest rate (in percentage)")
    loan_parser.add_argument("term", type=int, help="Loan term in months")
    loan_parser.add_argument("--down-payment", "-d", type=float, default=0, help="Down payment amount")

    args = parser.parse_args()

    if args.command == "basic":
        principal = args.principal - args.down_payment
        time_years = args.term_months / 12
        if args.compound:
            interest = calculate_compound_interest(principal, args.rate, time_years, args.n)
            total_amount = principal + interest
            # For compound interest, EIR is mathematically (1 + r/n)^n - 1
            eir = ((1 + (args.rate / 100) / args.n) ** args.n - 1) * 100
            irr = eir # Annualized IRR and EIR are same in this context
            print(f"Compound Interest: {interest:.2f}")
        else:
            interest = calculate_simple_interest(principal, args.rate, time_years)
            total_amount = principal + interest
            # Calculate IRR assuming monthly installments (Flat Rate model)
            monthly_payment = total_amount / args.term_months
            monthly_irr = calculate_irr(principal, monthly_payment, int(args.term_months))
            irr = monthly_irr * 12 * 100
            eir = ((1 + monthly_irr) ** 12 - 1) * 100
            print(f"Simple Interest: {interest:.2f}")
        
        print(f"Financed Amount: {principal:.2f}")
        print(f"Total Amount to Pay: {total_amount:.2f}")
        print(f"Annual IRR: {irr:.2f}%")
        print(f"Annual EIR: {eir:.2f}%")

    elif args.command == "loan":
        df = calculate_loan_details(args.principal, args.down_payment, args.interest_flat, args.term)
        print("\n--- Loan Interest Details ---")
        print(df.to_string(index=False))
        print("-----------------------------\n")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
