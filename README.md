# Loan Interest Calculator Pro (Laos Microfinance Edition)

A professional suite of Python tools designed for the unique requirements of the Laos microfinance market, including Flat Rates, Grace Periods, Promotional Campaigns, and Revolving Credit.

---

## 1. Advanced Microfinance Calculator (`irr_eir_details.py`)
The primary tool for term loans (Agricultural, Business, and Group loans). It specializes in **Flat Interest Rate** products while revealing the **True Cost (IRR/EIR)**.

### How it Works
1.  **Target Total Calculation:** The script calculates the total amount the customer must pay back by adding the Principal to the total interest (calculated using the flat rate for each period, minus any interest-free or low-rate promo months).
2.  **Payment Determination:**
    *   **In `spread` mode:** It divides the Target Total by the total term to get an even payment.
    *   **In `delayed` mode:** It calculates two different payments: a lower one for the promo period (Principal + Promo Interest) and a standard one for the remaining term (Principal + Standard Interest).
3.  **Rounding:** Every payment is rounded **UP** to the nearest 1,000 LAK (or your custom `--round-to` amount).
4.  **Final Adjustment:** Because of rounding, the last payment is automatically reduced so the total paid exactly matches the target.
5.  **IRR/EIR Analysis:** It performs a Newton-Raphson root-finding algorithm on the actual cash flows to find the "True Cost" interest rate.

### Arguments Explained
*   `principal`: The total loan amount (e.g., 35000000 for 35M LAK).
*   `interest_flat_monthly`: The standard monthly flat interest rate (e.g., 1.59).
*   `term`: The total number of payment periods (e.g., 18).
*   `--frequency`: **M** (Monthly), **W** (Weekly), **B** (Bi-weekly).
*   `--grace`: Number of periods where the customer pays **only interest** (Principal Grace).
*   `--promo-months`: Number of initial periods with a special interest rate.
*   `--promo-rate`: The special monthly flat rate during the promo period (defaults to 0%).
*   `--promo-mode`: **spread** (default) or **delayed** (low initial payments).
*   `--fees`: Any upfront processing fees deducted from the disbursed amount.
*   `--round-to`: Amount to round payments up to (defaults to 1000 for LAK).

### Formula Reference: Term Loans
*   **Total Flat Interest:** 
    $$I_{total} = (P \times r_{promo} \times T_{promo}) + (P \times r_{std} \times (T_{total} - T_{promo}))$$
*   **Total Target to Pay:** 
    $$Target = Principal + I_{total}$$
*   **Monthly Payment (Rounded):** 
    $$PMT_{rounded} = \lceil (\frac{P}{T_{total}} + I_{periodic}) / Rounding \rceil \times Rounding$$
*   **Amortization - Flat Model (Month $t$):**
    *   *Flat Interest:* $I_{flat, t} = P \times r_{flat}$
    *   *Flat Principal:* $P_{flat, t} = PMT_t - I_{flat, t}$
*   **Amortization - Effective Model (Month $t$):**
    *   *Effective Interest:* $I_{eff, t} = Balance_{eff, t-1} \times PeriodicIRR$
    *   *Effective Principal:* $P_{eff, t} = PMT_t - I_{eff, t}$
    *   *Remaining Balance:* $Balance_{eff, t} = Balance_{eff, t-1} - P_{eff, t}$
*   **The IRR Equation (NPV):** The script solves for $r$ where:
    $$0 = -NetDisbursed + \sum_{t=1}^{n} \frac{PMT_t}{(1+r)^t}$$

### Example Usage Gallery
```bash
# Basic Term Loan (35M LAK, 1.59%, 18 months)
python3 irr_eir_details.py 35399000 1.59 18

# Weekly Group Loan (24 weeks frequency)
python3 irr_eir_details.py 10000000 1.5 24 --frequency W

# Bi-weekly Loan (12 periods)
python3 irr_eir_details.py 20000000 1.2 12 --frequency B

# Agricultural Loan (3-month Interest-Only Grace Period)
python3 irr_eir_details.py 50000000 1.0 12 --grace 3

# Delayed Promo (0.99% for 6 months, then 1.59%)
python3 irr_eir_details.py 35399000 1.59 18 --promo-months 6 --promo-rate 0.99 --promo-mode delayed

# Spread Promo (0% for 3 months, savings spread across 18 months)
python3 irr_eir_details.py 35399000 1.59 18 --promo-months 3 --promo-mode spread

# Loan with Upfront Processing Fees (500,000 LAK)
python3 irr_eir_details.py 35399000 1.59 18 --fees 500000

# Custom Rounding (Round up to nearest 5,000 LAK)
python3 irr_eir_details.py 35399000 1.59 18 --round-to 5000
```

---

## 2. Revolving Credit Calculator (`revolving_calc.py`)
Used for Lines of Credit (LOC) and overdraft products where the balance changes daily.

### How it Works
1.  **Daily Ledger:** Maps every transaction to a calendar and tracks the closing balance for every single day.
2.  **Payment Hierarchy:** Repayments are applied in a specific order:
    *   **1. Fees** (Drawdown, Monthly, and Over-limit fees).
    *   **2. Interest** (Accrued daily interest).
    *   **3. Principal** (The main borrowed amount).
