import unittest
from main import calculate_simple_interest, calculate_compound_interest, calculate_irr, calculate_loan_details

class TestLoanInterestCalc(unittest.TestCase):
    def test_simple_interest(self):
        # Principal: 1000, Rate: 5%, Time: 2 years
        interest = calculate_simple_interest(1000, 5, 2)
        self.assertEqual(interest, 100.0)

    def test_compound_interest(self):
        # Principal: 1000, Rate: 5%, Time: 2 years, Compounded monthly (12 times)
        interest = calculate_compound_interest(1000, 5, 2, 12)
        self.assertAlmostEqual(interest, 104.941322, places=2)

    def test_irr_calculation(self):
        # Principal: 100,000, Monthly Payment: 4,666.67, Months: 24
        # From previous test, IRR (Annual %) was 11.13%
        # Monthly IRR = 11.13 / 12 / 100 = 0.009275
        monthly_irr = calculate_irr(100000, 4666.67, 24)
        self.assertAlmostEqual(monthly_irr * 12 * 100, 11.13, places=1)

    def test_loan_details(self):
        # Principal: 100,000, Monthly Flat Rate: 0.5%, Term: 24 months
        df = calculate_loan_details(100000, 0.5, 24)
        
        # Check specific values from the dataframe
        self.assertEqual(df.loc[df['Description'] == 'Total Principal', 'Value'].values[0], '100,000.00')
        self.assertEqual(df.loc[df['Description'] == 'Flat Rate (Annual %)', 'Value'].values[0], '6.00%')
        self.assertEqual(df.loc[df['Description'] == 'Total Interest', 'Value'].values[0], '12,000.00')

if __name__ == "__main__":
    unittest.main()
