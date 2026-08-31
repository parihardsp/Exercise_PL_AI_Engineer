# 📊 Portfolio Analytics Agent — Evaluation & Benchmark Report

**Generated:** 2026-08-30 04:38:34  
**Questions Evaluated:** 12 Ground Truth Test Cases

## 📈 Executive Summary Scorecard

| Metric | Result | Status |
| :--- | :---: | :---: |
| **Tool Routing Accuracy** | **100.0%** | ✅ PASSED |
| **Execution Success Rate** | **100.0%** | ✅ PASSED |
| **SQL Structural Similarity** | **87.5%** | ✅ PASSED |
| **Data / Result Match Rate** | **100.0%** | ✅ PASSED |
| **Average Execution Latency** | **4.73s** | ✅ PASSED |

## 🔍 Detailed Question-by-Question Breakdown

### 🔹 Question 1: How many portfolios do we have in total?

- **Type:** `text2sql` | **Difficulty:** `easy` | **Latency:** `2.21s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **100%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
SELECT COUNT(*) FROM portfolios;
```

**Generated Agent SQL:**
```sql
SELECT count(*) FROM portfolios;
```

**Ground Truth Data Output:**
```json
[
  {
    "COUNT(*)": 13
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "count(*)": 13
  }
]
```

**Formatted Agent Response Preview:**
> 1 row(s) returned....


---

### 🔹 Question 2: What are the names of all active portfolios?

- **Type:** `text2sql` | **Difficulty:** `easy` | **Latency:** `1.75s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **100%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
SELECT portfolio_name FROM portfolios WHERE status = 'Active';
```

**Generated Agent SQL:**
```sql
SELECT portfolio_name FROM portfolios WHERE status = 'Active';
```

**Ground Truth Data Output:**
```json
[
  {
    "portfolio_name": "Growth Equity Fund"
  },
  {
    "portfolio_name": "Conservative Income Fund"
  },
  {
    "portfolio_name": "Tech Innovation Fund"
  },
  {
    "portfolio_name": "Balanced Portfolio"
  },
  {
    "portfolio_name": "ESG Sustainable Fund"
  },
  {
    "portfolio_name": "Small Cap Value Fund"
  },
  {
    "portfolio_name": "International Equity Fund"
  },
  {
    "portfolio_name": "Fixed Income Plus"
  },
  {
    "portfolio_name": "Dividend Aristocrats Fund"
  },
  {
    "portfolio_name": "Emerging Markets Fund"
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "portfolio_name": "Growth Equity Fund"
  },
  {
    "portfolio_name": "Conservative Income Fund"
  },
  {
    "portfolio_name": "Tech Innovation Fund"
  },
  {
    "portfolio_name": "Balanced Portfolio"
  },
  {
    "portfolio_name": "ESG Sustainable Fund"
  },
  {
    "portfolio_name": "Small Cap Value Fund"
  },
  {
    "portfolio_name": "International Equity Fund"
  },
  {
    "portfolio_name": "Fixed Income Plus"
  },
  {
    "portfolio_name": "Dividend Aristocrats Fund"
  },
  {
    "portfolio_name": "Emerging Markets Fund"
  }
]
```

**Formatted Agent Response Preview:**
> 10 row(s) returned....


---

### 🔹 Question 3: Which securities are in the Technology sector?

- **Type:** `text2sql` | **Difficulty:** `easy` | **Latency:** `1.82s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **100%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
SELECT s.symbol, s.company_name FROM securities s JOIN sectors sec ON s.sector_id = sec.sector_id WHERE sec.sector_name = 'Technology';
```

**Generated Agent SQL:**
```sql
SELECT s.symbol, s.company_name FROM securities s JOIN sectors sec ON s.sector_id = sec.sector_id WHERE sec.sector_name = 'Technology';
```