3.  **Capitalization:** Unpaid interest and fees are tracked separately and repaid first during the next payment.
4.  **Over-limit Tracking:** Monitors the maximum balance reached each month. If it exceeds the `--limit`, a penalty is calculated on the last day of the month.
5.  **True Cost (EIR):** It finds the "Daily IRR" of all cash flows (withdrawals, fees, penalties, and repayments) and compounds it to show the Annual EIR.

### Arguments Explained
*   `--limit`: Maximum credit limit approved.
*   `--rate`: Annual nominal interest rate (e.g., 18.00).
*   `--drawdown-fee`: Percentage fee charged per withdrawal.
*   `--monthly-fee`: Fixed monthly maintenance fee.
*   `--overlimit-fee-flat`: Fixed penalty if balance > limit.
*   `--overlimit-fee-pct`: Percentage penalty on excess amount.
*   `--trans`: Transactions as `YYYY-MM-DD:Amount` (Withdrawal +, Repayment -).

### Formula Reference: Revolving Credit
*   **Daily Interest:** 
    $$I_{daily} = \frac{Balance_{principal} \times (Rate_{annual}/100)}{365}$$
*   **Over-limit Penalty Fee:** 
    $$Fee_{flat} + ((MaxBalance_{month} - Limit) \times \frac{Fee_{pct}}{100})$$
*   **Annual EIR:** 
    $$EIR = (1 + DailyIRR)^{365} - 1$$

### Example Usage Gallery
```bash
# Basic Revolving Account (Multiple Transactions)
python3 revolving_calc.py --limit 50000000 --rate 18 --trans 2024-01-01:10000000 2024-02-01:-2000000 2024-03-01:5000000

# Revolving with Drawdown Fees (3%) and Monthly Fees (50,000 LAK)
python3 revolving_calc.py --limit 50000000 --rate 18 --drawdown-fee 3 --monthly-fee 50000 --trans 2024-01-01:10000000

# Revolving with Over-limit Penalties (50k flat + 5% of excess)
python3 revolving_calc.py --limit 10000 \
  --rate 18 \
  --overlimit-fee-flat 50 \
  --overlimit-fee-pct 5 \
  --trans 2024-01-15:12000 2024-02-15:-500
```

---

## 3. Basic Utility Calculator (`main.py`)
A lightweight tool for quick interest checks and simple comparisons.

### Arguments Explained
*   `principal`: Initial amount.
*   `rate`: Annual rate (for `basic`) or monthly flat rate (for `loan`).
*   `term_months`: Term in months.
*   `--compound`: Enable compound interest (default is simple).
*   `--n`: Number of compounding periods per year (e.g., 12 for monthly, 4 for quarterly).

### Formula Reference: Basic Utilities
*   **Simple Interest:** 
    $$I = P \times \frac{Rate}{100} \times \frac{Months}{12}$$
*   **Compound Interest:** 
    $$A = P \times (1 + \frac{Rate/100}{n})^{n \times \frac{Months}{12}}$$

### Example Usage Gallery
```bash
# Simple Interest (Basic Check)
python3 main.py basic 1000000 5 24

# Compound Interest (Compounded Quarterly, n=4)
python3 main.py basic 1000000 5 12 --compound --n 4

# Quick Flat vs Effective Comparison Table
python3 main.py loan 100000000 1 12
```

---

## Installation & Requirements
Requires Python 3.x and the following libraries:
```bash
pip install pandas numpy
```

## Running Tests
To verify the math across all scripts:
```bash
python3 test_calc.py
```
########################
  1. irr_eir_details.py (Advanced Term Loans) - Verified
   * Rounding: Uses math.ceil for rounding up to any custom amount (default 1,000 LAK).
   * Last Payment: Correctly adjusts to ensure the target total is met exactly.
   * Promo Modes: Fully supports both spread and delayed modes.
   * Dual-Rate Promo: Supports --promo-rate for special introductory periods (e.g., 0.99% for 6
     months).
   * Grace Periods: Correctly handles interest-only periods.
   * Frequency: Supports Weekly (W), Bi-weekly (B), and Monthly (M).
   * Schedule: Side-by-side table for Flat Principal/Interest vs Eff. Principal/Interest.


  2. revolving_calc.py (Revolving Credit) - Verified
   * Daily Ledger: Tracks balance and accrues interest day-by-day.
   * Multiple Transactions: Handles any number of withdrawals/repayments.
   * Over-limit Penalties: Includes both flat (--overlimit-fee-flat) and percentage
     (--overlimit-fee-pct) penalties.
   * Annual EIR: Accurately calculated using Daily IRR on actual cash flows.


  3. main.py (Utility Calculator) - Verified
   * Basic Commands: Supports simple/compound interest.
   * IRR/EIR Output: Now displays "True Cost" even for basic simple interest checks.
   * Comparison Table: The loan command generates the quick lookup table.

   ##########################