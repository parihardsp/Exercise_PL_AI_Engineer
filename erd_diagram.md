# 🗄️ Database Entity-Relationship Diagram (ERD)

This document visualizes the database schema for the **Portfolio Analytics Agent**, including all 9 tables, fields, data types, primary keys (PK), foreign keys (FK), and relationship cardinalities.

---

## 📊 Complete Mermaid ERD

```mermaid
erDiagram
    SECTORS ||--o{ SECURITIES : "categorizes (1:N)"
    PORTFOLIOS ||--o{ HOLDINGS : "contains (1:N)"
    SECURITIES ||--o{ HOLDINGS : "held in (1:N)"
    PORTFOLIOS ||--o{ TRANSACTIONS : "records (1:N)"
    SECURITIES ||--o{ TRANSACTIONS : "traded in (1:N)"
    SECURITIES ||--o{ HISTORICAL_PRICES : "has prices (1:N)"
    PORTFOLIOS ||--o{ PORTFOLIO_PERFORMANCE : "tracks (1:N)"
    PORTFOLIOS ||--o{ RISK_METRICS : "evaluates (1:N)"
    BENCHMARKS ||--o{ PORTFOLIOS : "benchmarks (1:N)"

    SECTORS {
        INTEGER sector_id PK
        TEXT sector_name "UNIQUE, NOT NULL"
        TEXT sector_description
        TEXT industry_group
    }

    SECURITIES {
        INTEGER security_id PK
        TEXT symbol "UNIQUE, NOT NULL"
        TEXT company_name "NOT NULL"
        TEXT asset_type "CHECK: 'Stock' | 'Bond'"
        INTEGER sector_id FK "NULL for Bonds"
        REAL market_cap
        REAL current_price
        TEXT currency "DEFAULT 'USD'"
        TEXT exchange
        TEXT country
        DATE listing_date
        DATE maturity_date "Only for Bonds"
        REAL coupon_rate "Only for Bonds"
    }

    BENCHMARKS {
        INTEGER benchmark_id PK
        TEXT benchmark_name "UNIQUE, NOT NULL"
        TEXT benchmark_symbol
        TEXT benchmark_type
        TEXT description
        DATE inception_date
    }

    PORTFOLIOS {
        INTEGER portfolio_id PK
        TEXT portfolio_name "UNIQUE, NOT NULL"
        DATE creation_date
        TEXT target_risk_level "'High' | 'Medium' | 'Low'"
        REAL total_aum "Assets Under Management"
        TEXT strategy_type "'Growth' | 'Income' | 'Value' | 'ESG' | 'Index'"
        TEXT benchmark_index "Symbol linking to Benchmark"
        TEXT status "'Active' | 'Passive'"
    }

    HOLDINGS {
        INTEGER holding_id PK
        INTEGER portfolio_id FK "NOT NULL"
        INTEGER security_id FK "NOT NULL"
        REAL quantity "NOT NULL"
        REAL purchase_price
        DATE purchase_date
        REAL current_weight "Weight in portfolio (0.0 - 1.0)"
        REAL cost_basis "Total invested amount"
    }

    TRANSACTIONS {
        INTEGER transaction_id PK
        INTEGER portfolio_id FK "NOT NULL"
        INTEGER security_id FK "NOT NULL"
        TEXT transaction_type "'BUY' | 'SELL'"
        REAL quantity "NOT NULL"
        REAL price "NOT NULL"
        DATE transaction_date "NOT NULL"
        REAL fees "DEFAULT 0"
        DATE settlement_date
        TEXT notes
    }

    HISTORICAL_PRICES {
        INTEGER price_id PK
        INTEGER security_id FK "NOT NULL"
        DATE price_date "NOT NULL"
        REAL open_price
        REAL high_price
        REAL low_price
        REAL close_price "NOT NULL"
        INTEGER volume
        REAL adjusted_close
    }

    PORTFOLIO_PERFORMANCE {
        INTEGER performance_id PK
        INTEGER portfolio_id FK "NOT NULL"
        DATE performance_date "NOT NULL"
        REAL nav "Net Asset Value"
        REAL total_return_1m "1-month return"
        REAL total_return_3m "3-month return"
        REAL total_return_6m "6-month return"
        REAL total_return_1y "1-year return"
        REAL volatility
        REAL sharpe_ratio
        REAL max_drawdown
    }

    RISK_METRICS {
        INTEGER risk_id PK
        INTEGER portfolio_id FK "NOT NULL"
        DATE calculation_date "NOT NULL"
        REAL var_95 "Value at Risk 95%"
        REAL var_99 "Value at Risk 99%"
        REAL cvar_95 "Conditional VaR"
        REAL beta "Sensitivity to market"
        REAL correlation_sp500 "Correlation with S&P 500"
        REAL tracking_error
        REAL information_ratio
        REAL sortino_ratio
    }
```

---

## 🔍 Key Relational Insights for Queries & Calculations

### 1. **Sector Exposure Calculation Join Path**
```
PORTFOLIOS (portfolio_id / portfolio_name)
    ↓ (1:N)
HOLDINGS (current_weight, quantity)
    ↓ (N:1)
SECURITIES (asset_type == 'Stock', sector_id)
    ↓ (N:1)
SECTORS (sector_name)
```
* **Filter:** `securities.asset_type = 'Stock'` (bonds have `sector_id IS NULL`).
* **Aggregation:** `SUM(holdings.current_weight)` grouped by `sectors.sector_name`.

### 2. **Portfolio Valuation & Holdings Query**
```sql
SELECT 
    p.portfolio_name,
    s.symbol,
    s.company_name,
    sec.sector_name,
    h.quantity,
    s.current_price,
    (h.quantity * s.current_price) AS market_value,
    h.current_weight
FROM portfolios p
JOIN holdings h ON p.portfolio_id = h.portfolio_id
JOIN securities s ON h.security_id = s.security_id
LEFT JOIN sectors sec ON s.sector_id = sec.sector_id
WHERE p.portfolio_name = 'Tech Innovation Fund';
```

### 3. **Performance & Risk Tracking Path**
* `PORTFOLIOS` connects 1:N to `PORTFOLIO_PERFORMANCE` (keyed on `portfolio_id, performance_date`).
* `PORTFOLIOS` connects 1:N to `RISK_METRICS` (keyed on `portfolio_id, calculation_date`).