**Ground Truth Data Output:**
```json
[
  {
    "symbol": "AAPL",
    "company_name": "Apple Inc."
  },
  {
    "symbol": "MSFT",
    "company_name": "Microsoft Corporation"
  },
  {
    "symbol": "GOOGL",
    "company_name": "Alphabet Inc."
  },
  {
    "symbol": "META",
    "company_name": "Meta Platforms Inc."
  },
  {
    "symbol": "NVDA",
    "company_name": "NVIDIA Corporation"
  },
  {
    "symbol": "AVGO",
    "company_name": "Broadcom Inc."
  },
  {
    "symbol": "CRM",
    "company_name": "Salesforce Inc."
  },
  {
    "symbol": "ORCL",
    "company_name": "Oracle Corporation"
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "symbol": "AAPL",
    "company_name": "Apple Inc."
  },
  {
    "symbol": "MSFT",
    "company_name": "Microsoft Corporation"
  },
  {
    "symbol": "GOOGL",
    "company_name": "Alphabet Inc."
  },
  {
    "symbol": "META",
    "company_name": "Meta Platforms Inc."
  },
  {
    "symbol": "NVDA",
    "company_name": "NVIDIA Corporation"
  },
  {
    "symbol": "AVGO",
    "company_name": "Broadcom Inc."
  },
  {
    "symbol": "CRM",
    "company_name": "Salesforce Inc."
  },
  {
    "symbol": "ORCL",
    "company_name": "Oracle Corporation"
  }
]
```

**Formatted Agent Response Preview:**
> 8 row(s) returned....


---

### 🔹 Question 4: What is the total Assets Under Management (AUM) for portfolios with high target risk level?

- **Type:** `text2sql` | **Difficulty:** `medium` | **Latency:** `1.81s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **100%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
SELECT SUM(total_aum) FROM portfolios WHERE target_risk_level = 'High';
```

**Generated Agent SQL:**
```sql
SELECT SUM(total_aum) FROM portfolios WHERE target_risk_level = 'High';
```

**Ground Truth Data Output:**
```json
[
  {
    "SUM(total_aum)": 85000000.0
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "SUM(total_aum)": 85000000.0
  }
]
```

**Formatted Agent Response Preview:**
> 1 row(s) returned....


---

### 🔹 Question 5: Show me the top 5 holdings by cost basis in the Growth Equity Fund

- **Type:** `text2sql` | **Difficulty:** `medium` | **Latency:** `1.95s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **91%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
SELECT h.holding_id, s.symbol, s.company_name, h.quantity, h.cost_basis FROM holdings h JOIN securities s ON h.security_id = s.security_id JOIN portfolios p ON h.portfolio_id = p.portfolio_id WHERE p.portfolio_name = 'Growth Equity Fund' ORDER BY h.cost_basis DESC LIMIT 5;
```

**Generated Agent SQL:**
```sql
SELECT s.symbol, s.company_name, h.cost_basis 
FROM holdings h 
JOIN securities s ON h.security_id = s.security_id 
JOIN portfolios p ON h.portfolio_id = p.portfolio_id 
WHERE p.portfolio_name = 'Growth Equity Fund' 
ORDER BY h.cost_basis DESC 
LIMIT 5;
```

**Ground Truth Data Output:**
```json
[
  {
    "holding_id": 1,
    "symbol": "AAPL",
    "company_name": "Apple Inc.",
    "quantity": 2500.0,
    "cost_basis": 438000.0
  },
  {
    "holding_id": 8,
    "symbol": "AMZN",
    "company_name": "Amazon.com Inc.",
    "quantity": 100.0,
    "cost_basis": 320000.0
  },
  {
    "holding_id": 2,
    "symbol": "MSFT",
    "company_name": "Microsoft Corporation",
    "quantity": 800.0,
    "cost_basis": 304400.0
  },
  {
    "holding_id": 3,
    "symbol": "NVDA",
    "company_name": "NVIDIA Corporation",
    "quantity": 400.0,
    "cost_basis": 288040.0
  },
  {
    "holding_id": 6,
    "symbol": "CRM",
    "company_name": "Salesforce Inc.",
    "quantity": 1000.0,
    "cost_basis": 185400.0
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "symbol": "AAPL",
    "company_name": "Apple Inc.",
    "cost_basis": 438000.0
  },
  {
    "symbol": "AMZN",
    "company_name": "Amazon.com Inc.",
    "cost_basis": 320000.0
  },
  {
    "symbol": "MSFT",
    "company_name": "Microsoft Corporation",
    "cost_basis": 304400.0
  },
  {
    "symbol": "NVDA",
    "company_name": "NVIDIA Corporation",
    "cost_basis": 288040.0
  },
  {
    "symbol": "CRM",
    "company_name": "Salesforce Inc.",
    "cost_basis": 185400.0
  }
]
```

