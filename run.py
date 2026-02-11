from main import AdvancedPortfolioManager


manager = AdvancedPortfolioManager(
    initial_capital=10000,
    risk_tolerance=5,
    tax_status='standard'
)

investment_universe = [
    'AAPL', 'GOOGL', 'MSFT', 'AMZN',
    'JNJ', 'PG', 'KO', 'SPY'
]

result = manager.optimize_portfolio(investment_universe)

print("\nPORTFOLIO WEIGHTS")
print(result['weights'])

print("\nRISK PROFILE")
print(result['risk_profile'])

print("\nTAX EFFICIENCY")
print(result['tax_efficiency'])

print("\nLOSS HARVESTING")
print(result['loss_harvesting'])