**Formatted Agent Response Preview:**
> 5 row(s) returned....


---

### 🔹 Question 6: What is the average current price of securities in each sector?

- **Type:** `text2sql` | **Difficulty:** `medium` | **Latency:** `1.80s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **63%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
SELECT sec.sector_name, AVG(s.current_price) as avg_price FROM securities s JOIN sectors sec ON s.sector_id = sec.sector_id GROUP BY sec.sector_name ORDER BY avg_price DESC;
```

**Generated Agent SQL:**
```sql
SELECT s.sector_name, AVG(sec.current_price) AS average_current_price FROM sectors s JOIN securities sec ON s.sector_id = sec.sector_id GROUP BY s.sector_id, s.sector_name;
```

**Ground Truth Data Output:**
```json
[
  {
    "sector_name": "Consumer Discretionary",
    "avg_price": 3380.0
  },
  {
    "sector_name": "Technology",
    "avg_price": 719.245
  },
  {
    "sector_name": "Healthcare",
    "avg_price": 285.17
  },
  {
    "sector_name": "Automotive",
    "avg_price": 248.5
  },
  {
    "sector_name": "Financials",
    "avg_price": 201.2125
  },
  {
    "sector_name": "Consumer Staples",
    "avg_price": 173.8625
  },
  {
    "sector_name": "Energy",
    "avg_price": 128.575
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "sector_name": "Automotive",
    "average_current_price": 248.5
  },
  {
    "sector_name": "Consumer Discretionary",
    "average_current_price": 3380.0
  },
  {
    "sector_name": "Consumer Staples",
    "average_current_price": 173.8625
  },
  {
    "sector_name": "Energy",
    "average_current_price": 128.575
  },
  {
    "sector_name": "Financials",
    "average_current_price": 201.2125
  },
  {
    "sector_name": "Healthcare",
    "average_current_price": 285.17
  },
  {
    "sector_name": "Technology",
    "average_current_price": 719.245
  }
]
```

**Formatted Agent Response Preview:**
> 7 row(s) returned....


---

### 🔹 Question 7: For each portfolio, show the total value of Technology sector holdings and what percentage it represents of the total portfolio value

- **Type:** `text2sql` | **Difficulty:** `hard` | **Latency:** `3.47s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **57%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
WITH portfolio_tech_value AS (SELECT p.portfolio_id, p.portfolio_name, SUM(h.quantity * s.current_price) as tech_value FROM portfolios p JOIN holdings h ON p.portfolio_id = h.portfolio_id JOIN securities s ON h.security_id = s.security_id JOIN sectors sec ON s.sector_id = sec.sector_id WHERE sec.sector_name = 'Technology' GROUP BY p.portfolio_id, p.portfolio_name), portfolio_total_value AS (SELECT p.portfolio_id, SUM(h.quantity * s.current_price) as total_value FROM portfolios p JOIN holdings h ON p.portfolio_id = h.portfolio_id JOIN securities s ON h.security_id = s.security_id GROUP BY p.portfolio_id) SELECT ptv.portfolio_name, ptv.tech_value, ptv2.total_value, ROUND((ptv.tech_value / ptv2.total_value) * 100, 2) as tech_percentage FROM portfolio_tech_value ptv JOIN portfolio_total_value ptv2 ON ptv.portfolio_id = ptv2.portfolio_id ORDER BY tech_percentage DESC;
```

**Generated Agent SQL:**
```sql
SELECT 
    p.portfolio_name,
    SUM(h.quantity * s.current_price) AS tech_holding_value,
    (SUM(h.quantity * s.current_price) * 100.0 / p.total_aum) AS tech_percentage
FROM portfolios p
JOIN holdings h ON p.portfolio_id = h.portfolio_id
JOIN securities s ON h.security_id = s.security_id
JOIN sectors sec ON s.sector_id = sec.sector_id
WHERE sec.sector_name = 'Technology'
GROUP BY p.portfolio_id, p.portfolio_name, p.total_aum;
```

**Ground Truth Data Output:**
```json
[
  {
    "portfolio_name": "Tech Innovation Fund",
    "tech_value": 1565292.5,
    "total_value": 1565292.5,
    "tech_percentage": 100.0
  },
  {
    "portfolio_name": "Growth Equity Fund",
    "tech_value": 1866148.0,
    "total_value": 2204148.0,
    "tech_percentage": 84.67
  },
  {
    "portfolio_name": "Total International Index Fund",
    "tech_value": 1427086.0,
    "total_value": 2281686.0,
    "tech_percentage": 62.55
  },
  {
    "portfolio_name": "International Equity Fund",
    "tech_value": 346888.0,
    "total_value": 734928.0,
    "tech_percentage": 47.2
  },
  {
    "portfolio_name": "Total Stock Market Index Fund",
    "tech_value": 3093520.0,
    "total_value": 6622340.0,
    "tech_percentage": 46.71
  },
  {
    "portfolio_name": "Balanced Portfolio",
    "tech_value": 388704.0,
    "total_value": 1073279.0,
    "tech_percentage": 36.22
  },
  {
    "portfolio_name": "Emerging Markets Fund",
    "tech_value": 339095.0,
    "total_value": 1045100.0,
    "tech_percentage": 32.45
  },
  {
    "portfolio_name": "ESG Sustainable Fund",
    "tech_value": 272978.0,
    "total_value": 1007228.0,
    "tech_percentage": 27.1
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "portfolio_name": "Growth Equity Fund",
    "tech_holding_value": 1866148.0,
    "tech_percentage": 7.464592
  },
  {
    "portfolio_name": "Tech Innovation Fund",
    "tech_holding_value": 1565292.5,
    "tech_percentage": 4.8915390625
  },
  {
    "portfolio_name": "Balanced Portfolio",
    "tech_holding_value": 388704.0,
    "tech_percentage": 1.7668363636363635
  },
  {
    "portfolio_name": "ESG Sustainable Fund",
    "tech_holding_value": 272978.0,
    "tech_percentage": 1.8198533333333333
  },
  {
    "portfolio_name": "International Equity Fund",
    "tech_holding_value": 346888.0,
    "tech_percentage": 1.2388857142857144
  },
  {
    "portfolio_name": "Emerging Markets Fund",
    "tech_holding_value": 339095.0,
    "tech_percentage": 2.11934375
  },
  {
    "portfolio_name": "Total Stock Market Index Fund",
    "tech_holding_value": 3093520.0,
    "tech_percentage": 6.874488888888889
  },
  {
    "portfolio_name": "Total International Index Fund",
    "tech_holding_value": 1427086.0,
    "tech_percentage": 5.708344
  }
]
```

**Formatted Agent Response Preview:**
> 8 row(s) returned....


---

### 🔹 Question 8: Find portfolios that have holdings in more than 5 different sectors and show their diversification metrics

- **Type:** `text2sql` | **Difficulty:** `hard` | **Latency:** `35.57s`
- **Tool Routing:** Expected `sql_query` vs Actual `sql_query` (✅)
- **SQL Structural Similarity:** **40%**
- **Data / Result Match:** ✅

**Ground Truth SQL:**
```sql
WITH portfolio_sector_count AS (SELECT p.portfolio_id, p.portfolio_name, COUNT(DISTINCT sec.sector_id) as sector_count FROM portfolios p JOIN holdings h ON p.portfolio_id = h.portfolio_id JOIN securities s ON h.security_id = s.security_id JOIN sectors sec ON s.sector_id = sec.sector_id WHERE s.asset_type = 'Stock' GROUP BY p.portfolio_id, p.portfolio_name HAVING COUNT(DISTINCT sec.sector_id) > 5), portfolio_holdings_count AS (SELECT p.portfolio_id, COUNT(h.holding_id) as total_holdings FROM portfolios p JOIN holdings h ON p.portfolio_id = h.portfolio_id GROUP BY p.portfolio_id) SELECT psc.portfolio_name, psc.sector_count, phc.total_holdings, ROUND(CAST(psc.sector_count AS REAL) / phc.total_holdings, 3) as diversification_ratio FROM portfolio_sector_count psc JOIN portfolio_holdings_count phc ON psc.portfolio_id = phc.portfolio_id ORDER BY diversification_ratio DESC;
```

**Generated Agent SQL:**
```sql
SELECT 
    p.portfolio_id,
    p.portfolio_name,
    COUNT(DISTINCT s.sector_id) AS distinct_sectors_count
FROM portfolios p
JOIN holdings h ON p.portfolio_id = h.portfolio_id
JOIN securities s ON h.security_id = s.security_id
GROUP BY p.portfolio_id, p.portfolio_name
HAVING COUNT(DISTINCT s.sector_id) > 5;
```

**Ground Truth Data Output:**
```json
[
  {
    "portfolio_name": "Total Stock Market Index Fund",
    "sector_count": 6,
    "total_holdings": 12,
    "diversification_ratio": 0.5
  }
]
```

**Generated Agent Data Output:**
```json
[
  {
    "portfolio_id": 11,
    "portfolio_name": "Total Stock Market Index Fund",
    "distinct_sectors_count": 6
  }
]
```

**Formatted Agent Response Preview:**
> 1 row(s) returned....


---

### 🔹 Question 9: What are the sector exposures for the Tech Innovation Fund?

- **Type:** `exposure_calculator` | **Difficulty:** `medium` | **Latency:** `1.14s`
- **Tool Routing:** Expected `exposure_calculator` vs Actual `exposure_calculator` (✅)
- **Data / Result Match:** ✅

**Ground Truth Data Output:**
```json
{
  "expected_portfolio": "Tech Innovation Fund",
  "expected_result_type": "sector_exposure_breakdown"
}
```

**Generated Agent Data Output:**
```json
{
  "portfolio_name": "Tech Innovation Fund",
  "exposures": [
    {
      "sector": "Technology",
      "exposure_pct": 100.0
    }
  ],
  "total_equity_weight": 1.0
}
```

**Formatted Agent Response Preview:**
> **Sector Exposure for Tech Innovation Fund** (Equities Only)  - **Technology** : 100.00%...


---

### 🔹 Question 10: Calculate the sector exposure breakdown for international equity

- **Type:** `exposure_calculator` | **Difficulty:** `medium` | **Latency:** `0.84s`
- **Tool Routing:** Expected `exposure_calculator` vs Actual `exposure_calculator` (✅)
- **Data / Result Match:** ✅

**Ground Truth Data Output:**
```json
{
  "expected_portfolio": "International Equity Fund",
  "expected_result_type": "sector_exposure_breakdown"
}
```

**Generated Agent Data Output:**
```json
{
  "portfolio_name": "International Equity Fund",
  "exposures": [
    {
      "sector": "Energy",
      "exposure_pct": 38.0
    },
    {
      "sector": "Technology",
      "exposure_pct": 36.0
    },
    {
      "sector": "Automotive",
      "exposure_pct": 15.0
    },
    {
      "sector": "Consumer Staples",
      "exposure_pct": 11.0
    }
  ],
  "total_equity_weight": 1.0
}
```

**Formatted Agent Response Preview:**
> **Sector Exposure for International Equity Fund** (Equities Only)  - **Energy** : 38.00% - **Technology** : 36.00% - **Automotive** : 15.00% - **Consumer Staples** : 11.00%...


---

### 🔹 Question 11: What is the sector exposure breakdown for the portfolio with the highest total AUM?

- **Type:** `hybrid` | **Difficulty:** `hard` | **Latency:** `2.04s`
- **Tool Routing:** Expected `hybrid_exposure_tool` vs Actual `hybrid_exposure_tool` (✅)
- **SQL Structural Similarity:** **100%**
- **Data / Result Match:** ✅

**Generated Agent SQL:**
```sql
SELECT portfolio_name FROM portfolios ORDER BY total_aum DESC LIMIT 1;
```

**Ground Truth Data Output:**
```json
{
  "expected_portfolio": "Total Stock Market Index Fund",
  "expected_result_type": "sector_exposure_breakdown"
}
```

**Generated Agent Data Output:**
```json
{
  "portfolio_name": "Total Stock Market Index Fund",
  "exposures": [
    {
      "sector": "Technology",
      "exposure_pct": 48.98
    },
    {
      "sector": "Healthcare",
      "exposure_pct": 16.33
    },
    {
      "sector": "Financials",
      "exposure_pct": 14.29
    },
    {
      "sector": "Consumer Discretionary",
      "exposure_pct": 10.2
    },
    {
      "sector": "Automotive",
      "exposure_pct": 6.12
    },
    {
      "sector": "Consumer Staples",
      "exposure_pct": 4.08
    }
  ],
  "total_equity_weight": 0.98,
  "lookup_sql": "SELECT portfolio_name FROM portfolios ORDER BY total_aum DESC LIMIT 1;"
}
```

**Formatted Agent Response Preview:**
> **Sector Exposure for Total Stock Market Index Fund** (Equities Only)  - **Technology** : 48.98% - **Healthcare** : 16.33% - **Financials** : 14.29% - **Consumer Discretionary** : 10.20% - **Automotive** : 6.12% - **Consumer Staples** : 4.08%...


---

### 🔹 Question 12: Show the equity sector allocation for the top performing fund based on 1-year total return

- **Type:** `hybrid` | **Difficulty:** `hard` | **Latency:** `2.31s`
- **Tool Routing:** Expected `hybrid_exposure_tool` vs Actual `hybrid_exposure_tool` (✅)
- **SQL Structural Similarity:** **100%**
- **Data / Result Match:** ✅

**Generated Agent SQL:**
```sql
SELECT p.portfolio_name 
FROM portfolios p 
JOIN portfolio_performance pp ON p.portfolio_id = pp.portfolio_id 
GROUP BY p.portfolio_id, p.portfolio_name 
ORDER BY pp.total_return_1y DESC 
LIMIT 1;
```

**Ground Truth Data Output:**
```json
{
  "expected_portfolio": "Tech Innovation Fund",
  "expected_result_type": "sector_exposure_breakdown"
}
```

**Generated Agent Data Output:**
```json
{
  "portfolio_name": "Tech Innovation Fund",
  "exposures": [
    {
      "sector": "Technology",
      "exposure_pct": 100.0
    }
  ],
  "total_equity_weight": 1.0,
  "lookup_sql": "SELECT p.portfolio_name \nFROM portfolios p \nJOIN portfolio_performance pp ON p.portfolio_id = pp.portfolio_id \nGROUP BY p.portfolio_id, p.portfolio_name \nORDER BY pp.total_return_1y DESC \nLIMIT 1;"
}
```

**Formatted Agent Response Preview:**
> **Sector Exposure for Tech Innovation Fund** (Equities Only)  - **Technology** : 100.00%...


---
